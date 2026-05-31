from __future__ import annotations

import math

import pytest
from houndex_core import canonical_json


def test_sorts_object_keys() -> None:
    assert canonical_json({"b": 1, "a": 2, "c": 3}) == '{"a":2,"b":1,"c":3}'


def test_independent_of_insertion_order() -> None:
    assert canonical_json({"z": 1, "a": {"y": 2, "x": 3}}) == canonical_json(
        {"a": {"x": 3, "y": 2}, "z": 1}
    )


def test_preserves_array_order() -> None:
    assert canonical_json([3, 1, 2]) == "[3,1,2]"


def test_serializes_null_and_booleans() -> None:
    assert canonical_json({"a": None, "b": True}) == '{"a":null,"b":true}'


def test_rejects_non_finite() -> None:
    with pytest.raises(ValueError):
        canonical_json(math.inf)
    with pytest.raises(ValueError):
        canonical_json(math.nan)
