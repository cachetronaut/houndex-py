from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from houndex_cli import CONFIG_FILENAME, CommandDeps, HoundexConfig, SyntheticEmbedder
from houndex_cli.adapter_factory import create_adapter
from houndex_cli.config import default_config, parse_config
from houndex_core.storage import StorageAdapter


@dataclass
class ApiDeps:
    adapter: StorageAdapter
    config: HoundexConfig
    now: Callable[[], int]

    def command_deps(self, tenant_id: str) -> CommandDeps:
        config = self.config.model_copy(
            update={"tenant": self.config.tenant.model_copy(update={"tenant_id": tenant_id})}
        )
        return CommandDeps(
            adapter=self.adapter,
            config=config,
            embedder=SyntheticEmbedder(config.embedding.dimensions),
            now=self.now,
        )


async def build_api_deps(cwd: Path | None = None, now: Callable[[], int] | None = None) -> ApiDeps:
    config = load_config(cwd or Path.cwd())
    adapter = await create_adapter(config)
    return ApiDeps(adapter=adapter, config=config, now=now or (lambda: 0))


def load_config(cwd: Path) -> HoundexConfig:
    path = cwd / CONFIG_FILENAME
    if path.exists():
        return parse_config(json.loads(path.read_text(encoding="utf-8")))
    return default_config()
