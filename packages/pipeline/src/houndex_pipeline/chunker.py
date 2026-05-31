"""Deterministic text chunker for embedding. Caps each chunk at ``target_chars``
then walks back to the nearest paragraph/sentence/whitespace boundary; adjacent
chunks share a fixed-size overlap window. Mirrors the TypeScript ``chunkText`` so
chunk boundaries — and the content hashes derived from them — agree across
languages.
"""

from __future__ import annotations

_BOUNDARY_PREFERENCE = ("\n\n", ". ", "\n", " ")


def chunk_text(text: str, target_chars: int = 1200, overlap_chars: int = 100) -> list[str]:
    trimmed = text.strip()
    if trimmed == "":
        return []
    if len(trimmed) <= target_chars:
        return [trimmed]

    chunks: list[str] = []
    cursor = 0
    length = len(trimmed)

    while cursor < length:
        end = min(cursor + target_chars, length)
        if end < length:
            window = trimmed[cursor:end]
            for separator in _BOUNDARY_PREFERENCE:
                position = window.rfind(separator)
                if position > target_chars // 2:
                    end = cursor + position + len(separator)
                    break
        chunk = trimmed[cursor:end].strip()
        if chunk != "":
            chunks.append(chunk)
        next_cursor = end - overlap_chars if overlap_chars > 0 else end
        cursor = max(next_cursor, cursor + 1)

    return chunks
