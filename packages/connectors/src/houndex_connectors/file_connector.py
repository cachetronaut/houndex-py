from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from pathlib import Path
from urllib.parse import quote

from houndex_core.providers import ScrapedPage

_DEFAULT_INCLUDE = (".md", ".txt", ".json")


class FileConnector:
    name = "file"

    def __init__(
        self,
        *,
        root: str | Path,
        include: Sequence[str] | None = None,
        base_url: str | None = None,
    ) -> None:
        self._root = Path(root).resolve()
        self._include = frozenset(include or _DEFAULT_INCLUDE)
        self._base_url = base_url

    async def pages(self) -> AsyncIterator[ScrapedPage]:
        for path in self._files():
            text = path.read_text(encoding="utf-8")
            relative_path = path.relative_to(self._root).as_posix()
            yield ScrapedPage(
                source_url=self._source_url(path, relative_path),
                title=path.name,
                text=text,
            )

    def _files(self) -> list[Path]:
        return sorted(
            (
                path
                for path in self._root.rglob("*")
                if path.is_file() and path.suffix in self._include
            ),
            key=lambda path: path.relative_to(self._root).as_posix(),
        )

    def _source_url(self, path: Path, relative_path: str) -> str:
        if self._base_url is None:
            return path.as_uri()
        base_url = self._base_url.rstrip("/")
        encoded_path = "/".join(quote(part, safe="") for part in relative_path.split("/"))
        return f"{base_url}/{encoded_path}"
