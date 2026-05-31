"""Live integration tests against a real Supabase (Postgres + pgvector).

Skipped unless ``SUPABASE_URL`` and a service-role key are set, and the optional
``supabase`` client is installed. To run locally::

    supabase start                       # in the repo root, boots local stack
    supabase db reset                    # applies supabase/migrations/*.sql
    export SUPABASE_URL=http://127.0.0.1:54321
    export SUPABASE_SERVICE_ROLE_KEY=<service_role key from `supabase start`>
    PYTHONSAFEPATH=1 pytest -k integration packages/storage-supabase

``PYTHONSAFEPATH=1`` is required: the Supabase CLI directory at the repo root is
literally named ``supabase/`` and, with the current working directory on
``sys.path``, it shadows the installed ``supabase`` client library. Setting the
flag drops the implicit CWD entry so the real package imports.

The service-role key bypasses row-level security; the adapter still filters every
query by ``tenant_id``, so isolation is exercised on that path. Each test run uses
a unique tenant namespace so repeated runs against a persistent database stay
independent.
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
from houndex_storage_supabase import SupabaseStorageAdapter

_URL = os.environ.get("SUPABASE_URL")
_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
_EMBEDDING_DIM = 1536

pytestmark = pytest.mark.skipif(
    not (_URL and _KEY),
    reason="set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to run live integration tests",
)


def _client():  # noqa: ANN202 — supabase Client type only available when extra is installed
    create_client = pytest.importorskip("supabase").create_client
    assert _URL is not None and _KEY is not None
    return create_client(_URL, _KEY)


def _tenant(suffix: str) -> TenantContext:
    return TenantContext(
        tenant_id=f"it-{uuid.uuid4().hex}-{suffix}",
        user_id="integration",
        role=TenantRole.ADMIN,
    )


def _unit_vector(seed: int) -> list[float]:
    """A deterministic L2-normalized vector that leans on dimension ``seed``."""
    raw = [1.0 if i == seed % _EMBEDDING_DIM else 0.01 for i in range(_EMBEDDING_DIM)]
    norm = math.sqrt(sum(x * x for x in raw))
    return [x / norm for x in raw]


def _make_claim(
    tenant_id: str, *, subject: str = "Acme", claim_text: str = "Has audit log"
) -> Claim:
    source_url = f"https://example.com/{uuid.uuid4().hex}"
    return Claim.model_validate(
        {
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
    )


def test_upsert_idempotent_and_get() -> None:
    async def run() -> None:
        adapter = SupabaseStorageAdapter(_client())
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
        adapter = SupabaseStorageAdapter(_client())
        owner, intruder = _tenant("owner"), _tenant("intruder")
        claim = _make_claim(owner.tenant_id)
        await adapter.upsert_claim(UpsertClaimInput(tenant=owner, claim=claim))
        assert (
            await adapter.get_claim(GetClaimInput(tenant=intruder, claim_id=claim.claim_id))
        ) is None
        assert len(await adapter.search_claims(ClaimSearchInput(tenant=intruder))) == 0
        assert len(await adapter.search_claims(ClaimSearchInput(tenant=owner))) == 1

    asyncio.run(run())


def test_vector_search_orders_by_cosine_distance() -> None:
    async def run() -> None:
        adapter = SupabaseStorageAdapter(_client())
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
        adapter = SupabaseStorageAdapter(_client())
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
