"""Command handlers. Each is a pure-ish coroutine over injected dependencies
(adapter, config, embedder) and already-parsed arguments, returning an exit code
+ output string. The Typer shell (``cli.py``) does the I/O; these are unit-tested
directly against the in-memory local adapter. Mirrors the TypeScript ``commands.ts``.

Exit-code convention: 0 = pass, 1 = a verification/check failure (CI signal),
2 = operational error.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from houndex_core.storage import (
    ClaimSearchInput,
    EnsureTenantInput,
    StorageAdapter,
    UpsertClaimInput,
)
from houndex_evals import EvalFixture, FixtureResult, format_report, score_envelope

from .adapter_factory import missing_env
from .config import HoundexConfig, default_config
from .embedder import SyntheticEmbedder
from .engine import (
    build_answer_envelope,
    build_claim,
    default_verify_fixture,
    resolve_graph,
)


@dataclass
class CommandResult:
    code: int
    output: str
    content: str | None = None


@dataclass
class CommandDeps:
    adapter: StorageAdapter
    config: HoundexConfig
    embedder: SyntheticEmbedder
    now: Callable[[], int]


def init(
    *, adapter: str | None, tenant_id: str | None, force: bool, config_exists: bool
) -> CommandResult:
    if config_exists and not force:
        return CommandResult(2, "houndex.config.json already exists — pass --force to overwrite.")
    config = default_config(adapter=adapter or "local", tenant_id=tenant_id)
    content = config.model_dump_json(by_alias=True, indent=2) + "\n"
    return CommandResult(0, f"Wrote houndex.config.json (adapter: {config.adapter}).", content)


async def doctor(
    *, config: HoundexConfig, env: Mapping[str, str], connect: Callable[[], Any]
) -> CommandResult:
    lines: list[str] = [f"✓ config valid (adapter: {config.adapter})"]
    ok = True
    missing = missing_env(config.adapter, env)
    if missing:
        ok = False
        lines.append(f"✗ missing environment variables: {', '.join(missing)}")
    else:
        lines.append("✓ required environment variables present")
        try:
            adapter = await connect()
            await adapter.ensure_tenant(EnsureTenantInput(tenant=config.tenant_context()))
            lines.append(f'✓ adapter reachable (ensureTenant for "{config.tenant.tenant_id}")')
        except Exception as err:  # noqa: BLE001 — report any connectivity failure
            ok = False
            lines.append(f"✗ adapter unreachable: {err}")
    return CommandResult(0 if ok else 1, "\n".join(lines))


async def ingest(
    deps: CommandDeps, *, claims: Sequence[Mapping[str, Any]], as_json: bool
) -> CommandResult:
    tenant = deps.config.tenant_context()
    await deps.adapter.ensure_tenant(EnsureTenantInput(tenant=tenant))
    created = skipped = 0
    for content in claims:
        claim = build_claim(tenant.tenant_id, content)
        embedding = deps.embedder.embed(claim.claim_text)
        result = await deps.adapter.upsert_claim(
            UpsertClaimInput(tenant=tenant, claim=claim, embedding=embedding)
        )
        if result.created:
            created += 1
        else:
            skipped += 1
    if as_json:
        return CommandResult(
            0, json.dumps({"created": created, "skipped": skipped, "total": len(claims)})
        )
    return CommandResult(
        0, f"Ingested {len(claims)} claim(s): {created} created, {skipped} already present."
    )


async def ask(deps: CommandDeps, *, query: str, limit: int, as_json: bool) -> CommandResult:
    tenant = deps.config.tenant_context()
    query_vector = deps.embedder.embed(query)
    claims = await deps.adapter.search_claims(
        ClaimSearchInput(tenant=tenant, query_vector=query_vector, limit=limit)
    )
    envelope = build_answer_envelope(tenant.tenant_id, query, claims, deps.now())
    graph = await resolve_graph(deps.adapter, tenant)
    score = score_envelope(default_verify_fixture(), envelope, graph)
    if as_json:
        return CommandResult(
            0, json.dumps({"envelope": envelope.model_dump(), "verdict": _verdict_dict(score)})
        )
    body = "(no matching claims)" if not claims else envelope.payload["answer"]
    lines = [f"answer: {body}"]
    if claims:
        lines.append("citations:")
        lines.extend(f"  - {claim.claim_id}  {claim.claim_text}" for claim in claims)
    lines.append(f"verdict: {'PASS' if score.passed else 'FAIL'} (score {score.total:.3f})")
    return CommandResult(0, "\n".join(lines))


async def verify(
    deps: CommandDeps, *, envelope: Any, claim_ids: Sequence[str] | None, as_json: bool
) -> CommandResult:
    graph = await resolve_graph(deps.adapter, deps.config.tenant_context(), claim_ids)
    score = score_envelope(default_verify_fixture(), envelope, graph)
    code = 0 if score.passed else 1
    if as_json:
        return CommandResult(code, json.dumps(_verdict_dict(score)))
    determinism = "—" if score.determinism is None else f"{score.determinism:.3f}"
    lines = [
        f"verdict: {'PASS' if score.passed else 'FAIL'}",
        f"  traceResolution:  {score.trace_resolution:.3f}",
        f"  envelopeValidity: {score.envelope_validity:.3f}",
        f"  determinism:      {determinism}",
        f"  total:            {score.total:.3f}",
        *(f"  · {note}" for note in score.notes),
    ]
    return CommandResult(code, "\n".join(lines))


async def evaluate(
    deps: CommandDeps,
    *,
    cases: Sequence[tuple[EvalFixture, Any]],
    claim_ids: Sequence[str] | None,
    threshold: float | None,
    as_json: bool,
) -> CommandResult:
    graph = await resolve_graph(deps.adapter, deps.config.tenant_context(), claim_ids)
    results = [
        FixtureResult(name=fixture.name, score=score_envelope(fixture, envelope, graph))
        for fixture, envelope in cases
    ]
    aggregate = 0.0 if not results else sum(result.score.total for result in results) / len(results)
    below = threshold is not None and aggregate < threshold
    code = 1 if below else 0
    if as_json:
        return CommandResult(
            code,
            json.dumps(
                {
                    "aggregate": aggregate,
                    "threshold": threshold,
                    "results": [
                        {"name": result.name, **_verdict_dict(result.score)} for result in results
                    ],
                }
            ),
        )
    summary = f"aggregate: {aggregate:.3f}"
    if threshold is not None:
        summary += f" (threshold {threshold:.3f} — {'FAIL' if below else 'PASS'})"
    return CommandResult(code, f"{format_report(results)}\n{summary}")


def _verdict_dict(score: Any) -> dict[str, Any]:
    return {
        "trace_resolution": score.trace_resolution,
        "envelope_validity": score.envelope_validity,
        "determinism": score.determinism,
        "total": score.total,
        "passed": score.passed,
        "notes": list(score.notes),
    }
