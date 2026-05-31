from __future__ import annotations

from houndex_core import compute_claim_id

BASE = {
    "tenant_id": "primary",
    "subject": "Acme",
    "claim_text": "Ships a hosted control plane",
    "source_url": "https://example.com/docs/control-plane",
}


def test_is_16_hex() -> None:
    import re

    assert re.fullmatch(r"[0-9a-f]{16}", compute_claim_id(**BASE))


def test_deterministic() -> None:
    assert compute_claim_id(**BASE) == compute_claim_id(**BASE)


def test_collapses_text_whitespace_and_case() -> None:
    assert compute_claim_id(**{**BASE, "claim_text": "  Ships a   hosted CONTROL plane "}) == (
        compute_claim_id(**BASE)
    )


def test_ignores_url_scheme_query_fragment_and_trailing_slash() -> None:
    noisy = "http://example.com/docs/control-plane/?utm_source=x#section"
    assert compute_claim_id(**{**BASE, "source_url": noisy}) == compute_claim_id(**BASE)


def test_isolated_by_tenant() -> None:
    assert compute_claim_id(**{**BASE, "tenant_id": "secondary"}) != compute_claim_id(**BASE)
