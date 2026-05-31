"""Ingestion pipeline orchestration — the deterministic spine that sequences:
plan -> search -> dedupe -> scrape -> classify tier -> chunk -> extract ->
(embed) -> sink. Dependency-injected over the provider/extractor ports, so the
whole sequence is testable offline with in-memory fakes. Mirrors the TypeScript
``runIngestion``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field

from houndex_core.providers import Embedder, ScrapedPage, Scraper, SearchProvider, SearchResult
from houndex_core.schemas import ExtractedClaim, SearchPlan, SourceTier

from .chunker import chunk_text
from .content_hash import content_hash, dedupe_by_url
from .source_tier import SourceTierClassifier

_DEFAULT_MAX_PAGES = 25
_DEFAULT_EXTRACTION_CONCURRENCY = 4


@dataclass(frozen=True)
class ExtractedClaimWithContext:
    claim: ExtractedClaim
    subject: str
    source_url: str
    source_tier: SourceTier


@dataclass(frozen=True)
class ExtractionOutcome:
    kept: list[ExtractedClaimWithContext] = field(default_factory=list)
    dropped: list[tuple[ExtractedClaim, str]] = field(default_factory=list)


@dataclass(frozen=True)
class IngestionInput:
    subject: str
    signal: str | None = None


@dataclass(frozen=True)
class ExtractInput:
    subject: str
    source_url: str
    source_tier: SourceTier
    page_text: str


@dataclass(frozen=True)
class SinkResult:
    claim_id: str
    created: bool


@dataclass
class DiscoverDeps:
    plan: Callable[[IngestionInput], Awaitable[SearchPlan]]
    search: SearchProvider
    scrape: Scraper
    max_results_per_query: int = 5
    max_pages: int = _DEFAULT_MAX_PAGES
    on_page_error: Callable[[str, BaseException], None] | None = None


@dataclass
class ProcessDeps:
    classifier: SourceTierClassifier
    extract: Callable[[ExtractInput], Awaitable[ExtractionOutcome]]
    sink: Callable[[ExtractedClaimWithContext, list[float] | None], Awaitable[SinkResult]]
    embed: Embedder | None = None
    extraction_concurrency: int = _DEFAULT_EXTRACTION_CONCURRENCY
    on_page_error: Callable[[str, BaseException], None] | None = None


@dataclass
class IngestionDeps:
    plan: Callable[[IngestionInput], Awaitable[SearchPlan]]
    search: SearchProvider
    scrape: Scraper
    classifier: SourceTierClassifier
    extract: Callable[[ExtractInput], Awaitable[ExtractionOutcome]]
    sink: Callable[[ExtractedClaimWithContext, list[float] | None], Awaitable[SinkResult]]
    embed: Embedder | None = None
    max_results_per_query: int = 5
    max_pages: int = _DEFAULT_MAX_PAGES
    extraction_concurrency: int = _DEFAULT_EXTRACTION_CONCURRENCY
    on_page_error: Callable[[str, BaseException], None] | None = None


@dataclass
class IngestionResult:
    pages_scraped: int = 0
    pages_failed: int = 0
    claims_extracted: int = 0
    claims_dropped: int = 0
    claims_created: int = 0
    claims_deduped: int = 0
    scraped_hashes: list[str] = field(default_factory=list)


async def discover_pages(input: IngestionInput, deps: DiscoverDeps) -> list[ScrapedPage]:
    plan = await deps.plan(input)

    # Search every planned query, then dedupe by canonical URL.
    all_results: list[SearchResult] = []
    for query in plan.queries:
        all_results.extend(await deps.search.search(query.query, deps.max_results_per_query))
    # Cap the candidate set *before* scraping. URL-dedupe first (cheap,
    # deterministic), then take the head — search providers return best-first.
    unique = dedupe_by_url(all_results)[: deps.max_pages]

    async def _safe_scrape(url: str) -> ScrapedPage | None:
        try:
            return await deps.scrape.scrape(url)
        except BaseException as error:  # noqa: BLE001 — one failure must not abort the run
            if deps.on_page_error is not None:
                deps.on_page_error(url, error)
            return None

    scraped = await asyncio.gather(*(_safe_scrape(source.url) for source in unique))
    return [page for page in scraped if page is not None]


async def process_pages(
    pages: Sequence[ScrapedPage], input: IngestionInput, deps: ProcessDeps
) -> IngestionResult:
    # Content-hash dedupe runs sequentially so the kept set is deterministic
    # regardless of scrape completion order (identical page text kept once).
    result = IngestionResult()
    seen_hashes: set[str] = set()
    unique_pages: list[ScrapedPage] = []
    for page in pages:
        digest = content_hash(page.text)
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        result.pages_scraped += 1
        result.scraped_hashes.append(digest)
        unique_pages.append(page)

    # Extraction is the model-bound bottleneck. Process pages in concurrent
    # batches; each page's classify + chunk + embed + extract is independent.
    concurrency = max(1, deps.extraction_concurrency)
    sinkable: list[tuple[list[ExtractedClaimWithContext], list[float] | None]] = []

    async def _process(
        page: ScrapedPage,
    ) -> tuple[list[ExtractedClaimWithContext], list[float] | None] | None:
        source_tier = deps.classifier.classify(page.source_url, input.subject)
        chunks = chunk_text(page.text)
        embedding: list[float] | None = None
        if deps.embed is not None and chunks:
            embedding = (await deps.embed.embed([chunks[0]]))[0]
        try:
            outcome = await deps.extract(
                ExtractInput(
                    subject=input.subject,
                    source_url=page.source_url,
                    source_tier=source_tier,
                    page_text=page.text,
                )
            )
        except BaseException as error:  # noqa: BLE001 — per-page failure is non-fatal
            result.pages_failed += 1
            if deps.on_page_error is not None:
                deps.on_page_error(page.source_url, error)
            return None
        result.claims_extracted += len(outcome.kept)
        result.claims_dropped += len(outcome.dropped)
        return (outcome.kept, embedding)

    for offset in range(0, len(unique_pages), concurrency):
        batch = unique_pages[offset : offset + concurrency]
        for outcome in await asyncio.gather(*(_process(page) for page in batch)):
            if outcome is not None:
                sinkable.append(outcome)

    # Sink sequentially — it mutates shared counters and the content-addressed
    # store dedupes by id, so serial writes keep that race-free.
    for kept, embedding in sinkable:
        for claim in kept:
            sunk = await deps.sink(claim, embedding)
            if sunk.created:
                result.claims_created += 1
            else:
                result.claims_deduped += 1

    return result


async def run_ingestion(input: IngestionInput, deps: IngestionDeps) -> IngestionResult:
    pages = await discover_pages(
        input,
        DiscoverDeps(
            plan=deps.plan,
            search=deps.search,
            scrape=deps.scrape,
            max_results_per_query=deps.max_results_per_query,
            max_pages=deps.max_pages,
            on_page_error=deps.on_page_error,
        ),
    )
    return await process_pages(
        pages,
        input,
        ProcessDeps(
            classifier=deps.classifier,
            extract=deps.extract,
            sink=deps.sink,
            embed=deps.embed,
            extraction_concurrency=deps.extraction_concurrency,
            on_page_error=deps.on_page_error,
        ),
    )
