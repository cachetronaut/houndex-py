from __future__ import annotations

from houndex_pipeline import chunk_text


def test_single_chunk_when_short() -> None:
    assert chunk_text("short text") == ["short text"]


def test_respects_target_and_overlaps() -> None:
    chunks = chunk_text("a" * 3000, 1000, 100)
    assert len(chunks) > 1
    assert all(len(chunk) <= 1000 for chunk in chunks)


def test_breaks_on_paragraph_boundary() -> None:
    text = "First paragraph.\n\n" + ("b" * 1500)
    chunks = chunk_text(text, 1000, 50)
    assert "First paragraph." in chunks[0]


def test_empty_input() -> None:
    assert chunk_text("") == []
    assert chunk_text("   ") == []
