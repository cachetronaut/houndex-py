"""Cross-language parity.

Loads the same ``core-vectors.json`` the TypeScript core asserts against and
verifies the Python primitives reproduce every expected value byte-for-byte. If
the two languages diverge, this fails.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from houndex_core import canonical_json, compute_claim_id
from houndex_core.schemas import canonicalize_url, edge_idempotency_key

_VECTORS = json.loads((Path(__file__).parent / "core-vectors.json").read_text())


@pytest.mark.parametrize("case", _VECTORS["claimId"])
def test_claim_id(case: dict[str, Any]) -> None:
    case_input = case["input"]
    assert (
        compute_claim_id(
            tenant_id=case_input["tenantId"],
            subject=case_input["subject"],
            claim_text=case_input["claimText"],
            source_url=case_input["sourceUrl"],
        )
        == case["expected"]
    )


@pytest.mark.parametrize("case", _VECTORS["edgeIdempotencyKey"])
def test_edge_idempotency_key(case: dict[str, Any]) -> None:
    case_input = case["input"]
    assert (
        edge_idempotency_key(
            src_id=case_input["srcId"], dst_id=case_input["dstId"], kind=case_input["kind"]
        )
        == (case["expected"])
    )


@pytest.mark.parametrize("case", _VECTORS["canonicalizeUrl"])
def test_canonicalize_url(case: dict[str, Any]) -> None:
    assert canonicalize_url(case["input"]) == case["expected"]


@pytest.mark.parametrize("case", _VECTORS["canonicalJson"])
def test_canonical_json(case: dict[str, Any]) -> None:
    assert canonical_json(case["input"]) == case["expected"]
