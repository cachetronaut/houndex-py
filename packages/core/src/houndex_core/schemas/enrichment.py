"""Deterministic enrichment schemas. Every field is a stable numeric a
downstream judge can trust and re-verify against the graph; no model is in the
loop.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .taxonomy import Category, Confidence, EdgeKind, Polarity, Scope, SourceTier


class Enrichment(BaseModel):
    corroboration_count: dict[EdgeKind, int] = Field(default_factory=dict)
    contradiction_count: int = 0
    source_tier_distribution: dict[SourceTier, int] = Field(default_factory=dict)
    source_count: int = 0
    semantic_score: float | None = None
    via_structural_edge: bool = False


class EnrichedClaim(BaseModel):
    claim_id: str
    claim_text: str = Field(min_length=1)
    evidence_text: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    category: Category
    polarity: Polarity
    scope: Scope
    confidence: Confidence
    source_tier: SourceTier
    source_url: str = Field(min_length=1)
    enrichment: Enrichment
