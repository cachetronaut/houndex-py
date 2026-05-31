from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from houndex_core import compute_claim_id, tenant_primary
from houndex_core.schemas import Claim
from houndex_core.storage import (
    ClaimSearchInput,
    CreateRunInput,
    GetClaimInput,
    ListKbEntriesInput,
    UpsertClaimInput,
    UpsertKbEntryInput,
    VerificationOverrideInput,
)
from houndex_storage_convex import ConvexStorageAdapter


class FakeConvexClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Mapping[str, Any]]] = []
        self.responses: dict[str, Any] = {}

    def mutation(self, name: str, args: Mapping[str, Any]) -> Any:
        self.calls.append(("mutation", name, args))
        return self.responses.get(name)

    def query(self, name: str, args: Mapping[str, Any]) -> Any:
        self.calls.append(("query", name, args))
        return self.responses.get(name)


def _claim(**overrides: Any) -> Claim:
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


def _camel_row(c: Claim) -> dict[str, Any]:
    return {
        "tenantId": c.tenant_id,
        "claimId": c.claim_id,
        "subject": c.subject,
        "category": c.category,
        "polarity": c.polarity,
        "scope": c.scope,
        "claimText": c.claim_text,
        "evidenceText": c.evidence_text,
        "confidence": c.confidence,
        "sourceUrl": c.source_url,
        "sourceTier": c.source_tier,
        "extractedAt": c.extracted_at,
    }


def test_upsert_claim_wires_function_and_maps_result() -> None:
    claim = _claim()
    client = FakeConvexClient()
    client.responses["claims:upsertClaim"] = {"id": claim.claim_id, "created": True}
    adapter = ConvexStorageAdapter(client)

    result = asyncio.run(
        adapter.upsert_claim(UpsertClaimInput(tenant=tenant_primary(), claim=claim))
    )
    assert result.created is True
    assert result.id == claim.claim_id

    kind, name, args = client.calls[-1]
    assert (kind, name) == ("mutation", "claims:upsertClaim")
    assert args["claimText"] == claim.claim_text
    assert args["tenant"] == {"tenantId": "primary", "userId": "user_primary", "role": "admin"}


def test_get_claim_maps_camel_row() -> None:
    claim = _claim()
    client = FakeConvexClient()
    client.responses["claims:getClaim"] = _camel_row(claim)
    adapter = ConvexStorageAdapter(client)

    got = asyncio.run(
        adapter.get_claim(GetClaimInput(tenant=tenant_primary(), claim_id=claim.claim_id))
    )
    assert got is not None
    assert got.subject == "Acme"
    assert got.claim_text == claim.claim_text


def test_get_claim_none() -> None:
    client = FakeConvexClient()  # no response registered -> None
    adapter = ConvexStorageAdapter(client)
    got = asyncio.run(
        adapter.get_claim(GetClaimInput(tenant=tenant_primary(), claim_id="abcdef0123456789"))
    )
    assert got is None


def test_search_claims_maps_rows() -> None:
    claim = _claim()
    client = FakeConvexClient()
    client.responses["claims:searchClaims"] = [_camel_row(claim)]
    adapter = ConvexStorageAdapter(client)

    rows = asyncio.run(
        adapter.search_claims(ClaimSearchInput(tenant=tenant_primary(), subject="Acme"))
    )
    assert len(rows) == 1
    assert rows[0].subject == "Acme"
    _, _, args = client.calls[-1]
    assert args["subject"] == "Acme"


def test_create_run_maps_row() -> None:
    client = FakeConvexClient()
    client.responses["runs:createRun"] = {
        "tenantId": "primary",
        "runId": "r1",
        "subject": "Acme",
        "status": "running",
        "createdAt": 1,
    }
    adapter = ConvexStorageAdapter(client)
    run = asyncio.run(
        adapter.create_run(CreateRunInput(tenant=tenant_primary(), run_id="r1", subject="Acme"))
    )
    assert run.status == "running"
    assert run.run_id == "r1"


def test_kb_roundtrip() -> None:
    claim = _claim()
    client = FakeConvexClient()
    client.responses["kb:listKbEntries"] = [
        {
            "tenantId": "primary",
            "entryId": "e1",
            "claim": _camel_row(claim),
            "status": "approved",
            "updatedAt": 2,
        }
    ]
    adapter = ConvexStorageAdapter(client)

    asyncio.run(
        adapter.upsert_kb_entry(
            UpsertKbEntryInput(
                tenant=tenant_primary(), entry_id="e1", claim=claim, action="approved"
            )
        )
    )
    _, name, args = client.calls[-1]
    assert name == "kb:upsertKbEntry"
    assert args["claim"]["claimText"] == claim.claim_text

    entries = asyncio.run(adapter.list_kb_entries(ListKbEntriesInput(tenant=tenant_primary())))
    assert len(entries) == 1
    assert entries[0].status == "approved"
    assert entries[0].claim.subject == "Acme"


def test_override_call_name() -> None:
    client = FakeConvexClient()
    adapter = ConvexStorageAdapter(client)
    asyncio.run(
        adapter.record_verification_override(
            VerificationOverrideInput(
                tenant=tenant_primary(), claim_id="abcdef0123456789", verdict="green", reason="ok"
            )
        )
    )
    kind, name, args = client.calls[-1]
    assert (kind, name) == ("mutation", "overrides:recordVerificationOverride")
    assert args["verdict"] == "green"
