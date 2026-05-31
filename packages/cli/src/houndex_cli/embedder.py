"""Synthetic, deterministic embedder — the CLI's zero-dependency default, so the
whole tool runs offline with no API keys and produces stable, assertable output.
NOT a semantic model: identical text -> identical vector. The algorithm is
integer-exact and mirrors the TypeScript CLI byte-for-byte (FNV-1a/32 seeds a
32-bit LCG; each step yields one component in [-1, 1); the vector is then
L2-normalized). 32-bit arithmetic via ``& 0xFFFFFFFF`` matches JS ``Math.imul``.
"""

from __future__ import annotations

import math

_FNV_OFFSET = 0x811C9DC5
_FNV_PRIME = 0x01000193
_LCG_MULT = 1664525
_LCG_INC = 1013904223
_UINT32 = 4294967296
_MASK = 0xFFFFFFFF


def _fnv1a32(text: str) -> int:
    h = _FNV_OFFSET
    for byte in text.encode("utf-8"):
        h = ((h ^ byte) * _FNV_PRIME) & _MASK
    return h


class SyntheticEmbedder:
    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        state = _fnv1a32(text) or 1
        vector: list[float] = []
        for _ in range(self.dimensions):
            state = (_LCG_MULT * state + _LCG_INC) & _MASK
            vector.append(state / _UINT32 * 2 - 1)
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
