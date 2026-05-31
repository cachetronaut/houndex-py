from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from houndex_core import compute_claim_id, tenant_primary, tenant_secondary
from houndex_core.schemas import Claim, Edge
from houndex_core.storage import (
    ClaimSearchInput,
    CompleteRunInput,
    CreateRunInput,
    CurationSuggestionInput,
    DecideSuggestionInput,
    EnsureTenantInput,
    GetClaimInput,
    ListKbEntriesInput,
    UpsertClaimInput,
    UpsertEdgeInput,
    UpsertKbEntryInput,
    VerificationOverrideInput,
)
from houndex_storage_supabase import SupabaseStorageAdapter

# ── In-memory Supabase fake (chainable builder + .execute()). ──────────────


class _Resp:
    def __init__(self, data: Any) -> None:
        self.data = data


class _Query:
    def __init__(self, store: dict[str, list[dict[str, Any]]], table: str) -> None:
        self._store = store
        self._table = table
        self._filters: list[tuple[str, Any]] = []
        self._limit: int | None = None
        self._mode = "select"
        self._payload: dict[str, Any] = {}
        self._on_conflict: str | None = None
        self._ignore = False

    def select(self, columns: str = "*") -> _Query:
        self._mode = "select"
        return self

    def insert(self, row: Mapping[str, Any]) -> _Query:
        self._mode = "insert"
        self._payload = dict(row)
        return self

    def upsert(
        self,
        row: Mapping[str, Any],
        *,
        on_conflict: str | None = None,
        ignore_duplicates: bool = False,
    ) -> _Query:
        self._mode = "upsert"
        self._payload = dict(row)
        self._on_conflict = on_conflict
        self._ignore = ignore_duplicates
        return self

    def update(self, values: Mapping[str, Any]) -> _Query:
        self._mode = "update"
        self._payload = dict(values)
        return self

    def eq(self, column: str, value: Any) -> _Query:
        self._filters.append((column, value))
        return self

    def limit(self, count: int) -> _Query:
        self._limit = count
        return self

    def execute(self) -> _Resp:
        rows = self._store.setdefault(self._table, [])
        if self._mode == "insert":
            rows.append(self._payload)
            return _Resp(None)
        if self._mode == "upsert":
            conflict_columns = [
                column.strip() for column in (self._on_conflict or "").split(",") if column.strip()
            ]
            existing_index = next(
                (
                    index
                    for index, existing_row in enumerate(rows)
                    if conflict_columns
                    and all(
                        existing_row.get(column) == self._payload.get(column)
                        for column in conflict_columns
                    )
                ),
                -1,
            )
            if existing_index == -1:
                rows.append(self._payload)
            elif not self._ignore:
                rows[existing_index] = self._payload
            return _Resp(None)
        matched = [
            row for row in rows if all(row.get(column) == value for column, value in self._filters)
        ]
        if self._mode == "update":
            for row in matched:
                row.update(self._payload)
            return _Resp(matched)
        if self._limit is not None:
            matched = matched[: self._limit]
        return _Resp(matched)


class FakeSupabase:
    def __init__(self) -> None:
        self._store: dict[str, list[dict[str, Any]]] = {}

    def table(self, name: str) -> _Query:
        return _Query(self._store, name)

    def rpc(self, fn: str, params: Mapping[str, Any]) -> _Query:
        return _Query(self._store, "__rpc__")


def _make_claim(**overrides: Any) -> Claim:
    subject = overrides.pop("subject", "Acme")
    claim_text = overrides.pop("claim_text", "Has an audit log")
    source_url = overrides.pop("source_url", "https://example.com/security")
    tenant_id = overrides.pop("tenant_id", "primary")
    data: dict[str, Any] = {
        "tenant_id": tenant_id,
        "claim_id": compute_claim_id(
            tenant_id=tenant_id, subject=subject, claim_text=claim_text, source_url=source_url
        ),
        "subject": subject,
        "category": "security",
        "polarity": "positive",
        "scope": "global",
        "claim_text": claim_text,
        "evidence_text": "evidence",
        "confidence": "stated",
        "source_url": source_url,
        "source_tier": "tier_2",
        "extracted_at": 1_700_000_000_000,
    }
    data.update(overrides)
    return Claim.model_validate(data)


