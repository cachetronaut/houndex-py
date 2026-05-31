"""houndex-pipeline — deterministic ingestion and enrichment transforms."""

from __future__ import annotations

from .chunker import chunk_text
from .content_hash import UrlBearing, content_hash, dedupe_by_url
from .enrich import EnrichmentEdge, compute_enrichment
from .orchestrator import (
    DiscoverDeps,
    ExtractedClaimWithContext,
    ExtractInput,
    ExtractionOutcome,
    IngestionDeps,
    IngestionInput,
    IngestionResult,
    ProcessDeps,
    SinkResult,
    discover_pages,
    process_pages,
    run_ingestion,
)
from .source_tier import SourceTierClassifier, SourceTierRubric
from .source_tier_loader import load_source_tier_classifier

__all__ = [
    "EnrichmentEdge",
    "DiscoverDeps",
    "ExtractInput",
    "ExtractedClaimWithContext",
    "ExtractionOutcome",
    "IngestionDeps",
    "IngestionInput",
    "IngestionResult",
    "ProcessDeps",
    "SinkResult",
    "SourceTierClassifier",
    "SourceTierRubric",
    "UrlBearing",
    "chunk_text",
    "compute_enrichment",
    "content_hash",
    "dedupe_by_url",
    "discover_pages",
    "load_source_tier_classifier",
    "process_pages",
    "run_ingestion",
]
