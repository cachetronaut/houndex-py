"""Live integration tests against a real Convex deployment.

Skipped unless ``CONVEX_URL`` is set and the optional ``convex`` client is
installed. To run locally, link a deployment and push the schema + functions
first (from the TypeScript ``houndex-ts`` package, which owns the Convex
backend)::

    pnpm exec convex dev --once          # logs in, links a dev deployment, pushes
    export CONVEX_URL=https://<your-deployment>.convex.cloud
    pytest -k convex_integration packages/storage-convex

Each run uses a unique tenant namespace so repeated runs against a persistent
deployment stay independent.
"""

from __future__ import annotations

import asyncio
import math
import os
import uuid

import pytest
from houndex_core import compute_claim_id
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
from houndex_core.tenant import TenantContext, TenantRole
from houndex_storage_convex import ConvexStorageAdapter

_URL = os.environ.get("CONVEX_URL")
_EMBEDDING_DIM = 1536

pytestmark = pytest.mark.skipif(
    not _URL, reason="set CONVEX_URL to run live Convex integration tests"
)


def _adapter() -> ConvexStorageAdapter:
    convex = pytest.importorskip("convex")
    assert _URL is not None
    return ConvexStorageAdapter(convex.ConvexClient(_URL))


def _tenant(suffix: str) -> TenantContext:
    return TenantContext(
        tenant_id=f"it-{uuid.uuid4().hex}-{suffix}",
        user_id="integration",
        role=TenantRole.ADMIN,
    )


def _unit_vector(seed: int) -> list[float]:
    raw = [1.0 if i == seed % _EMBEDDING_DIM else 0.01 for i in range(_EMBEDDING_DIM)]
    norm = math.sqrt(sum(x * x for x in raw))
    return [x / norm for x in raw]


def _make_claim(tenant_id: str, *, claim_text: str = "Has audit log") -> Claim:
    source_url = f"https://example.com/{uuid.uuid4().hex}"
    return Claim.model_validate(
        {
            "tenant_id": tenant_id,
            "claim_id": compute_claim_id(
                tenant_id=tenant_id, subject="Acme", claim_text=claim_text, source_url=source_url
            ),
            "subject": "Acme",
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
    )


def test_upsert_idempotent_and_get() -> None:
    async def run() -> None:
        adapter = _adapter()
        tenant = _tenant("a")
        await adapter.ensure_tenant(EnsureTenantInput(tenant=tenant))
        claim = _make_claim(tenant.tenant_id)
        assert (await adapter.upsert_claim(UpsertClaimInput(tenant=tenant, claim=claim))).created
        assert not (
            await adapter.upsert_claim(UpsertClaimInput(tenant=tenant, claim=claim))
        ).created
        got = await adapter.get_claim(GetClaimInput(tenant=tenant, claim_id=claim.claim_id))
        assert got is not None
        assert got.subject == "Acme"

    asyncio.run(run())


def test_tenant_isolation() -> None:
    async def run() -> None:
        adapter = _adapter()
        owner, intruder = _tenant("owner"), _tenant("intruder")
        claim = _make_claim(owner.tenant_id)
        await adapter.upsert_claim(UpsertClaimInput(tenant=owner, claim=claim))
        assert (
            await adapter.get_claim(GetClaimInput(tenant=intruder, claim_id=claim.claim_id))
        ) is None
        assert len(await adapter.search_claims(ClaimSearchInput(tenant=intruder))) == 0

    asyncio.run(run())


def test_vector_search_orders_by_cosine_distance() -> None:
    async def run() -> None:
        adapter = _adapter()
        tenant = _tenant("vec")
        near = _make_claim(tenant.tenant_id, claim_text="near")
        far = _make_claim(tenant.tenant_id, claim_text="far")
        await adapter.upsert_claim(
            UpsertClaimInput(tenant=tenant, claim=near, embedding=_unit_vector(0))
        )
        await adapter.upsert_claim(
            UpsertClaimInput(tenant=tenant, claim=far, embedding=_unit_vector(7))
        )
        results = await adapter.search_claims(
            ClaimSearchInput(tenant=tenant, query_vector=_unit_vector(0), limit=2)
        )
        assert [c.claim_id for c in results] == [near.claim_id, far.claim_id]

    asyncio.run(run())


def test_run_edge_curation_kb_override() -> None:
    async def run() -> None:
        adapter = _adapter()
        tenant = _tenant("flow")
        created = await adapter.create_run(
            CreateRunInput(tenant=tenant, run_id="r1", subject="Acme")
        )
        assert created.status == "running"
        await adapter.complete_run(CompleteRunInput(tenant=tenant, run_id="r1"))

        edge = Edge(
            tenant_id=tenant.tenant_id,
            src_id="claim:0000000000000001",
            dst_id="claim:0000000000000002",
            kind="reinforces",
        )
        assert (await adapter.upsert_edge(UpsertEdgeInput(tenant=tenant, edge=edge))).created
        assert not (await adapter.upsert_edge(UpsertEdgeInput(tenant=tenant, edge=edge))).created

        claim = _make_claim(tenant.tenant_id)
        await adapter.create_curation_suggestion(
            CurationSuggestionInput(tenant=tenant, suggestion_id="s1", claim=claim)
        )
        await adapter.decide_suggestion(
            DecideSuggestionInput(tenant=tenant, suggestion_id="s1", status="approved")
        )
        await adapter.upsert_kb_entry(
            UpsertKbEntryInput(tenant=tenant, entry_id="e1", claim=claim, action="approved")
        )
        entries = await adapter.list_kb_entries(ListKbEntriesInput(tenant=tenant, subject="Acme"))
        assert len(entries) == 1
        assert entries[0].status == "approved"

        await adapter.record_verification_override(
            VerificationOverrideInput(
                tenant=tenant, claim_id=claim.claim_id, verdict="green", reason="ok"
            )
        )

    asyncio.run(run())
