from __future__ import annotations

from houndex_pipeline import EnrichmentEdge, compute_enrichment


def test_counts_corroboration_and_contradictions() -> None:
    edges = [
        EnrichmentEdge("c1", "c2", "reinforces"),
        EnrichmentEdge("c3", "c1", "reinforces"),
        EnrichmentEdge("c1", "c4", "contradicts"),
        EnrichmentEdge("c1", "c5", "refines"),
    ]
    enrichment = compute_enrichment(claim_id="c1", edges=edges)
    assert enrichment.corroboration_count["reinforces"] == 2
    assert enrichment.corroboration_count["refines"] == 1
    assert enrichment.contradiction_count == 1


def test_tallies_source_tier_distribution() -> None:
    edges = [
        EnrichmentEdge("c1", "s1", "cites_source", {"tier": "tier_1"}),
        EnrichmentEdge("c1", "s2", "cites_source", {"tier": "tier_1"}),
        EnrichmentEdge("c1", "s3", "cites_source", {"tier": "tier_3"}),
    ]
    enrichment = compute_enrichment(claim_id="c1", edges=edges)
    assert enrichment.source_count == 3
    assert enrichment.source_tier_distribution["tier_1"] == 2
    assert enrichment.source_tier_distribution["tier_3"] == 1


def test_ignores_non_incident_edges() -> None:
    edges = [EnrichmentEdge("x", "y", "reinforces")]
    enrichment = compute_enrichment(claim_id="c1", edges=edges)
    assert enrichment.corroboration_count == {}
    assert enrichment.source_count == 0
