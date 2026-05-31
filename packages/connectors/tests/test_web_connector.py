from __future__ import annotations

import asyncio

from houndex_connectors import FetchResponse, WebConnector, WebConnectorError


class FakeFetcher:
    def __init__(self, responses: dict[str, FetchResponse | Exception]) -> None:
        self._responses = responses

    async def fetch(self, url: str) -> FetchResponse:
        response = self._responses.get(url)
        if response is None:
            raise RuntimeError(f"missing fake response for {url}")
        if isinstance(response, Exception):
            raise response
        return response


def test_web_connector_fetches_explicit_urls_in_input_order() -> None:
    connector = WebConnector(
        urls=["https://example.com/b?utm_source=x", "https://example.com/a"],
        concurrency=2,
        fetcher=FakeFetcher(
            {
                "https://example.com/b?utm_source=x": FetchResponse(status=200, text="second"),
                "https://example.com/a": FetchResponse(status=200, text="first"),
            }
        ),
    )

    async def run() -> list[tuple[str, str, str]]:
        pages = []
        async for page in connector.pages():
            pages.append((page.source_url, page.title, page.text))
        return pages

    assert asyncio.run(run()) == [
        ("https://example.com/b", "example.com/b", "second"),
        ("https://example.com/a", "example.com/a", "first"),
    ]


def test_web_connector_skips_failed_fetches_and_reports_errors() -> None:
    errors: list[WebConnectorError] = []
    connector = WebConnector(
        urls=[
            "https://example.com/good",
            "https://example.com/missing",
            "https://example.com/error",
        ],
        concurrency=3,
        fetcher=FakeFetcher(
            {
                "https://example.com/good": FetchResponse(status=200, text="good"),
                "https://example.com/missing": FetchResponse(status=404, text="missing"),
                "https://example.com/error": TypeError("network failed"),
            }
        ),
        on_error=errors.append,
    )

    async def run() -> list[str]:
        pages = []
        async for page in connector.pages():
            pages.append(page.source_url)
        return pages

    assert asyncio.run(run()) == ["https://example.com/good"]
    assert [error.url for error in errors] == [
        "https://example.com/missing",
        "https://example.com/error",
    ]
    assert isinstance(errors[0].error, RuntimeError)
    assert isinstance(errors[1].error, TypeError)
