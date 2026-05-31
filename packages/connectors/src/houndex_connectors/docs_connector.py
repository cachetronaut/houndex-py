"""DocsConnector — crawl a documentation site from a single seed and yield pages.

It does not follow links recursively. It reads exactly one seed — a
``sitemap.xml`` or an HTML index/nav page — extracts the candidate URLs, applies
conservative filtering (same-origin, optional path-prefix, dedupe, page cap),
then delegates the actual fetching to a ``WebConnector``. Discovery and fetching
stay separate: this connector decides *which* URLs, the web connector decides
*how* to fetch them. A failed or non-2xx seed is reported through ``on_error``
and yields zero pages rather than raising. Mirrors the TypeScript
``DocsConnector``.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator, Callable, Sequence
from urllib.parse import urljoin, urlsplit

from houndex_core.providers import ScrapedPage

from .web_connector import Fetcher, WebConnector, WebConnectorError

_DEFAULT_MAX_PAGES = 100
_LOC_PATTERN = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.IGNORECASE)
_HREF_PATTERN = re.compile(r"""<a\s[^>]*href=["']([^"']+)["']""", re.IGNORECASE)


class DocsConnector:
    name = "docs"

    def __init__(
        self,
        *,
        fetcher: Fetcher | None = None,
        sitemap_url: str | None = None,
        index_url: str | None = None,
        include: str | None = None,
        max_pages: int = _DEFAULT_MAX_PAGES,
        on_error: Callable[[WebConnectorError], None] | None = None,
    ) -> None:
        if (sitemap_url is None) == (index_url is None):
            raise ValueError("DocsConnector requires exactly one of sitemap_url or index_url")
        if sitemap_url is not None:
            self._seed_url = sitemap_url
            self._kind = "sitemap"
        else:
            assert index_url is not None
            self._seed_url = index_url
            self._kind = "index"
        self._fetcher = fetcher
        self._include = include
        self._max_pages = max_pages
        self._on_error = on_error

    async def pages(self) -> AsyncIterator[ScrapedPage]:
        fetcher = self._fetcher
        if fetcher is None:
            from .web_connector import DefaultFetcher

            fetcher = DefaultFetcher()
        try:
            response = await fetcher.fetch(self._seed_url)
        except Exception as error:  # noqa: BLE001 — a bad seed must not raise
            self._report(self._seed_url, error)
            return
        if response.status < 200 or response.status >= 300:
            self._report(
                self._seed_url,
                RuntimeError(f"seed fetch failed with status {response.status}"),
            )
            return

        if self._kind == "sitemap":
            candidates = extract_sitemap_urls(response.text)
        else:
            candidates = extract_index_urls(response.text, self._seed_url)
        urls = filter_doc_urls(candidates, self._seed_url, self._include)[: self._max_pages]

        web = WebConnector(urls=urls, fetcher=fetcher, on_error=self._on_error)
        async for page in web.pages():
            yield page

    def _report(self, url: str, error: object) -> None:
        if self._on_error is not None:
            self._on_error(WebConnectorError(url=url, error=error))


def extract_sitemap_urls(xml: str) -> list[str]:
    """Parse ``<loc>`` entries out of a sitemap. Nested sitemap indexes are
    treated as plain URLs; later filtering drops anything off-origin or off-prefix.
    """
    return [_decode_xml_entities(match) for match in _LOC_PATTERN.findall(xml)]


def extract_index_urls(html: str, base_url: str) -> list[str]:
    """Parse ``<a href>`` targets out of an HTML index/nav page, resolving
    relative hrefs against the index URL. Fragment-only hrefs are skipped.
    """
    urls: list[str] = []
    for href in _HREF_PATTERN.findall(html):
        if href and not href.startswith("#"):
            urls.append(urljoin(base_url, _decode_xml_entities(href)))
    return urls


def filter_doc_urls(
    candidates: Sequence[str],
    seed_url: str,
    include: str | None = None,
) -> list[str]:
    """Keep only http(s) URLs that share the seed's origin and (if given) start
    with the include prefix, deduped while preserving discovery order.
    """
    seed = urlsplit(seed_url)
    seed_origin = (seed.scheme, seed.netloc)
    seen: set[str] = set()
    kept: list[str] = []
    for candidate in candidates:
        parts = urlsplit(candidate)
        if parts.scheme not in ("http", "https"):
            continue
        if (parts.scheme, parts.netloc) != seed_origin:
            continue
        if include is not None and not parts.path.startswith(include):
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        kept.append(candidate)
    return kept


def _decode_xml_entities(value: str) -> str:
    return (
        value.replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", '"')
        .replace("&#39;", "'")
    )
