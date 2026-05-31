from __future__ import annotations

import json

from houndex_pipeline import (
    SourceTierClassifier,
    SourceTierRubric,
    load_source_tier_classifier,
)

_RUBRIC: SourceTierRubric = {
    "tier_2_domains": ["trade-press.com"],
    "tier_3_domains": ["forum.example"],
    "authoritative_domains": ["sec.gov"],
}


def test_authoritative_wins() -> None:
    assert SourceTierClassifier(_RUBRIC).classify("https://www.sec.gov/filing") == "authoritative"


def test_subject_root_is_tier_1() -> None:
    assert SourceTierClassifier(_RUBRIC).classify("https://acme.com/pricing", "Acme") == "tier_1"


def test_tier_lists() -> None:
    classifier = SourceTierClassifier(_RUBRIC)
    assert classifier.classify("https://trade-press.com/post") == "tier_2"
    assert classifier.classify("https://forum.example/thread") == "tier_3"


def test_fallback_tier_4() -> None:
    assert SourceTierClassifier(_RUBRIC).classify("https://random-blog.net/x") == "tier_4"


def test_empty_rubric() -> None:
    assert SourceTierClassifier().classify("https://sec.gov/x") == "tier_4"


def test_loader_accepts_json_string_and_object() -> None:
    assert load_source_tier_classifier(json.dumps(_RUBRIC)).classify("https://sec.gov/x") == (
        "authoritative"
    )
    assert load_source_tier_classifier(_RUBRIC).classify("https://trade-press.com/x") == "tier_2"
