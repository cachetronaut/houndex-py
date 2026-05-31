"""houndex-evals — deterministic regression/evaluation harness."""

from __future__ import annotations

from .fixture import EvalExpected, EvalFixture, EvalRubricConfig
from .report import FixtureResult, format_report
from .rubric import (
    GraphState,
    RubricScore,
    hash_envelope,
    score_determinism,
    score_envelope,
    score_envelope_validity,
    score_trace_resolution,
)

__all__ = [
    "EvalExpected",
    "EvalFixture",
    "EvalRubricConfig",
    "FixtureResult",
    "GraphState",
    "RubricScore",
    "format_report",
    "hash_envelope",
    "score_determinism",
    "score_envelope",
    "score_envelope_validity",
    "score_trace_resolution",
]
