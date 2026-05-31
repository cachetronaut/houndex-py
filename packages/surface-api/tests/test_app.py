from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from fastapi.testclient import TestClient
from houndex_cli import default_config
from houndex_cli.engine import build_answer_envelope, build_claim
from houndex_core.storage import EnsureTenantInput, UpsertClaimInput
from houndex_storage_local import LocalStorageAdapter
from houndex_surface_api import create_app
from houndex_surface_api.deps import ApiDeps


def _claim_content(text: str = "Acme keeps audit logs") -> dict[str, Any]:
    return {
        "subject": "Acme",
        "category": "capability",
        "polarity": "positive",
        "scope": "global",
        "claim_text": text,
        "evidence_text": text,
        "confidence": "stated",
        "source_url": "https://example.com/docs/a",
        "source_tier": "tier_2",
        "extracted_at": 1_700_000_000_000,
    }


def _client() -> tuple[TestClient, LocalStorageAdapter]:
    adapter = LocalStorageAdapter()
    deps = ApiDeps(adapter=adapter, config=default_config(), now=lambda: 1_700_000_000_000)
    return TestClient(create_app(deps)), adapter


def _headers(tenant_id: str = "tenant-a") -> Mapping[str, str]:
    return {"X-Houndex-Tenant": tenant_id}


def test_verify_returns_passed_true_for_grounded_answer() -> None:
    client, adapter = _client()
    claim = build_claim("tenant-a", _claim_content())

    async def seed() -> None:
        tenant = default_config(tenant_id="tenant-a").tenant_context()
        await adapter.ensure_tenant(EnsureTenantInput(tenant=tenant))
        await adapter.upsert_claim(UpsertClaimInput(tenant=tenant, claim=claim))

    asyncio.run(seed())
    envelope = build_answer_envelope("tenant-a", "audit logs", [claim], 1_700_000_000_000)

    response = client.post(
        "/verify",
        json={"envelope": envelope.model_dump()},
        headers=_headers(),
    )

    assert response.status_code == 200
    assert response.json()["passed"] is True


def test_verify_returns_passed_false_for_unknown_citation() -> None:
    client, _adapter = _client()
    envelope = {
        "tenant_id": "tenant-a",
        "generated_at": 1_700_000_000_000,
        "trace": [{"claim_id": "deadbeefdeadbeef", "mechanism": "vector_search"}],
        "payload": {"answer": "unsupported", "citations": ["deadbeefdeadbeef"]},
    }

    response = client.post("/verify", json={"envelope": envelope}, headers=_headers())

    assert response.status_code == 200
    assert response.json()["passed"] is False
    assert response.json()["trace_resolution"] == 0


def test_ask_returns_envelope_and_verdict() -> None:
    client, adapter = _client()
    claim = build_claim("tenant-a", _claim_content())

    async def seed() -> None:
        tenant = default_config(tenant_id="tenant-a").tenant_context()
        await adapter.ensure_tenant(EnsureTenantInput(tenant=tenant))
        await adapter.upsert_claim(UpsertClaimInput(tenant=tenant, claim=claim, embedding=[0.1]))

    asyncio.run(seed())

    response = client.post("/ask", json={"query": "audit", "limit": 1}, headers=_headers())

    assert response.status_code == 200
    body = response.json()
    assert body["envelope"]["tenant_id"] == "tenant-a"
    assert body["envelope"]["payload"]["citations"] == [claim.claim_id]
    assert body["verdict"]["passed"] is True


def test_ingest_processes_pages_and_reports_created_then_deduped_counts() -> None:
    client, _adapter = _client()
    payload = {
        "subject": "Acme",
        "pages": [
            {
                "source_url": "https://example.com/docs/a",
                "title": "A",
                "text": "Acme keeps audit logs.",
                "claims": [
                    {
                        "category": "capability",
                        "polarity": "positive",
                        "scope": "global",
                        "claim_text": "Acme keeps audit logs",
                        "evidence_text": "Acme keeps audit logs.",
                        "confidence": "stated",
                    }
                ],
            }
        ],
    }

    first = client.post("/ingest", json=payload, headers=_headers())
    second = client.post("/ingest", json=payload, headers=_headers())

    assert first.status_code == 200
    assert first.json()["claims_created"] == 1
    assert first.json()["claims_deduped"] == 0
    assert second.status_code == 200
    assert second.json()["claims_created"] == 0
    assert second.json()["claims_deduped"] == 1


def test_missing_tenant_header_returns_clean_400() -> None:
    client, _adapter = _client()

    response = client.post("/verify", json={"envelope": {}, "claim_ids": []})

    assert response.status_code == 400
    assert response.json()["detail"] == "X-Houndex-Tenant header is required"
