"""Canonical JSON serialization — deterministic, key-sorted output so the same
logical value always produces the same bytes. Mirrors the TypeScript
``canonicalJson`` exactly so a value serialized in either language is identical.

Rules:
  - object keys are sorted lexicographically (by code point)
  - arrays preserve order
  - ``None`` serializes to ``null``
  - no insignificant whitespace
  - non-finite floats are rejected (they have no portable JSON form)
"""

from __future__ import annotations

import json
import math
from typing import Any


def canonical_json(value: Any) -> str:
    if value is None:
        return "null"
    # bool must be checked before int (bool is a subclass of int).
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"canonical_json: non-finite number is not serializable: {value}")
        return json.dumps(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (list, tuple)):
        return "[" + ",".join(canonical_json(item) for item in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value.keys())
        entries = (
            json.dumps(key, ensure_ascii=False) + ":" + canonical_json(value[key]) for key in keys
        )
        return "{" + ",".join(entries) + "}"
    raise TypeError(f"canonical_json: unsupported type {type(value).__name__}")
