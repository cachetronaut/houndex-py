from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from houndex_core.providers import ScrapedPage
from houndex_core.schemas import SourceTier, canonicalize_url, extract_domain
from houndex_pipeline import IngestionInput, IngestionResult, ProcessDeps, process_pages


class Connector(Protocol):
    name: str

    def pages(self) -> AsyncIterator[ScrapedPage]: ...


@dataclass(frozen=True)
class SourceDraft:
    url: str
    title: str
    domain: str
    tier: SourceTier
    fetched_at: int


@dataclass(frozen=True)
class IngestConnectorOptions:
    upsert_source: Callable[[SourceDraft], Awaitable[None]] | None = None
    now: Callable[[], int] | None = None


async def ingest_connector(
    connector: Connector,
    input: IngestionInput,
    deps: ProcessDeps,
    options: IngestConnectorOptions | None = None,
) -> IngestionResult:
    settings = options or IngestConnectorOptions()
    pages: list[ScrapedPage] = []
    async for page in connector.pages():
        pages.append(page)
        if settings.upsert_source is not None:
            await settings.upsert_source(_source_draft_for_page(page, input, deps, settings.now))
    return await process_pages(pages, input, deps)


def _source_draft_for_page(
    page: ScrapedPage,
    input: IngestionInput,
    deps: ProcessDeps,
    now: Callable[[], int] | None,
) -> SourceDraft:
    url = canonicalize_url(page.source_url)
    return SourceDraft(
        url=url,
        title=page.title,
        domain=extract_domain(url),
        tier=deps.classifier.classify(page.source_url, input.subject),
        fetched_at=now() if now is not None else int(time.time() * 1000),
    )
