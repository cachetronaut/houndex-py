"""Convex client adapter implementing the ``StorageAdapter`` contract.

A thin RPC layer over a deployed ``houndex/storage-convex`` backend: each
method calls the matching Convex function with a validated ``tenant`` argument
and translates between the core (snake_case) models and the Convex
(camelCase) wire shapes. Mirrors the TypeScript ``ConvexStorageAdapter``.

The Convex Python client is synchronous; methods bridge it to the async
``StorageAdapter`` protocol with ``asyncio.to_thread``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

from houndex_core.schemas import Claim, Run, Source
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
from houndex_core.tenant import TenantContext


@runtime_checkable
class ConvexClient(Protocol):
    """The slice of the Convex Python client this adapter uses."""

    def query(self, name: str, args: Mapping[str, Any]) -> Any: ...
    def mutation(self, name: str, args: Mapping[str, Any]) -> Any: ...


def _tenant_arg(tenant: TenantContext) -> dict[str, Any]:
    return {"tenantId": tenant.tenant_id, "userId": tenant.user_id, "role": tenant.role.value}


def _claim_fields(claim: Claim) -> dict[str, Any]:
    return {
        "claimId": claim.claim_id,
        "subject": claim.subject,
        "category": claim.category,
        "polarity": claim.polarity,
        "scope": claim.scope,
        "claimText": claim.claim_text,
        "evidenceText": claim.evidence_text,
        "confidence": claim.confidence,
        "sourceUrl": claim.source_url,
        "sourceTier": claim.source_tier,
        "extractedAt": claim.extracted_at,
    }


def _claim_row(claim: Claim) -> dict[str, Any]:
    return {"tenantId": claim.tenant_id, **_claim_fields(claim)}


def _claim_from_row(row: Mapping[str, Any]) -> Claim:
    return Claim.model_validate(
        {
            "tenant_id": row["tenantId"],
            "claim_id": row["claimId"],
            "subject": row["subject"],
            "category": row["category"],
            "polarity": row["polarity"],
            "scope": row["scope"],
            "claim_text": row["claimText"],
            "evidence_text": row["evidenceText"],
            "confidence": row["confidence"],
            "source_url": row["sourceUrl"],
            "source_tier": row["sourceTier"],
            "extracted_at": row["extractedAt"],
        }
    )


class ConvexStorageAdapter:
    def __init__(self, client: ConvexClient) -> None:
        self._client = client

    async def _mutation(self, name: str, args: Mapping[str, Any]) -> Any:
        return await asyncio.to_thread(self._client.mutation, name, args)

    async def _query(self, name: str, args: Mapping[str, Any]) -> Any:
        return await asyncio.to_thread(self._client.query, name, args)

    async def ensure_tenant(self, input: EnsureTenantInput) -> None:
        await self._mutation("tenants:ensureTenant", {"tenant": _tenant_arg(input.tenant)})

    async def create_run(self, input: CreateRunInput) -> Run:
        row = await self._mutation(
            "runs:createRun",
            {
                "tenant": _tenant_arg(input.tenant),
                "runId": input.run_id,
                "subject": input.subject,
                "signal": input.signal,
            },
        )
        return Run.model_validate(
            {
                "tenant_id": row["tenantId"],
                "run_id": row["runId"],
                "subject": row["subject"],
                "signal": row.get("signal"),
                "status": row["status"],
                "created_at": row["createdAt"],
            }
        )

    async def complete_run(self, input: CompleteRunInput) -> None:
        await self._mutation(
            "runs:setRunStatus",
            {"tenant": _tenant_arg(input.tenant), "runId": input.run_id, "status": "complete"},
        )

    async def fail_run(self, input: FailRunInput) -> None:
        await self._mutation(
            "runs:setRunStatus",
            {
                "tenant": _tenant_arg(input.tenant),
                "runId": input.run_id,
                "status": "failed",
                "reason": input.reason,
            },
        )

    async def upsert_source(self, input: UpsertSourceInput) -> Source:
        row = await self._mutation(
            "sources:upsertSource",
            {
                "tenant": _tenant_arg(input.tenant),
                "url": input.source.url,
                "title": input.source.title,
                "domain": input.source.domain,
                "tier": input.source.tier,
                "fetchedAt": input.source.fetched_at,
            },
        )
        return Source.model_validate(
            {
                "tenant_id": row["tenantId"],
                "url": row["url"],
                "title": row["title"],
                "domain": row["domain"],
                "tier": row["tier"],
                "fetched_at": row["fetchedAt"],
            }
        )

    async def upsert_claim(self, input: UpsertClaimInput) -> UpsertResult:
        args: dict[str, Any] = {"tenant": _tenant_arg(input.tenant), **_claim_fields(input.claim)}
        if input.embedding is not None:
            args["embedding"] = list(input.embedding)
        result = await self._mutation("claims:upsertClaim", args)
        return UpsertResult(id=result["id"], created=result["created"])

    async def upsert_edge(self, input: UpsertEdgeInput) -> UpsertResult:
        result = await self._mutation(
            "edges:upsertEdge",
            {
                "tenant": _tenant_arg(input.tenant),
                "srcId": input.edge.src_id,
                "dstId": input.edge.dst_id,
                "kind": input.edge.kind,
                "attributes": input.edge.attributes,
            },
        )
        return UpsertResult(id=result["id"], created=result["created"])

    async def search_claims(self, input: ClaimSearchInput) -> list[Claim]:
        rows = await self._query(
            "claims:searchClaims",
            {
                "tenant": _tenant_arg(input.tenant),
                "subject": input.subject,
                "category": input.category,
                "limit": input.limit,
            },
        )
        return [_claim_from_row(row) for row in rows]

    async def get_claim(self, input: GetClaimInput) -> Claim | None:
        row = await self._query(
            "claims:getClaim",
            {"tenant": _tenant_arg(input.tenant), "claimId": input.claim_id},
        )
        return None if row is None else _claim_from_row(row)

    async def create_curation_suggestion(self, input: CurationSuggestionInput) -> None:
        await self._mutation(
            "curation:createCurationSuggestion",
            {
                "tenant": _tenant_arg(input.tenant),
                "suggestionId": input.suggestion_id,
                "claim": _claim_row(input.claim),
                "rationale": input.rationale,
            },
        )

    async def decide_suggestion(self, input: DecideSuggestionInput) -> None:
        await self._mutation(
            "curation:decideSuggestion",
            {
                "tenant": _tenant_arg(input.tenant),
                "suggestionId": input.suggestion_id,
                "status": input.status,
                "editedClaim": None
                if input.edited_claim is None
                else _claim_row(input.edited_claim),
                "reason": input.reason,
            },
        )

    async def upsert_kb_entry(self, input: UpsertKbEntryInput) -> None:
        await self._mutation(
            "kb:upsertKbEntry",
            {
                "tenant": _tenant_arg(input.tenant),
                "entryId": input.entry_id,
                "claim": _claim_row(input.claim),
                "action": input.action,
                "subject": input.claim.subject,
                "category": input.claim.category,
            },
        )

    async def list_kb_entries(self, input: ListKbEntriesInput) -> list[KbEntryRecord]:
        rows = await self._query(
            "kb:listKbEntries",
            {
                "tenant": _tenant_arg(input.tenant),
                "subject": input.subject,
                "category": input.category,
            },
        )
        return [
            KbEntryRecord(
                tenant_id=row["tenantId"],
                entry_id=row["entryId"],
                claim=_claim_from_row(row["claim"]),
                status=row["status"],
                updated_at=row["updatedAt"],
            )
            for row in rows
        ]

    async def record_verification_override(self, input: VerificationOverrideInput) -> None:
        await self._mutation(
            "overrides:recordVerificationOverride",
            {
                "tenant": _tenant_arg(input.tenant),
                "claimId": input.claim_id,
                "verdict": input.verdict,
                "reason": input.reason,
            },
        )
