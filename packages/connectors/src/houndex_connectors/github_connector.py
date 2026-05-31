from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Callable, Sequence
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import quote
from urllib.request import Request, urlopen

from houndex_core.providers import ScrapedPage

_DEFAULT_INCLUDE = (".md", ".txt", ".json")
_DEFAULT_REF = "main"


@dataclass(frozen=True)
class GitHubRepository:
    owner: str
    repo: str
    ref: str = _DEFAULT_REF


@dataclass(frozen=True)
class GitHubFileRef:
    path: str
    sha: str | None = None


class GitHubClient(Protocol):
    async def list_files(self, repository: GitHubRepository) -> Sequence[GitHubFileRef]: ...

    async def read_file(self, repository: GitHubRepository, file: GitHubFileRef) -> str: ...


@dataclass(frozen=True)
class GitHubConnectorError:
    path: str
    error: object


class DefaultGitHubClient:
    def __init__(self, *, token: str | None = None) -> None:
        self._token = token

    async def list_files(self, repository: GitHubRepository) -> list[GitHubFileRef]:
        url = (
            f"https://api.github.com/repos/{repository.owner}/{repository.repo}"
            f"/git/trees/{repository.ref}?recursive=1"
        )
        payload = await asyncio.to_thread(_fetch_json, url, self._headers())
        tree = payload.get("tree") if isinstance(payload, dict) else None
        if not isinstance(tree, list):
            return []

        files: list[GitHubFileRef] = []
        for entry in tree:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path")
            sha = entry.get("sha")
            if entry.get("type") == "blob" and isinstance(path, str):
                files.append(GitHubFileRef(path=path, sha=sha if isinstance(sha, str) else None))
        return files

    async def read_file(self, repository: GitHubRepository, file: GitHubFileRef) -> str:
        return await asyncio.to_thread(
            _fetch_text, _raw_url_for_file(repository, file.path), self._headers()
        )

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "houndex-connectors/0.1",
        }
        if self._token is not None:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers


class GitHubConnector:
    name = "github"

    def __init__(
        self,
        *,
        repository: GitHubRepository,
        include: Sequence[str] | None = None,
        client: GitHubClient | None = None,
        on_error: Callable[[GitHubConnectorError], None] | None = None,
    ) -> None:
        self._repository = GitHubRepository(
            owner=repository.owner,
            repo=repository.repo,
            ref=repository.ref or _DEFAULT_REF,
        )
        self._include = frozenset(include or _DEFAULT_INCLUDE)
        self._client = client or DefaultGitHubClient()
        self._on_error = on_error

    async def pages(self) -> AsyncIterator[ScrapedPage]:
        files = sorted(
            (
                file
                for file in await self._client.list_files(self._repository)
                if _extension_for_path(file.path) in self._include
            ),
            key=lambda file: file.path,
        )
        for file in files:
            try:
                text = await self._client.read_file(self._repository, file)
                yield ScrapedPage(
                    source_url=_source_url_for_file(self._repository, file.path),
                    title=file.path,
                    text=text,
                )
            except Exception as error:  # noqa: BLE001 — one unreadable file must not abort the run
                self._emit_error(file.path, error)

    def _emit_error(self, path: str, error: object) -> None:
        if self._on_error is not None:
            self._on_error(GitHubConnectorError(path=path, error=error))


def _fetch_json(url: str, headers: dict[str, str]) -> Any:
    return json.loads(_fetch_text(url, headers))


def _fetch_text(url: str, headers: dict[str, str]) -> str:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response:  # noqa: S310 — explicit repository input
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def _extension_for_path(file_path: str) -> str:
    file_name = file_path.rsplit("/", maxsplit=1)[-1]
    if "." not in file_name:
        return ""
    return f".{file_name.rsplit('.', maxsplit=1)[-1]}"


def _source_url_for_file(repository: GitHubRepository, file_path: str) -> str:
    return (
        f"https://github.com/{repository.owner}/{repository.repo}"
        f"/blob/{repository.ref}/{_encode_path(file_path)}"
    )


def _raw_url_for_file(repository: GitHubRepository, file_path: str) -> str:
    return (
        f"https://raw.githubusercontent.com/{repository.owner}/{repository.repo}"
        f"/{repository.ref}/{_encode_path(file_path)}"
    )


def _encode_path(file_path: str) -> str:
    return "/".join(quote(part, safe="") for part in file_path.split("/"))
