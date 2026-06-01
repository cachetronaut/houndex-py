"""Build a ``StorageAdapter`` from config. ``local`` is in-process and
dependency-free; ``supabase``/``convex`` are imported (with their client SDKs)
only when selected, and read their secrets from the environment.
"""

from __future__ import annotations

import importlib
import os
from collections.abc import Mapping
from types import ModuleType

from houndex_core.storage import StorageAdapter
from houndex_storage_local import LocalStorageAdapter

from .config import AdapterName, HoundexConfig

REQUIRED_ENV: dict[AdapterName, list[str]] = {
    "local": [],
    "supabase": ["SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"],
    "convex": ["CONVEX_URL"],
}


def missing_env(adapter: AdapterName, env: Mapping[str, str] | None = None) -> list[str]:
    source = os.environ if env is None else env
    return [name for name in REQUIRED_ENV[adapter] if not source.get(name)]


def _require(name: str, env: Mapping[str, str]) -> str:
    value = env.get(name)
    if not value:
        raise RuntimeError(f"missing required environment variable {name}")
    return value


async def create_adapter(
    config: HoundexConfig, env: Mapping[str, str] | None = None
) -> StorageAdapter:
    source = os.environ if env is None else env
    if config.adapter == "local":
        return LocalStorageAdapter()
    if config.adapter == "supabase":
        url = _require("SUPABASE_URL", source)
        key = _require("SUPABASE_SERVICE_ROLE_KEY", source)
        adapters = _import("houndex_storage_supabase", "supabase")
        supabase = _import("supabase", "supabase")
        return adapters.SupabaseStorageAdapter(supabase.create_client(url, key))
    url = _require("CONVEX_URL", source)
    adapters = _import("houndex_storage_convex", "convex")
    convex = _import("convex", "convex")
    return adapters.ConvexStorageAdapter(convex.ConvexClient(url))


def _import(module: str, adapter: str) -> ModuleType:
    try:
        return importlib.import_module(module)
    except ImportError as err:
        extra = f"storage-{adapter}"
        raise RuntimeError(
            f"the '{adapter}' adapter needs the '{extra}' extra: pip install 'houndex[{extra}]'"
        ) from err
