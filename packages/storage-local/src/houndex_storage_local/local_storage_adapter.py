"""Zero-service, in-memory ``StorageAdapter``. Every method is scoped to
``input.tenant.tenant_id``; tenants are fully partitioned, so a read for one
tenant can never return another tenant's records. Mirrors the TypeScript
``LocalStorageAdapter``.
"""

from __future__ import annotations

import math
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Literal

from houndex_core.schemas import (
    Claim,
    Run,
    Source,
    canonicalize_url,
    edge_idempotency_key,
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


@dataclass
class _StoredClaim:
    claim: Claim
    embedding: Sequence[float] | None = None


@dataclass
class _StoredSuggestion:
    claim: Claim
    status: str
    rationale: str | None = None


@dataclass
class _Override:
    claim_id: str
    verdict: str
    reason: str


@dataclass
class _TenantStore:
    runs: dict[str, Run] = field(default_factory=dict)
    sources: dict[str, Source] = field(default_factory=dict)
    claims: dict[str, _StoredClaim] = field(default_factory=dict)
    edges: set[str] = field(default_factory=set)
    suggestions: dict[str, _StoredSuggestion] = field(default_factory=dict)
    kb_entries: dict[str, KbEntryRecord] = field(default_factory=dict)
    overrides: list[_Override] = field(default_factory=list)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    length = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(length))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class LocalStorageAdapter:
    def __init__(self) -> None:
        self._tenants: dict[str, _TenantStore] = {}

    def _store(self, tenant_id: str) -> _TenantStore:
        store = self._tenants.get(tenant_id)
        if store is None:
            store = _TenantStore()
            self._tenants[tenant_id] = store
        return store

    async def ensure_tenant(self, input: EnsureTenantInput) -> None:
        self._store(input.tenant.tenant_id)

    async def create_run(self, input: CreateRunInput) -> Run:
        run = Run(
            tenant_id=input.tenant.tenant_id,
            run_id=input.run_id,
            subject=input.subject,
            signal=input.signal,
            status="running",
            created_at=_now_ms(),
        )
        self._store(input.tenant.tenant_id).runs[run.run_id] = run
        return run

    async def complete_run(self, input: CompleteRunInput) -> None:
        self._set_run_status(input.tenant.tenant_id, input.run_id, "complete")

    async def fail_run(self, input: FailRunInput) -> None:
        self._set_run_status(input.tenant.tenant_id, input.run_id, "failed")

    def _set_run_status(
        self, tenant_id: str, run_id: str, status: Literal["complete", "failed"]
    ) -> None:
        run = self._store(tenant_id).runs.get(run_id)
        if run is not None:
            run.status = status

    async def upsert_source(self, input: UpsertSourceInput) -> Source:
        key = canonicalize_url(input.source.url)
        source = input.source.model_copy(update={"url": key})
        self._store(input.tenant.tenant_id).sources[key] = source
        return source

    async def upsert_claim(self, input: UpsertClaimInput) -> UpsertResult:
        claims = self._store(input.tenant.tenant_id).claims
        created = input.claim.claim_id not in claims
        claims[input.claim.claim_id] = _StoredClaim(claim=input.claim, embedding=input.embedding)
        return UpsertResult(id=input.claim.claim_id, created=created)

    async def upsert_edge(self, input: UpsertEdgeInput) -> UpsertResult:
        key = edge_idempotency_key(
            src_id=input.edge.src_id, dst_id=input.edge.dst_id, kind=input.edge.kind
        )
        edges = self._store(input.tenant.tenant_id).edges
        created = key not in edges
        edges.add(key)
        return UpsertResult(id=key, created=created)

    async def search_claims(self, input: ClaimSearchInput) -> list[Claim]:
        stored = list(self._store(input.tenant.tenant_id).claims.values())
        matches = [
            entry
            for entry in stored
            if (input.subject is None or entry.claim.subject == input.subject)
            and (input.category is None or entry.claim.category == input.category)
        ]

        if input.query_vector is not None:
            query = input.query_vector

            def score(entry: _StoredClaim) -> float:
                return _cosine_similarity(query, entry.embedding) if entry.embedding else -1.0

            matches.sort(key=score, reverse=True)

        claims = [entry.claim for entry in matches]
        return claims[: input.limit] if input.limit is not None else claims

    async def get_claim(self, input: GetClaimInput) -> Claim | None:
        entry = self._store(input.tenant.tenant_id).claims.get(input.claim_id)
        return entry.claim if entry is not None else None

    async def create_curation_suggestion(self, input: CurationSuggestionInput) -> None:
        self._store(input.tenant.tenant_id).suggestions[input.suggestion_id] = _StoredSuggestion(
            claim=input.claim, status="pending", rationale=input.rationale
        )

    async def decide_suggestion(self, input: DecideSuggestionInput) -> None:
        suggestion = self._store(input.tenant.tenant_id).suggestions.get(input.suggestion_id)
        if suggestion is None:
            return
        suggestion.status = input.status
        if input.edited_claim is not None:
            suggestion.claim = input.edited_claim

    async def upsert_kb_entry(self, input: UpsertKbEntryInput) -> None:
        self._store(input.tenant.tenant_id).kb_entries[input.entry_id] = KbEntryRecord(
            tenant_id=input.tenant.tenant_id,
            entry_id=input.entry_id,
            claim=input.claim,
            status="rejected" if input.action == "rejected" else "approved",
            updated_at=_now_ms(),
        )

    async def list_kb_entries(self, input: ListKbEntriesInput) -> list[KbEntryRecord]:
        entries = self._store(input.tenant.tenant_id).kb_entries.values()
        return [
            entry
            for entry in entries
            if (input.subject is None or entry.claim.subject == input.subject)
            and (input.category is None or entry.claim.category == input.category)
        ]

    async def record_verification_override(self, input: VerificationOverrideInput) -> None:
        self._store(input.tenant.tenant_id).overrides.append(
            _Override(claim_id=input.claim_id, verdict=input.verdict, reason=input.reason)
        )
