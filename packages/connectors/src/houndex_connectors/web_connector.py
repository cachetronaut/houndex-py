from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass
from typing import Protocol
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from houndex_core.providers import ScrapedPage
from houndex_core.schemas import canonicalize_url

_DEFAULT_CONCURRENCY = 4


@dataclass(frozen=True)
class FetchResponse:
    status: int
    text: str


class Fetcher(Protocol):
    async def fetch(self, url: str) -> FetchResponse: ...


@dataclass(frozen=True)
class WebConnectorError:
    url: str
    error: object


class DefaultFetcher:
    async def fetch(self, url: str) -> FetchResponse:
        return await asyncio.to_thread(_fetch_sync, url)


class WebConnector:
    name = "web"

    def __init__(
        self,
        *,
        urls: Sequence[str],
        fetcher: Fetcher | None = None,
        concurrency: int = _DEFAULT_CONCURRENCY,
        on_error: Callable[[WebConnectorError], None] | None = None,
    ) -> None:
        self._urls = list(urls)
        self._fetcher = fetcher or DefaultFetcher()
        self._concurrency = max(1, concurrency)
        self._on_error = on_error

    async def pages(self) -> AsyncIterator[ScrapedPage]:
        for offset in range(0, len(self._urls), self._concurrency):
            batch = self._urls[offset : offset + self._concurrency]
            pages = await asyncio.gather(*(self._fetch_page(url) for url in batch))
            for page in pages:
                if page is not None:
                    yield page

    async def _fetch_page(self, url: str) -> ScrapedPage | None:
        try:
            response = await self._fetcher.fetch(url)
            if response.status < 200 or response.status >= 300:
                self._emit_error(url, RuntimeError(f"fetch failed with status {response.status}"))
                return None
            source_url = canonicalize_url(url)
            return ScrapedPage(
                source_url=source_url,
                title=_title_for_url(source_url),
                text=response.text,
            )
        except Exception as error:  # noqa: BLE001 — one failed URL must not abort the run
            self._emit_error(url, error)
            return None

    def _emit_error(self, url: str, error: object) -> None:
        if self._on_error is not None:
            self._on_error(WebConnectorError(url=url, error=error))


def _fetch_sync(url: str) -> FetchResponse:
    request = Request(url, headers={"User-Agent": "houndex-connectors/0.1"})
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 — explicit user URLs only
            status = response.status
            charset = response.headers.get_content_charset() or "utf-8"
            text = response.read().decode(charset, errors="replace")
            return FetchResponse(status=status, text=text)
    except HTTPError as error:
        text = error.read().decode("utf-8", errors="replace")
        return FetchResponse(status=error.code, text=text)


def _title_for_url(url: str) -> str:
    parts = urlsplit(url)
    return parts.netloc if parts.path in ("", "/") else f"{parts.netloc}{parts.path}"
