"""Deterministic source-tier classifier. The rubric is plain data (lists of
domains per tier). Mirrors the TypeScript ``SourceTierClassifier``.

Precedence: authoritative domain wins; registrable root matching the normalized
subject -> tier_1; tier_2 list -> tier_2; tier_3 list -> tier_3; else tier_4.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypedDict

from houndex_core.schemas import SourceTier, extract_domain


class SourceTierRubric(TypedDict, total=False):
    tier_2_domains: list[str]
    tier_3_domains: list[str]
    authoritative_domains: list[str]


def _normalize_subject(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


class SourceTierClassifier:
    def __init__(self, rubric: SourceTierRubric | None = None) -> None:
        rubric = rubric or {}

        def lower(values: Iterable[str] | None) -> frozenset[str]:
            return frozenset(domain.lower() for domain in (values or []))

        self._tier2 = lower(rubric.get("tier_2_domains"))
        self._tier3 = lower(rubric.get("tier_3_domains"))
        self._authoritative = lower(rubric.get("authoritative_domains"))

    def classify(self, url: str, subject: str | None = None) -> SourceTier:
        registrable = extract_domain(url)
        root = registrable.split(".")[0] if registrable else ""

        if registrable in self._authoritative:
            return "authoritative"
        if subject is not None and _normalize_subject(subject) == root:
            return "tier_1"
        if registrable in self._tier2:
            return "tier_2"
        if registrable in self._tier3:
            return "tier_3"
        return "tier_4"
