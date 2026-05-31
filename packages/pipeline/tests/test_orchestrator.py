from __future__ import annotations

import asyncio
from collections.abc import Sequence

from houndex_core.providers import ScrapedPage, SearchResult
from houndex_core.schemas import ExtractedClaim, SearchPlan, SearchQuery
from houndex_pipeline import (
    ExtractedClaimWithContext,
    ExtractInput,
    ExtractionOutcome,
    IngestionDeps,
    IngestionInput,
    ProcessDeps,
    SinkResult,
    SourceTierClassifier,
    process_pages,
    run_ingestion,
)

_PLAN = SearchPlan(subject="Acme", queries=[SearchQuery(query="q", intent="i")])


class _Search:
    def __init__(self, results: list[SearchResult]) -> None:
        self._results = results

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        return list(self._results)


class _Scrape:
    def __init__(self, text: str = "body") -> None:
        self._text = text

    async def scrape(self, url: str) -> ScrapedPage | None:
        return ScrapedPage(source_url=url, title="t", text=self._text)


def _base_claim() -> ExtractedClaimWithContext:
    return ExtractedClaimWithContext(
        claim=ExtractedClaim(
            category="capability",
            polarity="positive",
            scope="global",
            claim_text="Claim text here",
            evidence_text="Evidence quote",
            confidence="stated",
        ),
        subject="Acme",
        source_url="https://example.com/a",
        source_tier="tier_3",
    )


def _make_deps(
    *,
    results: list[SearchResult] | None = None,
    created: bool = True,
) -> IngestionDeps:
    async def plan(_: IngestionInput) -> SearchPlan:
        return _PLAN

    async def extract(_: ExtractInput) -> ExtractionOutcome:
        return ExtractionOutcome(kept=[_base_claim()], dropped=[])

    async def sink(
        _claim: ExtractedClaimWithContext, _embedding: Sequence[float] | None
    ) -> SinkResult:
        return SinkResult(claim_id="id1", created=created)

    return IngestionDeps(
        plan=plan,
        search=_Search(
            results or [SearchResult(url="https://example.com/a", title="t", snippet="s")]
        ),
        scrape=_Scrape(),
        classifier=SourceTierClassifier(),
        extract=extract,
        sink=sink,
    )


def test_runs_full_pipeline() -> None:
    result = asyncio.run(run_ingestion(IngestionInput(subject="Acme"), _make_deps()))
    assert result.pages_scraped == 1
    assert result.claims_extracted == 1
    assert result.claims_created == 1


def test_dedupes_identical_page_text() -> None:
    results = [
        SearchResult(url="https://example.com/a", title="t", snippet="s"),
        SearchResult(url="https://example.com/b", title="t", snippet="s"),
    ]
    result = asyncio.run(run_ingestion(IngestionInput(subject="Acme"), _make_deps(results=results)))
    # Both URLs scrape to identical text, so only one page survives.
    assert result.pages_scraped == 1


def test_counts_deduped_sink() -> None:
    result = asyncio.run(run_ingestion(IngestionInput(subject="Acme"), _make_deps(created=False)))
    assert result.claims_created == 0
    assert result.claims_deduped == 1


def _make_process_deps(*, created: bool = True) -> ProcessDeps:
    async def extract(input: ExtractInput) -> ExtractionOutcome:
        claim = _base_claim()
        return ExtractionOutcome(
            kept=[
                ExtractedClaimWithContext(
                    claim=claim.claim,
                    subject=input.subject,
                    source_url=input.source_url,
                    source_tier=input.source_tier,
                )
            ],
            dropped=[],
        )

    async def sink(
        _claim: ExtractedClaimWithContext, _embedding: Sequence[float] | None
    ) -> SinkResult:
        return SinkResult(claim_id="id1", created=created)

    return ProcessDeps(classifier=SourceTierClassifier(), extract=extract, sink=sink)


def test_process_pages_dedupes_identical_page_text() -> None:
    pages = [
        ScrapedPage(source_url="https://example.com/a", title="A", text="body"),
        ScrapedPage(source_url="https://example.com/b", title="B", text="body"),
    ]
    result = asyncio.run(process_pages(pages, IngestionInput(subject="Acme"), _make_process_deps()))
    assert result.pages_scraped == 1
    assert result.claims_created == 1


def test_process_pages_survives_extract_failure() -> None:
    failed: list[str] = []

    async def extract(input: ExtractInput) -> ExtractionOutcome:
        if "/bad" in input.source_url:
            raise TypeError("extract failed")
        return ExtractionOutcome(kept=[_base_claim()], dropped=[])

    async def sink(
        _claim: ExtractedClaimWithContext, _embedding: Sequence[float] | None
    ) -> SinkResult:
        return SinkResult(claim_id="id1", created=True)

    deps = ProcessDeps(
        classifier=SourceTierClassifier(),
        extract=extract,
        sink=sink,
        on_page_error=lambda source_url, _error: failed.append(source_url),
    )
    pages = [
        ScrapedPage(source_url="https://example.com/good", title="Good", text="good body"),
        ScrapedPage(source_url="https://example.com/bad", title="Bad", text="bad body"),
    ]

    result = asyncio.run(process_pages(pages, IngestionInput(subject="Acme"), deps))

    assert result.pages_scraped == 2
    assert result.pages_failed == 1
    assert result.claims_created == 1
    assert failed == ["https://example.com/bad"]


def test_process_pages_passes_embedding_to_sink() -> None:
    embeddings: list[list[float] | None] = []

    class Embedder:
        @property
        def dimension(self) -> int:
            return 2

        async def embed(self, texts: Sequence[str]) -> list[list[float]]:
            return [[0.25, 0.75] for _text in texts]

    async def sink(
        _claim: ExtractedClaimWithContext, embedding: Sequence[float] | None
    ) -> SinkResult:
        embeddings.append(list(embedding) if embedding is not None else None)
        return SinkResult(claim_id="id1", created=False)

    deps = _make_process_deps(created=False)
    deps.embed = Embedder()
    deps.sink = sink
    result = asyncio.run(
        process_pages(
            [ScrapedPage(source_url="https://example.com/a", title="A", text="body")],
            IngestionInput(subject="Acme"),
            deps,
        )
    )

    assert result.claims_created == 0
    assert result.claims_deduped == 1
    assert embeddings == [[0.25, 0.75]]
