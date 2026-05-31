from __future__ import annotations

import asyncio
from collections.abc import Sequence

from houndex_connectors import (
    GitHubConnector,
    GitHubConnectorError,
    GitHubFileRef,
    GitHubRepository,
)


class FakeGitHubClient:
    def __init__(
        self,
        files: Sequence[GitHubFileRef],
        contents: dict[str, str | Exception],
    ) -> None:
        self._files = files
        self._contents = contents

    async def list_files(self, repository: GitHubRepository) -> Sequence[GitHubFileRef]:
        _ = repository
        return self._files

    async def read_file(self, repository: GitHubRepository, file: GitHubFileRef) -> str:
        _ = repository
        content = self._contents.get(file.path)
        if content is None:
            raise RuntimeError(f"missing fake content for {file.path}")
        if isinstance(content, Exception):
            raise content
        return content


def test_github_connector_lists_included_repository_files_in_sorted_path_order() -> None:
    connector = GitHubConnector(
        repository=GitHubRepository(owner="octo", repo="repo", ref="trunk"),
        client=FakeGitHubClient(
            files=[
                GitHubFileRef(path="docs/b.txt"),
                GitHubFileRef(path="image.png"),
                GitHubFileRef(path="README.md"),
                GitHubFileRef(path="docs/a.json"),
            ],
            contents={
                "README.md": "readme",
                "docs/a.json": '{"value":true}',
                "docs/b.txt": "text",
            },
        ),
    )

    async def run() -> list[tuple[str, str, str]]:
        pages = []
        async for page in connector.pages():
            pages.append((page.source_url, page.title, page.text))
        return pages

    assert asyncio.run(run()) == [
        ("https://github.com/octo/repo/blob/trunk/README.md", "README.md", "readme"),
        ("https://github.com/octo/repo/blob/trunk/docs/a.json", "docs/a.json", '{"value":true}'),
        ("https://github.com/octo/repo/blob/trunk/docs/b.txt", "docs/b.txt", "text"),
    ]


def test_github_connector_skips_file_read_failures_and_reports_errors() -> None:
    errors: list[GitHubConnectorError] = []
    connector = GitHubConnector(
        repository=GitHubRepository(owner="octo", repo="repo"),
        client=FakeGitHubClient(
            files=[GitHubFileRef(path="ok.md"), GitHubFileRef(path="bad.md")],
            contents={"ok.md": "ok", "bad.md": TypeError("read failed")},
        ),
        on_error=errors.append,
    )

    async def run() -> list[str]:
        pages = []
        async for page in connector.pages():
            pages.append(page.source_url)
        return pages

    assert asyncio.run(run()) == ["https://github.com/octo/repo/blob/main/ok.md"]
    assert [error.path for error in errors] == ["bad.md"]
    assert isinstance(errors[0].error, TypeError)
