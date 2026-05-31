"""The ``StorageAdapter`` contract — the single seam that decouples the framework
from any particular database. Every method takes a ``TenantContext``, so a
conforming adapter scopes all reads and writes to a tenant by construction.
Implementations live in adapter packages; the pipeline and surfaces depend only
on this protocol.

Records reuse the core schema types so an adapter never invents a parallel
shape. Ids are content-addressed by core, so upserts are idempotent: a repeat
write of the same logical record is a no-op, reported via ``UpsertResult.created``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from ..schemas.agent_io import Verdict
from ..schemas.edges import Edge
from ..schemas.nodes import Claim, Run, Source
from ..schemas.taxonomy import Category, CurationStatus, KbAction
from ..tenant import TenantContext


class UpsertResult(BaseModel):
    id: str
    # True if the write created a new record, False if it matched an existing one.
    created: bool


# ── tenant + run lifecycle ─────────────────────────────────────────────


class EnsureTenantInput(BaseModel):
    tenant: TenantContext


class CreateRunInput(BaseModel):
    tenant: TenantContext
    run_id: str
    subject: str
    signal: str | None = None


class CompleteRunInput(BaseModel):
    tenant: TenantContext
    run_id: str


class FailRunInput(BaseModel):
    tenant: TenantContext
    run_id: str
    reason: str | None = None


# ── evidence store: sources, claims, edges ─────────────────────────────


class UpsertSourceInput(BaseModel):
    tenant: TenantContext
    source: Source


class UpsertClaimInput(BaseModel):
    tenant: TenantContext
    claim: Claim
    # Optional embedding for vector search; dimension must match the store.
    embedding: Sequence[float] | None = None


class UpsertEdgeInput(BaseModel):
    tenant: TenantContext
    edge: Edge


class ClaimSearchInput(BaseModel):
    tenant: TenantContext
    subject: str | None = None
    category: Category | None = None
    query_vector: Sequence[float] | None = None
    limit: int | None = None


class GetClaimInput(BaseModel):
    tenant: TenantContext
    claim_id: str


# ── human curation ─────────────────────────────────────────────────────


class CurationSuggestionInput(BaseModel):
    tenant: TenantContext
    suggestion_id: str
    claim: Claim
    rationale: str | None = None


class DecideSuggestionInput(BaseModel):
    tenant: TenantContext
    suggestion_id: str
    status: CurationStatus
    # Present when the curator edited the claim before approving.
    edited_claim: Claim | None = None
    reason: str | None = None


# ── knowledge base (curated heads + non-destructive audit trail) ───────


class KbEntryRecord(BaseModel):
    tenant_id: str
    entry_id: str
    claim: Claim
    status: CurationStatus
    updated_at: int


class UpsertKbEntryInput(BaseModel):
    tenant: TenantContext
    entry_id: str
    claim: Claim
    action: KbAction


class ListKbEntriesInput(BaseModel):
    tenant: TenantContext
    subject: str | None = None
    category: Category | None = None


# ── verification overrides ─────────────────────────────────────────────


class VerificationOverrideInput(BaseModel):
    tenant: TenantContext
    claim_id: str
    verdict: Verdict
    reason: str = Field(min_length=1)


@runtime_checkable
class StorageAdapter(Protocol):
    """A tenant-scoped, storage-agnostic evidence store. Implementations must
    treat every method as scoped to ``input.tenant``; a read for one tenant must
    never return another tenant's records."""

    async def ensure_tenant(self, input: EnsureTenantInput) -> None: ...
    async def create_run(self, input: CreateRunInput) -> Run: ...
    async def complete_run(self, input: CompleteRunInput) -> None: ...
    async def fail_run(self, input: FailRunInput) -> None: ...

    async def upsert_source(self, input: UpsertSourceInput) -> Source: ...
    async def upsert_claim(self, input: UpsertClaimInput) -> UpsertResult: ...
    async def upsert_edge(self, input: UpsertEdgeInput) -> UpsertResult: ...
    async def search_claims(self, input: ClaimSearchInput) -> list[Claim]: ...
    async def get_claim(self, input: GetClaimInput) -> Claim | None: ...

    async def create_curation_suggestion(self, input: CurationSuggestionInput) -> None: ...
    async def decide_suggestion(self, input: DecideSuggestionInput) -> None: ...

    async def upsert_kb_entry(self, input: UpsertKbEntryInput) -> None: ...
    async def list_kb_entries(self, input: ListKbEntriesInput) -> list[KbEntryRecord]: ...

    async def record_verification_override(self, input: VerificationOverrideInput) -> None: ...
