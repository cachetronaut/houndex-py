"""Deterministic enrichment. Pure over a claim's incident edges; byte-identical
for the same inputs, no model in the loop. Mirrors the TypeScript
``computeEnrichment``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from houndex_core.schemas import EdgeKind, Enrichment

_CORROBORATION_KINDS: tuple[EdgeKind, ...] = ("reinforces", "refines", "duplicates")


@dataclass(frozen=True)
class EnrichmentEdge:
    src_id: str
    dst_id: str
    kind: EdgeKind
    attributes: dict[str, str] = field(default_factory=dict)


def compute_enrichment(
    *,
    claim_id: str,
    edges: Sequence[EnrichmentEdge],
    semantic_score: float | None = None,
    via_structural_edge: bool = False,
) -> Enrichment:
    incident = [edge for edge in edges if edge.src_id == claim_id or edge.dst_id == claim_id]

    corroboration: dict[str, int] = {}
    for kind in _CORROBORATION_KINDS:
        count = sum(1 for edge in incident if edge.kind == kind)
        if count > 0:
            corroboration[kind] = count

    contradiction_count = sum(1 for edge in incident if edge.kind == "contradicts")

    distribution: dict[str, int] = {}
    for edge in incident:
        if edge.kind != "cites_source":
            continue
        tier = edge.attributes.get("tier")
        if tier is not None:
            distribution[tier] = distribution.get(tier, 0) + 1
    source_count = sum(distribution.values())

    return Enrichment.model_validate(
        {
            "corroboration_count": {key: corroboration[key] for key in sorted(corroboration)},
            "contradiction_count": contradiction_count,
            "source_tier_distribution": {key: distribution[key] for key in sorted(distribution)},
            "source_count": source_count,
            "semantic_score": semantic_score,
            "via_structural_edge": via_structural_edge,
        }
    )
