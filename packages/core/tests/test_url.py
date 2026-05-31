from __future__ import annotations

import pytest
from houndex_core.schemas import canonicalize_url, extract_domain


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("HTTPS://Example.COM/Docs/", "https://example.com/Docs"),
        ("http://example.com:80/a", "http://example.com/a"),
        ("https://example.com:443/a", "https://example.com/a"),
        ("https://example.com/a?b=2&utm_source=x&a=1", "https://example.com/a?a=1&b=2"),
        ("example.com/a", "https://example.com/a"),
    ],
)
def test_canonicalize_url(raw: str, expected: str) -> None:
    assert canonicalize_url(raw) == expected


def test_extract_domain() -> None:
    assert extract_domain("https://docs.example.com/a") == "example.com"
    assert extract_domain("https://example.com") == "example.com"
    assert extract_domain("   ") == ""
