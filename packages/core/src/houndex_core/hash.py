"""SHA-256 hex digest. Mirrors the TypeScript ``sha256Hex`` so content-addressed
identifiers are byte-for-byte identical across the two implementations."""

from __future__ import annotations

import hashlib


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
