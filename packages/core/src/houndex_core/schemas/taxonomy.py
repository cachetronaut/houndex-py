"""Closed vocabularies for the claim graph — the single source of truth for
every enum that crosses an agent, provider, or store boundary. Each vocabulary
is declared once as a ``Literal`` type with a matching value tuple.

``CATEGORY_VALUES`` is the one vocabulary applications are expected to replace
with their own domain categories; it ships as a small, generic default. The
rest are houndex-level and generic across domains.
"""

from __future__ import annotations

from typing import Literal

# Default claim categories — generic and domain-agnostic. Replace with your own
# closed set for a real application.
Category = Literal[
    "general",
    "capability",
    "limitation",
    "cost",
    "security",
    "support",
    "usability",
    "integration",
]
CATEGORY_VALUES: tuple[Category, ...] = (
    "general",
    "capability",
    "limitation",
    "cost",
    "security",
    "support",
    "usability",
    "integration",
)

Polarity = Literal["positive", "negative", "neutral", "unknown"]
POLARITY_VALUES: tuple[Polarity, ...] = ("positive", "negative", "neutral", "unknown")

Scope = Literal["global", "scoped", "anecdotal", "unverified"]
SCOPE_VALUES: tuple[Scope, ...] = ("global", "scoped", "anecdotal", "unverified")

SourceTier = Literal["tier_1", "tier_2", "tier_3", "tier_4", "authoritative"]
SOURCE_TIER_VALUES: tuple[SourceTier, ...] = (
    "tier_1",
    "tier_2",
    "tier_3",
    "tier_4",
    "authoritative",
)

Confidence = Literal["stated", "synthesized", "inferred", "weak"]
CONFIDENCE_VALUES: tuple[Confidence, ...] = ("stated", "synthesized", "inferred", "weak")

ReconciliationDecision = Literal[
    "new_claim",
    "duplicate",
    "reinforces_existing",
    "contradicts_existing",
    "refines_existing",
]
RECONCILIATION_DECISION_VALUES: tuple[ReconciliationDecision, ...] = (
    "new_claim",
    "duplicate",
    "reinforces_existing",
    "contradicts_existing",
    "refines_existing",
)

CurationStatus = Literal["pending", "approved", "edited", "rejected"]
CURATION_STATUS_VALUES: tuple[CurationStatus, ...] = ("pending", "approved", "edited", "rejected")

KbAction = Literal["created", "edited", "approved", "rejected"]
KB_ACTION_VALUES: tuple[KbAction, ...] = ("created", "edited", "approved", "rejected")

NodeKind = Literal["tenant", "subject", "claim", "source", "category", "run"]
NODE_KIND_VALUES: tuple[NodeKind, ...] = ("tenant", "subject", "claim", "source", "category", "run")

EdgeKind = Literal[
    "reinforces",
    "contradicts",
    "refines",
    "duplicates",
    "cites_source",
    "in_category",
    "in_run",
    "in_tenant",
]
EDGE_KIND_VALUES: tuple[EdgeKind, ...] = (
    "reinforces",
    "contradicts",
    "refines",
    "duplicates",
    "cites_source",
    "in_category",
    "in_run",
    "in_tenant",
)

# Maps a reconciler decision to the inter-claim edge kind it produces.
# ``new_claim`` produces a node, not an edge, and is intentionally absent.
DECISION_TO_EDGE_KIND: dict[ReconciliationDecision, EdgeKind] = {
    "reinforces_existing": "reinforces",
    "contradicts_existing": "contradicts",
    "refines_existing": "refines",
    "duplicate": "duplicates",
}
