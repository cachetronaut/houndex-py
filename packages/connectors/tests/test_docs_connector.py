from __future__ import annotations

import asyncio

import pytest
from houndex_connectors import (
    DocsConnector,
    FetchResponse,
    extract_index_urls,
    extract_sitemap_urls,
    filter_doc_urls,
)


class FakeFetcher:
    def __init__(self, responses: dict[str, FetchResponse]) -> None:
        self._responses = responses

    async def fetch(self, url: str) -> FetchResponse:
        response = self._responses.get(url)
        if response is None:
            raise RuntimeError(f"unexpected url {url}")
        return response


def _collect(connector: DocsConnector) -> list:
    async def run() -> list:
        pages = []
        async for page in connector.pages():
            pages.append(page)
        return pages

    return asyncio.run(run())


def test_extract_sitemap_urls_reads_loc_and_decodes_entities() -> None:
    xml = (
        "<urlset><url><loc>https://example.com/docs/a</loc></url>"
        "<url><loc>https://example.com/docs/b?x=1&amp;y=2</loc></url></urlset>"
    )
    assert extract_sitemap_urls(xml) == [
        "https://example.com/docs/a",
        "https://example.com/docs/b?x=1&y=2",
    ]


def test_extract_index_urls_resolves_relative_and_skips_fragments() -> None:
    html = (
        '<a href="/docs/a">A</a><a href="guide/b">B</a>'
        '<a href="#top">skip</a><a href="https://other.com/x">X</a>'
    )
    assert extract_index_urls(html, "https://example.com/docs/index.html") == [
        "https://example.com/docs/a",
        "https://example.com/docs/guide/b",
        "https://other.com/x",
    ]


def test_filter_doc_urls_keeps_same_origin_prefix_deduped() -> None:
    candidates = [
        "https://example.com/docs/a",
        "https://other.com/docs/a",
        "https://example.com/blog/c",
        "https://example.com/docs/a",
        "ftp://example.com/docs/d",
        "https://example.com/docs/b",
    ]
    assert filter_doc_urls(candidates, "https://example.com/sitemap.xml", "/docs/") == [
        "https://example.com/docs/a",
        "https://example.com/docs/b",
    ]


def test_crawls_sitemap_filters_and_yields_pages() -> None:
    responses = {
        "https://example.com/sitemap.xml": FetchResponse(
            status=200,
            text=(
                "<urlset><url><loc>https://example.com/docs/a</loc></url>"
                "<url><loc>https://example.com/blog/skip</loc></url>"
                "<url><loc>https://example.com/docs/b</loc></url></urlset>"
            ),
        ),
        "https://example.com/docs/a": FetchResponse(status=200, text="a"),
        "https://example.com/docs/b": FetchResponse(status=200, text="b"),
    }
    connector = DocsConnector(
        fetcher=FakeFetcher(responses),
        sitemap_url="https://example.com/sitemap.xml",
        include="/docs/",
    )
    pages = _collect(connector)
    assert [page.source_url for page in pages] == [
        "https://example.com/docs/a",
        "https://example.com/docs/b",
    ]
    assert [page.text for page in pages] == ["a", "b"]


def test_respects_max_pages() -> None:
    responses = {
        "https://example.com/sitemap.xml": FetchResponse(
            status=200,
            text=(
                "<urlset><url><loc>https://example.com/docs/a</loc></url>"
                "<url><loc>https://example.com/docs/b</loc></url></urlset>"
            ),
        ),
        "https://example.com/docs/a": FetchResponse(status=200, text="a"),
    }
    connector = DocsConnector(
        fetcher=FakeFetcher(responses),
        sitemap_url="https://example.com/sitemap.xml",
        max_pages=1,
    )
    pages = _collect(connector)
    assert len(pages) == 1
    assert pages[0].source_url == "https://example.com/docs/a"


def test_reports_failed_seed_and_yields_nothing() -> None:
    errors: list[str] = []
    responses = {"https://example.com/sitemap.xml": FetchResponse(status=404, text="")}
    connector = DocsConnector(
        fetcher=FakeFetcher(responses),
        sitemap_url="https://example.com/sitemap.xml",
        on_error=lambda event: errors.append(event.url),
    )
    pages = _collect(connector)
    assert pages == []
    assert errors == ["https://example.com/sitemap.xml"]


def test_rejects_ambiguous_seed_configuration() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        DocsConnector(
            fetcher=FakeFetcher({}),
            sitemap_url="https://example.com/sitemap.xml",
            index_url="https://example.com/index.html",
        )