def _adapter() -> SupabaseStorageAdapter:
    return SupabaseStorageAdapter(FakeSupabase())


def test_upsert_idempotent_and_get() -> None:
    async def run() -> None:
        adapter = _adapter()
        await adapter.ensure_tenant(EnsureTenantInput(tenant=tenant_primary()))
        claim = _make_claim()
        assert (
            await adapter.upsert_claim(UpsertClaimInput(tenant=tenant_primary(), claim=claim))
        ).created
        assert not (
            await adapter.upsert_claim(UpsertClaimInput(tenant=tenant_primary(), claim=claim))
        ).created
        got = await adapter.get_claim(
            GetClaimInput(tenant=tenant_primary(), claim_id=claim.claim_id)
        )
        assert got is not None
        assert got.subject == "Acme"

    asyncio.run(run())


def test_search_filters_by_subject() -> None:
    async def run() -> None:
        adapter = _adapter()
        await adapter.upsert_claim(UpsertClaimInput(tenant=tenant_primary(), claim=_make_claim()))
        await adapter.upsert_claim(
            UpsertClaimInput(
                tenant=tenant_primary(), claim=_make_claim(subject="Globex", claim_text="other")
            )
        )
        acme = await adapter.search_claims(
            ClaimSearchInput(tenant=tenant_primary(), subject="Acme")
        )
        assert len(acme) == 1
        assert acme[0].subject == "Acme"

    asyncio.run(run())


def test_tenant_isolation() -> None:
    async def run() -> None:
        adapter = _adapter()
        claim = _make_claim(tenant_id="primary")
        await adapter.upsert_claim(UpsertClaimInput(tenant=tenant_primary(), claim=claim))
        assert (
            await adapter.get_claim(
                GetClaimInput(tenant=tenant_secondary(), claim_id=claim.claim_id)
            )
        ) is None
        assert len(await adapter.search_claims(ClaimSearchInput(tenant=tenant_secondary()))) == 0
        assert len(await adapter.search_claims(ClaimSearchInput(tenant=tenant_primary()))) == 1

    asyncio.run(run())


def test_run_edge_curation_kb_override() -> None:
    async def run() -> None:
        adapter = _adapter()
        created = await adapter.create_run(
            CreateRunInput(tenant=tenant_primary(), run_id="r1", subject="Acme")
        )
        assert created.status == "running"
        await adapter.complete_run(CompleteRunInput(tenant=tenant_primary(), run_id="r1"))

        edge = Edge(
            tenant_id="primary",
            src_id="claim:0000000000000001",
            dst_id="claim:0000000000000002",
            kind="reinforces",
        )
        assert (
            await adapter.upsert_edge(UpsertEdgeInput(tenant=tenant_primary(), edge=edge))
        ).created
        assert not (
            await adapter.upsert_edge(UpsertEdgeInput(tenant=tenant_primary(), edge=edge))
        ).created

        claim = _make_claim()
        await adapter.create_curation_suggestion(
            CurationSuggestionInput(tenant=tenant_primary(), suggestion_id="s1", claim=claim)
        )
        await adapter.decide_suggestion(
            DecideSuggestionInput(tenant=tenant_primary(), suggestion_id="s1", status="approved")
        )
        await adapter.upsert_kb_entry(
            UpsertKbEntryInput(
                tenant=tenant_primary(), entry_id="e1", claim=claim, action="approved"
            )
        )
        entries = await adapter.list_kb_entries(
            ListKbEntriesInput(tenant=tenant_primary(), subject="Acme")
        )
        assert len(entries) == 1
        assert entries[0].status == "approved"
        assert entries[0].claim.subject == "Acme"

        await adapter.record_verification_override(
            VerificationOverrideInput(
                tenant=tenant_primary(), claim_id=claim.claim_id, verdict="green", reason="ok"
            )
        )

    asyncio.run(run())
