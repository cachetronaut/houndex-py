from __future__ import annotations

from typing import Any

from houndex_evals import (
    EvalFixture,
    FixtureResult,
    GraphState,
    format_report,
    hash_envelope,
    score_envelope,
)


def _envelope(claim_ids: list[str]) -> dict[str, Any]:
    return {
        "schema_version": "v1.0.0",
        "schema_url": "https://houndex.example/schemas/output_envelope.v1.json",
        "tenant_id": "primary",
        "generated_at": 1_700_000_000_000,
        "engine_version": "0.1.0",
        "trace": [
            {"claim_id": cid, "mechanism": "semantic", "semantic_score": 0.9} for cid in claim_ids
        ],
        "payload": {"value": "x"},
    }


_FIXTURE = EvalFixture(name="demo", description="a demo fixture")


def test_full_resolution_and_validity() -> None:
    score = score_envelope(_FIXTURE, _envelope(["a", "b"]), GraphState(claim_ids=["a", "b", "c"]))
    assert score.trace_resolution == 1
    assert score.envelope_validity == 1
    assert score.passed is True


def test_penalizes_unresolved() -> None:
    score = score_envelope(_FIXTURE, _envelope(["a", "z"]), GraphState(claim_ids=["a"]))
    assert score.trace_resolution == 0.5


def test_invalid_envelope_fails() -> None:
    score = score_envelope(_FIXTURE, {"not": "an envelope"}, GraphState(claim_ids=[]))
    assert score.envelope_validity == 0
    assert score.passed is False


def test_determinism_baseline() -> None:
    env = _envelope(["a"])
    assert score_envelope(_FIXTURE, env, GraphState(claim_ids=["a"])).determinism is None
    pinned = EvalFixture.model_validate(
        {"name": "pinned", "description": "pinned", "rubric": {"baseline_hash": hash_envelope(env)}}
    )
    assert score_envelope(pinned, env, GraphState(claim_ids=["a"])).determinism == 1


def test_min_trace_entries_floor() -> None:
    strict = EvalFixture.model_validate(
        {"name": "strict", "description": "needs trace", "expected": {"min_trace_entries": 2}}
    )
    assert score_envelope(strict, _envelope(["a"]), GraphState(claim_ids=["a"])).passed is False


def test_hash_is_key_order_independent() -> None:
    assert hash_envelope({"a": 1, "b": 2}) == hash_envelope({"b": 2, "a": 1})


def test_report_renders() -> None:
    score = score_envelope(_FIXTURE, _envelope(["a"]), GraphState(claim_ids=["a"]))
    report = format_report([FixtureResult(name="demo", score=score)])
    assert "1/1 fixtures passed" in report
    assert "| demo |" in report
