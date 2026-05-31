from __future__ import annotations

import asyncio
import json
import math
from typing import Any

import pytest
from houndex_cli.commands import CommandDeps, ask, doctor, evaluate, ingest, init, verify
from houndex_cli.config import EmbeddingConfig, HoundexConfig
from houndex_cli.embedder import SyntheticEmbedder
from houndex_cli.engine import build_answer_envelope, build_claim
from houndex_core import compute_claim_id
from houndex_core.schemas import OutputEnvelope, TraceEntry
from houndex_core.storage import EnsureTenantInput, UpsertClaimInput
from houndex_evals import EvalFixture
from houndex_storage_local import LocalStorageAdapter

DIM = 64

# Reference vector produced by the TypeScript CLI: syntheticEmbedder(8).embed("hello world").
TS_REFERENCE = [
    0.33315583871344806,
    -0.3339984022759528,
    0.4304256902219349,
    -0.3266503861956138,
    0.44534948283226516,
    0.15665859088976694,
    0.23607507901640584,
    0.45483621877808,
]


def _config() -> HoundexConfig:
    return HoundexConfig(embedding=EmbeddingConfig(dimensions=DIM))


def _deps() -> CommandDeps:
    return CommandDeps(
        adapter=LocalStorageAdapter(),
        config=_config(),
        embedder=SyntheticEmbedder(DIM),
        now=lambda: 1_700_000_000_000,
    )


def _claim_content(**overrides: Any) -> dict[str, Any]:
    return {
        "subject": "Acme",
        "category": "security",
        "polarity": "positive",
        "scope": "global",
        "claim_text": "Has an audit log",
        "evidence_text": "evidence",
        "confidence": "stated",
        "source_url": "https://example.com/security",
        "source_tier": "tier_2",
        "extracted_at": 1_700_000_000_000,
        **overrides,
    }


def test_embedder_deterministic_and_unit_length() -> None:
    embedder = SyntheticEmbedder(DIM)
    vector = embedder.embed("hello world")
    assert vector == embedder.embed("hello world")
    assert len(vector) == DIM
    assert math.isclose(
        math.sqrt(sum(component * component for component in vector)), 1.0, abs_tol=1e-9
    )
    assert embedder.embed("different") != vector


def test_embedder_matches_typescript() -> None:
    vec = SyntheticEmbedder(8).embed("hello world")
    assert vec == pytest.approx(TS_REFERENCE, abs=1e-12)


def test_init_content_and_overwrite_guard() -> None:
    created = init(adapter="supabase", tenant_id=None, force=False, config_exists=False)
    assert created.code == 0
    assert created.content is not None
    assert json.loads(created.content)["adapter"] == "supabase"

    blocked = init(adapter=None, tenant_id=None, force=False, config_exists=True)
    assert blocked.code == 2
    assert blocked.content is None


def test_doctor_local_passes_and_remote_missing_env_fails() -> None:
    async def run() -> None:
        ok = await doctor(config=_config(), env={}, connect=lambda: _ready(LocalStorageAdapter()))
        assert ok.code == 0

        cfg = HoundexConfig(adapter="supabase", embedding=EmbeddingConfig(dimensions=DIM))
        bad = await doctor(config=cfg, env={}, connect=lambda: _ready(LocalStorageAdapter()))
        assert bad.code == 1
        assert "SUPABASE_URL" in bad.output

    asyncio.run(run())


async def _ready(adapter: LocalStorageAdapter) -> LocalStorageAdapter:
    return adapter


def test_ingest_then_ask() -> None:
    async def run() -> None:
        deps = _deps()
        res = await ingest(
            deps,
            claims=[_claim_content(), _claim_content(claim_text="Encrypts at rest")],
            as_json=True,
        )
        assert json.loads(res.output) == {"created": 2, "skipped": 0, "total": 2}

        answered = await ask(deps, query="audit log", limit=5, as_json=False)
        assert answered.code == 0
        assert "verdict: PASS" in answered.output
        assert "citations:" in answered.output

    asyncio.run(run())


def test_ingest_idempotent() -> None:
    async def run() -> None:
        deps = _deps()
        await ingest(deps, claims=[_claim_content()], as_json=False)
        again = await ingest(deps, claims=[_claim_content()], as_json=True)
        assert json.loads(again.output)["skipped"] == 1

    asyncio.run(run())


def test_verify_pass_fail_invalid_and_self_contained() -> None:
    async def run() -> None:
        deps = _deps()
        tenant = deps.config.tenant_context()
        claim = build_claim(tenant.tenant_id, _claim_content())
        await deps.adapter.ensure_tenant(EnsureTenantInput(tenant=tenant))
        await deps.adapter.upsert_claim(UpsertClaimInput(tenant=tenant, claim=claim))

        good = build_answer_envelope(tenant.tenant_id, "q", [claim], 1)
        assert (await verify(deps, envelope=good, claim_ids=None, as_json=False)).code == 0

        hallucinated = OutputEnvelope[dict[str, Any]](
            tenant_id=tenant.tenant_id,
            generated_at=1,
            trace=[TraceEntry(claim_id="deadbeefdeadbeef", mechanism="guess")],
            payload={},
        )
        assert (await verify(deps, envelope=hallucinated, claim_ids=None, as_json=False)).code == 1

        assert (
            await verify(deps, envelope={"not": "envelope"}, claim_ids=None, as_json=False)
        ).code == 1

        # self-contained universe: passes even against an empty store
        empty = _deps()
        cid = compute_claim_id(
            tenant_id=empty.config.tenant.tenant_id,
            subject="Acme",
            claim_text="Has an audit log",
            source_url="https://example.com/security",
        )
        env = OutputEnvelope[dict[str, Any]](
            tenant_id=empty.config.tenant.tenant_id,
            generated_at=1,
            trace=[TraceEntry(claim_id=cid, mechanism="vector_search")],
            payload={},
        )
        assert (await verify(empty, envelope=env, claim_ids=[cid], as_json=False)).code == 0

    asyncio.run(run())


def test_eval_threshold_gate() -> None:
    async def run() -> None:
        deps = _deps()
        tenant = deps.config.tenant_context()
        claim = build_claim(tenant.tenant_id, _claim_content())
        envelope = build_answer_envelope(tenant.tenant_id, "q", [claim], 1)
        fixture = EvalFixture(name="grounded", description="cites a known claim")
        cases = [(fixture, envelope)]

        passed = await evaluate(
            deps, cases=cases, claim_ids=[claim.claim_id], threshold=0.5, as_json=True
        )
        assert passed.code == 0
        assert json.loads(passed.output)["aggregate"] >= 0.5

        failed = await evaluate(deps, cases=cases, claim_ids=[], threshold=0.99, as_json=True)
        assert failed.code == 1

    asyncio.run(run())
