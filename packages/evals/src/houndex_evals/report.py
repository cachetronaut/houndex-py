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
        s = result.score
        check = "✅" if s.passed else "❌"
        lines.append(
            f"| {result.name} | {check} | {_fmt(s.total)} | {_fmt(s.trace_resolution)} "
            f"| {_fmt(s.envelope_validity)} | {_fmt(s.determinism)} |"
        )
    return "\n".join(lines) + "\n"
