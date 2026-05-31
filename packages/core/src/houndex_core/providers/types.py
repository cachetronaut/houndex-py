"""Provider ports — the swap surface between pipeline code and external
services. The pipeline depends only on these protocols, so adding or changing a
provider needs no pipeline-code change. Concrete implementations live in adapter
packages, never here.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class SearchResult(BaseModel):
    url: str
    title: str
    snippet: str
    score: float | None = None


class ScrapedPage(BaseModel):
    source_url: str
    title: str
    text: str


class RerankHit(BaseModel):
    index: int
    score: float


@runtime_checkable
class SearchProvider(Protocol):
    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]: ...


@runtime_checkable
class Scraper(Protocol):
    async def scrape(self, url: str) -> ScrapedPage | None: ...


@runtime_checkable
class Embedder(Protocol):
    @property
    def dimension(self) -> int: ...

    async def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


@runtime_checkable
class Reranker(Protocol):
    async def rerank(
        self, query: str, documents: Sequence[str], top_n: int | None = None
    ) -> list[RerankHit]: ...
