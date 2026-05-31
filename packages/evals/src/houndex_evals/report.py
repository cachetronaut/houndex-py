"""Markdown regression report from a set of scored fixtures. Mirrors the
TypeScript ``formatReport``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .rubric import RubricScore


@dataclass(frozen=True)
class FixtureResult:
    name: str
    score: RubricScore


def _fmt(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"


def format_report(results: Sequence[FixtureResult]) -> str:
    passed = sum(1 for result in results if result.score.passed)
    lines = [
        "# Regression report",
        "",
        f"{passed}/{len(results)} fixtures passed.",
        "",
        "| fixture | passed | total | trace | validity | determinism |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in results:
        score = result.score
        check = "✅" if score.passed else "❌"
        lines.append(
            f"| {result.name} | {check} | {_fmt(score.total)} | "
            f"{_fmt(score.trace_resolution)} | {_fmt(score.envelope_validity)} | "
            f"{_fmt(score.determinism)} |"
        )
    return "\n".join(lines) + "\n"
