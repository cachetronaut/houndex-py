from __future__ import annotations

import re
from dataclasses import dataclass

from houndex_pipeline import content_hash, dedupe_by_url


def test_content_hash_is_deterministic_hex() -> None:
    digest = content_hash("hello world")
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    assert content_hash("hello world") == digest


def test_content_hash_differs() -> None:
    assert content_hash("a") != content_hash("b")


@dataclass
class _Item:
    url: str
    n: int


def test_dedupe_by_url_preserves_first_seen() -> None:
    items = [
        _Item("https://a.com", 1),
        _Item("https://b.com", 2),
        _Item("https://a.com", 3),
    ]
    assert dedupe_by_url(items) == [_Item("https://a.com", 1), _Item("https://b.com", 2)]
