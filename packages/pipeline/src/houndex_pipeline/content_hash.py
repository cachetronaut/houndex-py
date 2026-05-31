"""Content hashing + canonical-URL dedupe. The content hash keys idempotent
pipeline steps; the dedupe pass is unique-by-canonical-URL preserving first-seen
order. Mirrors the TypeScript ``contentHash`` / ``dedupeByUrl``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, TypeVar, runtime_checkable

from houndex_core import sha256_hex
from houndex_core.schemas import canonicalize_url


def content_hash(text: str) -> str:
    return sha256_hex(text)


@runtime_checkable
class UrlBearing(Protocol):
    url: str


T = TypeVar("T", bound=UrlBearing)


def dedupe_by_url(results: Sequence[T]) -> list[T]:
    """Unique-by-canonical-URL, preserving first-seen order."""
    seen: set[str] = set()
    unique: list[T] = []
    for result in results:
        key = canonicalize_url(result.url)
        if key in seen:
            continue
        seen.add(key)
        unique.append(result)
    return unique
