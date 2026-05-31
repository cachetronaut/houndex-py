from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path

from houndex_connectors import FileConnector, IngestConnectorOptions, SourceDraft, ingest_connector
from houndex_core.schemas import ExtractedClaim
from houndex_pipeline import (
    ExtractedClaimWithContext,
    ExtractInput,
    ExtractionOutcome,
    IngestionInput,
    ProcessDeps,
    SinkResult,
    SourceTierClassifier,
)


def _make_fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "docs"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (root / "b.txt").write_text("second", encoding="utf-8")
    (root / "a.md").write_text("first", encoding="utf-8")
    (nested / "c.json").write_text('{"value":true}', encoding="utf-8")
    (nested / "skip.csv").write_text("ignored", encoding="utf-8")
    return root


def test_file_connector_walks_in_sorted_relative_path_order(tmp_path: Path) -> None:
    root = _make_fixture_root(tmp_path)
    connector = FileConnector(root=root, base_url="https://docs.example.com/base/")

    async def run() -> list[tuple[str, str, str]]:
        pages = []
        async for page in connector.pages():
            pages.append((page.source_url, page.title, page.text))
        return pages

    assert asyncio.run(run()) == [
        ("https://docs.example.com/base/a.md", "a.md", "first"),
        ("https://docs.example.com/base/b.txt", "b.txt", "second"),
        ("https://docs.example.com/base/nested/c.json", "c.json", '{"value":true}'),
    ]


def test_ingest_connector_processes_pages_and_persists_sources(tmp_path: Path) -> None:
    root = _make_fixture_root(tmp_path)
    connector = FileConnector(root=root, include=[".md"], base_url="https://docs.example.com")
    sources: list[SourceDraft] = []
    embeddings: list[list[float] | None] = []

    class Embedder:
        @property
        def dimension(self) -> int:
            return 2

        async def embed(self, texts: Sequence[str]) -> list[list[float]]:
            return [[0.1, 0.9] for _text in texts]

    async def extract(input: ExtractInput) -> ExtractionOutcome:
        return ExtractionOutcome(
            kept=[
                ExtractedClaimWithContext(
                    claim=ExtractedClaim(
                        category="capability",
                        polarity="positive",
                        scope="global",
                        claim_text="Reads markdown files",
                        evidence_text="first",
                        confidence="stated",
                    ),
                    subject=input.subject,
                    source_url=input.source_url,
                    source_tier=input.source_tier,
                )
            ],
            dropped=[],
        )

    async def sink(
        _claim: ExtractedClaimWithContext, embedding: Sequence[float] | None
    ) -> SinkResult:
        embeddings.append(list(embedding) if embedding is not None else None)
        return SinkResult(claim_id="claim1", created=True)

    async def upsert_source(source: SourceDraft) -> None:
        sources.append(source)

    deps = ProcessDeps(
        classifier=SourceTierClassifier(),
        extract=extract,
        sink=sink,
        embed=Embedder(),
    )

    result = asyncio.run(
        ingest_connector(
            connector,
            IngestionInput(subject="Acme"),
            deps,
            IngestConnectorOptions(
                now=lambda: 1_700_000_000_000,
                upsert_source=upsert_source,
            ),
        )
    )

    assert result.pages_scraped == 1
    assert result.claims_created == 1
    assert embeddings == [[0.1, 0.9]]
    assert sources == [
        SourceDraft(
            url="https://docs.example.com/a.md",
            title="a.md",
            domain="example.com",
            tier="tier_4",
            fetched_at=1_700_000_000_000,
        )
    ]
