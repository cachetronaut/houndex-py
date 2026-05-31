from __future__ import annotations

import asyncio
from typing import Any

from houndex_core import compute_claim_id, tenant_primary, tenant_secondary
from houndex_core.schemas import Claim, Edge
from houndex_core.storage import (
    ClaimSearchInput,
    CompleteRunInput,
    CreateRunInput,
    CurationSuggestionInput,
    DecideSuggestionInput,
    FailRunInput,
    GetClaimInput,
    ListKbEntriesInput,
    UpsertClaimInput,
    UpsertEdgeInput,
    UpsertKbEntryInput,
    VerificationOverrideInput,
)
from houndex_storage_local import LocalStorageAdapter


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


def test_upsert_is_idempotent() -> None:
    async def run() -> None:
        adapter = LocalStorageAdapter()
        tenant = tenant_primary()
        claim = _make_claim()
        assert (await adapter.upsert_claim(UpsertClaimInput(tenant=tenant, claim=claim))).created
        assert not (
            await adapter.upsert_claim(UpsertClaimInput(tenant=tenant, claim=claim))
        ).created

    asyncio.run(run())


def test_get_and_search_filter() -> None:
    async def run() -> None:
        adapter = LocalStorageAdapter()
        tenant = tenant_primary()
        await adapter.upsert_claim(UpsertClaimInput(tenant=tenant, claim=_make_claim()))
        await adapter.upsert_claim(
            UpsertClaimInput(
                tenant=tenant, claim=_make_claim(subject="Globex", claim_text="different")
            )
        )
        acme = await adapter.search_claims(ClaimSearchInput(tenant=tenant, subject="Acme"))
        assert len(acme) == 1
        assert acme[0].subject == "Acme"

        first = _make_claim()
        got = await adapter.get_claim(GetClaimInput(tenant=tenant, claim_id=first.claim_id))
        assert got is not None
        assert got.subject == "Acme"

    asyncio.run(run())


def test_vector_search_orders_by_similarity() -> None:
    async def run() -> None:
        adapter = LocalStorageAdapter()
        tenant = tenant_primary()
        near = _make_claim(claim_text="near", source_url="https://example.com/near")
        far = _make_claim(claim_text="far", source_url="https://example.com/far")
        await adapter.upsert_claim(UpsertClaimInput(tenant=tenant, claim=far, embedding=[0.0, 1.0]))
        await adapter.upsert_claim(
            UpsertClaimInput(tenant=tenant, claim=near, embedding=[1.0, 0.0])
        )
        results = await adapter.search_claims(
            ClaimSearchInput(tenant=tenant, query_vector=[1.0, 0.0])
        )
        assert results[0].claim_id == near.claim_id

    asyncio.run(run())


def test_tenant_isolation() -> None:
    async def run() -> None:
        adapter = LocalStorageAdapter()
        primary = tenant_primary()
        secondary = tenant_secondary()
        claim = _make_claim(tenant_id="primary")
        await adapter.upsert_claim(UpsertClaimInput(tenant=primary, claim=claim))

        assert (
            await adapter.get_claim(GetClaimInput(tenant=secondary, claim_id=claim.claim_id))
        ) is None
        assert len(await adapter.search_claims(ClaimSearchInput(tenant=secondary))) == 0
        assert len(await adapter.search_claims(ClaimSearchInput(tenant=primary))) == 1

    asyncio.run(run())


def test_runs_edges_curation_kb_overrides() -> None:
    async def run() -> None:
        adapter = LocalStorageAdapter()
        tenant = tenant_primary()

        created_run = await adapter.create_run(
            CreateRunInput(tenant=tenant, run_id="r1", subject="Acme")
        )
        assert created_run.status == "running"
        await adapter.complete_run(CompleteRunInput(tenant=tenant, run_id="r1"))
        await adapter.fail_run(FailRunInput(tenant=tenant, run_id="missing"))

        edge = Edge(
            tenant_id="primary",
            src_id="claim:0000000000000001",
            dst_id="claim:0000000000000002",
            kind="reinforces",
        )
        assert (await adapter.upsert_edge(UpsertEdgeInput(tenant=tenant, edge=edge))).created
        assert not (await adapter.upsert_edge(UpsertEdgeInput(tenant=tenant, edge=edge))).created

        claim = _make_claim()
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
                tenant=tenant, claim_id="abcdef0123456789", verdict="green", reason="verified"
            )
        )

    asyncio.run(run())
