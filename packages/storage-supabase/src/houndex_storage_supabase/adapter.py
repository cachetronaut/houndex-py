"""Supabase (Postgres + pgvector) client adapter implementing ``StorageAdapter``.

A thin layer over the synchronous Supabase Python client, bridged to the async
contract with ``asyncio.to_thread``. Targets the SQL schema shipped by the
TypeScript ``houndex/storage-supabase`` package. Every query filters by
``tenant_id``. Because the Python core models and the Postgres columns are both
snake_case, row <-> model mapping is a direct ``model_dump`` / ``model_validate``.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from houndex_core.schemas import (
    Claim,
    Run,
    Source,
    canonicalize_url,
    edge_idempotency_key,
    source_node_id,
)
from houndex_core.storage import (
    ClaimSearchInput,
    CompleteRunInput,
    CreateRunInput,
    CurationSuggestionInput,
    DecideSuggestionInput,
    EnsureTenantInput,
    FailRunInput,
    GetClaimInput,
    KbEntryRecord,
    ListKbEntriesInput,
    UpsertClaimInput,
    UpsertEdgeInput,
    UpsertKbEntryInput,
    UpsertResult,
    UpsertSourceInput,
    VerificationOverrideInput,
)


@runtime_checkable
class SupabaseQuery(Protocol):
    """The chainable query builder slice this adapter uses (from supabase-py)."""

    def select(self, columns: str = "*") -> SupabaseQuery: ...
    def insert(self, row: Mapping[str, Any]) -> SupabaseQuery: ...
    def upsert(
        self,
        row: Mapping[str, Any],
        *,
        on_conflict: str | None = None,
        ignore_duplicates: bool = False,
    ) -> SupabaseQuery: ...
    def update(self, values: Mapping[str, Any]) -> SupabaseQuery: ...
    def eq(self, column: str, value: Any) -> SupabaseQuery: ...
    def limit(self, count: int) -> SupabaseQuery: ...
    def execute(self) -> Any: ...


@runtime_checkable
class SupabaseClient(Protocol):
    def table(self, name: str) -> SupabaseQuery: ...
    def rpc(self, fn: str, params: Mapping[str, Any]) -> SupabaseQuery: ...


_TABLE = {
    "tenants": "houndex_tenants",
    "runs": "houndex_runs",
    "claims": "houndex_claims",
    "sources": "houndex_sources",
    "edges": "houndex_edges",
    "curation": "houndex_curation_suggestions",
    "kb": "houndex_kb_entries",
    "overrides": "houndex_verification_overrides",
}
_SEARCH_FN = "houndex_search_claims"
_DEFAULT_MATCH_COUNT = 10


def _now_ms() -> int:
    return int(time.time() * 1000)


def _claim_row(claim: Claim, embedding: Sequence[float] | None = None) -> dict[str, Any]:
    row = claim.model_dump()
    row["embedding"] = list(embedding) if embedding is not None else None
    return row


class SupabaseStorageAdapter:
    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    async def _exec(self, query: SupabaseQuery) -> Any:
        response = await asyncio.to_thread(query.execute)
        return response.data

    async def _select(
        self, table: str, filters: Sequence[tuple[str, Any]], limit: int | None = None
    ) -> list[dict[str, Any]]:
        query = self._client.table(table).select("*")
        for column, value in filters:
            query = query.eq(column, value)
        if limit is not None:
            query = query.limit(limit)
        return list(await self._exec(query) or [])

    async def _select_one(
        self, table: str, filters: Sequence[tuple[str, Any]]
    ) -> dict[str, Any] | None:
        rows = await self._select(table, filters)
        return rows[0] if rows else None

    async def ensure_tenant(self, input: EnsureTenantInput) -> None:
        await self._exec(
            self._client.table(_TABLE["tenants"]).upsert(
                {"tenant_id": input.tenant.tenant_id, "created_at": _now_ms()},
                on_conflict="tenant_id",
                ignore_duplicates=True,
            )
        )

    async def create_run(self, input: CreateRunInput) -> Run:
        existing = await self._select_one(
            _TABLE["runs"], [("tenant_id", input.tenant.tenant_id), ("run_id", input.run_id)]
        )
        if existing is not None:
            return Run.model_validate(existing)
        run = Run(
            tenant_id=input.tenant.tenant_id,
            run_id=input.run_id,
            subject=input.subject,
            signal=input.signal,
            status="running",
            created_at=_now_ms(),
        )
        await self._exec(self._client.table(_TABLE["runs"]).insert(run.model_dump()))
        return run

    async def complete_run(self, input: CompleteRunInput) -> None:
        await self._set_status(input.tenant.tenant_id, input.run_id, "complete", None)

    async def fail_run(self, input: FailRunInput) -> None:
        await self._set_status(input.tenant.tenant_id, input.run_id, "failed", input.reason)

    async def _set_status(
        self, tenant_id: str, run_id: str, status: str, reason: str | None
    ) -> None:
        query = (
            self._client.table(_TABLE["runs"])
            .update({"status": status, "reason": reason})
            .eq("tenant_id", tenant_id)
            .eq("run_id", run_id)
        )
        await self._exec(query)

    async def upsert_source(self, input: UpsertSourceInput) -> Source:
        url = canonicalize_url(input.source.url)
        source_id = source_node_id(url)
        row = input.source.model_dump()
        row.update({"source_id": source_id, "url": url})
        await self._exec(
            self._client.table(_TABLE["sources"]).upsert(row, on_conflict="tenant_id,source_id")
        )
        return input.source.model_copy(update={"url": url})

    async def upsert_claim(self, input: UpsertClaimInput) -> UpsertResult:
        existing = await self._select_one(
            _TABLE["claims"],
            [("tenant_id", input.tenant.tenant_id), ("claim_id", input.claim.claim_id)],
        )
        if existing is not None:
            return UpsertResult(id=input.claim.claim_id, created=False)
        await self._exec(
            self._client.table(_TABLE["claims"]).insert(_claim_row(input.claim, input.embedding))
        )
        return UpsertResult(id=input.claim.claim_id, created=True)

    async def upsert_edge(self, input: UpsertEdgeInput) -> UpsertResult:
        key = edge_idempotency_key(
            src_id=input.edge.src_id, dst_id=input.edge.dst_id, kind=input.edge.kind
        )
        existing = await self._select_one(
            _TABLE["edges"], [("tenant_id", input.tenant.tenant_id), ("idempotency_key", key)]
        )
        if existing is not None:
            return UpsertResult(id=key, created=False)
        await self._exec(
            self._client.table(_TABLE["edges"]).insert(
                {
                    "tenant_id": input.tenant.tenant_id,
                    "idempotency_key": key,
                    "src_id": input.edge.src_id,
                    "dst_id": input.edge.dst_id,
                    "kind": input.edge.kind,
                    "attributes": input.edge.attributes,
                }
            )
        )
        return UpsertResult(id=key, created=True)

    async def search_claims(self, input: ClaimSearchInput) -> list[Claim]:
        if input.query_vector is not None:
            rows = await self._exec(
                self._client.rpc(
                    _SEARCH_FN,
                    {
                        "p_tenant_id": input.tenant.tenant_id,
                        "query_embedding": list(input.query_vector),
                        "match_count": input.limit or _DEFAULT_MATCH_COUNT,
                        "p_subject": input.subject,
                        "p_category": input.category,
                    },
                )
            )
            return [Claim.model_validate(row) for row in rows or []]
        filters: list[tuple[str, Any]] = [("tenant_id", input.tenant.tenant_id)]
        if input.subject is not None:
            filters.append(("subject", input.subject))
        if input.category is not None:
            filters.append(("category", input.category))
        rows = await self._select(_TABLE["claims"], filters, input.limit)
        return [Claim.model_validate(row) for row in rows]

    async def get_claim(self, input: GetClaimInput) -> Claim | None:
        row = await self._select_one(
            _TABLE["claims"], [("tenant_id", input.tenant.tenant_id), ("claim_id", input.claim_id)]
        )
        return None if row is None else Claim.model_validate(row)

    async def create_curation_suggestion(self, input: CurationSuggestionInput) -> None:
        await self._exec(
            self._client.table(_TABLE["curation"]).upsert(
                {
                    "tenant_id": input.tenant.tenant_id,
                    "suggestion_id": input.suggestion_id,
                    "claim": input.claim.model_dump(),
                    "status": "pending",
                    "rationale": input.rationale,
                    "created_at": _now_ms(),
                },
                on_conflict="tenant_id,suggestion_id",
                ignore_duplicates=True,
            )
        )

    async def decide_suggestion(self, input: DecideSuggestionInput) -> None:
        values: dict[str, Any] = {
            "status": input.status,
            "reason": input.reason,
            "decided_at": _now_ms(),
        }
        if input.edited_claim is not None:
            values["claim"] = input.edited_claim.model_dump()
        query = (
            self._client.table(_TABLE["curation"])
            .update(values)
            .eq("tenant_id", input.tenant.tenant_id)
            .eq("suggestion_id", input.suggestion_id)
        )
        await self._exec(query)

    async def upsert_kb_entry(self, input: UpsertKbEntryInput) -> None:
        await self._exec(
            self._client.table(_TABLE["kb"]).upsert(
                {
                    "tenant_id": input.tenant.tenant_id,
                    "entry_id": input.entry_id,
                    "claim": input.claim.model_dump(),
                    "status": "rejected" if input.action == "rejected" else "approved",
                    "subject": input.claim.subject,
                    "category": input.claim.category,
                    "updated_at": _now_ms(),
                },
                on_conflict="tenant_id,entry_id",
            )
        )

    async def list_kb_entries(self, input: ListKbEntriesInput) -> list[KbEntryRecord]:
        filters: list[tuple[str, Any]] = [("tenant_id", input.tenant.tenant_id)]
        if input.subject is not None:
            filters.append(("subject", input.subject))
        if input.category is not None:
            filters.append(("category", input.category))
        rows = await self._select(_TABLE["kb"], filters)
        return [KbEntryRecord.model_validate(row) for row in rows]

    async def record_verification_override(self, input: VerificationOverrideInput) -> None:
        await self._exec(
            self._client.table(_TABLE["overrides"]).insert(
                {
                    "tenant_id": input.tenant.tenant_id,
                    "claim_id": input.claim_id,
                    "verdict": input.verdict,
                    "reason": input.reason,
                    "created_at": _now_ms(),
                }
            )
        )
