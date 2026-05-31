"""Convenience loader: build a ``SourceTierClassifier`` from a JSON rubric string
or an already-parsed mapping. File I/O stays out of the package — callers read
the file and pass the contents.
"""

from __future__ import annotations

import json

from .source_tier import SourceTierClassifier, SourceTierRubric


def load_source_tier_classifier(rubric: str | SourceTierRubric) -> SourceTierClassifier:
    parsed: SourceTierRubric = json.loads(rubric) if isinstance(rubric, str) else rubric
    return SourceTierClassifier(parsed)
