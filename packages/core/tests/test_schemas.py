from __future__ import annotations

import pytest
from houndex_core import compute_claim_id
from houndex_core.schemas import (
    CATEGORY_VALUES,
    DECISION_TO_EDGE_KIND,
    Claim,
    OutputEnvelope,
    ReconciliationResult,
    edge_idempotency_key,
)
from pydantic import ValidationError


def _claim(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "tenant_id": "primary",
        "claim_id": compute_claim_id(
            tenant_id="primary",
            subject="Acme",
            claim_text="Has an audit log",
            source_url="https://example.com/security",
        ),
        "subject": "Acme",
        "category": "security",
        "polarity": "positive",
        "scope": "global",
        "claim_text": "Has an audit log",
        "evidence_text": "The product ships an immutable audit log.",
        "confidence": "stated",
        "source_url": "https://example.com/security",
        "source_tier": "tier_2",
        "extracted_at": 1_700_000_000_000,
    }
    data.update(overrides)
    return data


def test_claim_parses() -> None:
    assert Claim.model_validate(_claim()).subject == "Acme"


def test_claim_rejects_unknown_category() -> None:
    with pytest.raises(ValidationError):
        Claim.model_validate(_claim(category="market_share"))


def test_claim_rejects_malformed_id() -> None:
    with pytest.raises(ValidationError):
        Claim.model_validate(_claim(claim_id="nothex"))


def test_taxonomy() -> None:
    assert len(CATEGORY_VALUES) > 0
    assert DECISION_TO_EDGE_KIND["reinforces_existing"] == "reinforces"
    assert "new_claim" not in DECISION_TO_EDGE_KIND


def test_edge_idempotency_key_stability() -> None:
    first_key = edge_idempotency_key(src_id="claim:1", dst_id="claim:2", kind="reinforces")
    second_key = edge_idempotency_key(src_id="claim:1", dst_id="claim:2", kind="reinforces")
    assert first_key == second_key
    assert edge_idempotency_key(src_id="claim:1", dst_id="claim:2", kind="contradicts") != first_key


def test_envelope_defaults() -> None:
    env = OutputEnvelope[dict](tenant_id="primary", generated_at=1, payload={"value": "x"})
    assert env.schema_version == "v1.0.0"
    assert env.engine_version == "0.1.0"
    assert env.trace == []


def test_reconciliation_requires_match_for_non_new() -> None:
    with pytest.raises(ValidationError):
        ReconciliationResult(decision="duplicate", rationale="dup")
    with pytest.raises(ValidationError):
        ReconciliationResult(
            decision="new_claim", matched_claim_id="0123456789abcdef", rationale="x"
        )
    # valid cases
    ReconciliationResult(decision="new_claim", rationale="fresh")
    ReconciliationResult(decision="duplicate", matched_claim_id="0123456789abcdef", rationale="dup")
