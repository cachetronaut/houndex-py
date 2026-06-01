"""The ``houndex`` command-line shell (Typer). Thin: reads config + input files,
builds the configured adapter + synthetic embedder, delegates to a command
handler, prints the result, and exits with its code. All logic lives in the
handlers + engine, which are tested directly. Mirrors the TypeScript ``cli.ts``.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Annotated

try:
    import typer
except ImportError as err:  # pragma: no cover - exercised only in minimal installs
    raise RuntimeError(
        "the houndex command needs the 'cli' extra: pip install 'houndex[cli]'"
    ) from err

from . import commands as cmd
from .adapter_factory import create_adapter
from .config import CONFIG_FILENAME, HoundexConfig, default_config, parse_config
from .embedder import SyntheticEmbedder
from .engine import EvalFile, VerifyFile, parse_claims

app = typer.Typer(help="Verify RAG outputs against an evidence store.", no_args_is_help=True)


def _load_config(cwd: Path) -> HoundexConfig:
    path = cwd / CONFIG_FILENAME
    if path.exists():
        return parse_config(json.loads(path.read_text()))
    return default_config()


async def _build_deps(config: HoundexConfig) -> cmd.CommandDeps:
    return cmd.CommandDeps(
        adapter=await create_adapter(config),
        config=config,
        embedder=SyntheticEmbedder(config.embedding.dimensions),
        now=lambda: 0,
    )


def _emit(result: cmd.CommandResult) -> None:
    if result.output:
        typer.echo(result.output)
    raise typer.Exit(result.code)


def _guard(coro) -> cmd.CommandResult:  # noqa: ANN001 — awaitable returning CommandResult
    """Run an async handler; any raised error is an operational failure (exit 2)."""
    try:
        return asyncio.run(coro)
    except typer.Exit:
        raise
    except Exception as err:  # noqa: BLE001
        typer.echo(f"error: {err}", err=True)
        raise typer.Exit(2) from err


@app.command()
def init(
    adapter: Annotated[str | None, typer.Option(help="local | supabase | convex")] = None,
    tenant: Annotated[str | None, typer.Option(help="tenant id")] = None,
    force: Annotated[bool, typer.Option(help="overwrite an existing config")] = False,
) -> None:
    """Write houndex.config.json."""
    path = Path.cwd() / CONFIG_FILENAME
    result = cmd.init(
        adapter=adapter,
        tenant_id=tenant,
        force=force,
        config_exists=path.exists(),
    )
    if result.content is not None:
        path.write_text(result.content)
    _emit(result)


@app.command()
def doctor() -> None:
    """Validate config and check adapter connectivity."""
    config = _load_config(Path.cwd())
    _emit(_guard(cmd.doctor(config=config, env=os.environ, connect=lambda: create_adapter(config))))


@app.command()
def ingest(
    file: str,
    format: Annotated[str, typer.Option(help="json | jsonl")] = "json",
    as_json: Annotated[bool, typer.Option("--json", help="machine-readable output")] = False,
) -> None:
    """Load claims into the configured store."""

    async def run() -> cmd.CommandResult:
        config = _load_config(Path.cwd())
        deps = await _build_deps(config)
        text = Path(file).read_text()
        claims = parse_claims(text, "jsonl" if format == "jsonl" else "json")
        return await cmd.ingest(deps, claims=claims, as_json=as_json)

    _emit(_guard(run()))


@app.command()
def ask(
    query: str,
    limit: Annotated[int, typer.Option(help="max claims")] = 10,
    as_json: Annotated[bool, typer.Option("--json", help="machine-readable output")] = False,
) -> None:
    """Retrieve grounded claims and emit a verified answer envelope."""

    async def run() -> cmd.CommandResult:
        deps = await _build_deps(_load_config(Path.cwd()))
        return await cmd.ask(deps, query=query, limit=limit, as_json=as_json)

    _emit(_guard(run()))


@app.command()
def verify(
    file: str,
    as_json: Annotated[bool, typer.Option("--json", help="machine-readable output")] = False,
) -> None:
    """Verify an answer envelope against the store (exit 1 on failure)."""

    async def run() -> cmd.CommandResult:
        deps = await _build_deps(_load_config(Path.cwd()))
        data = VerifyFile.model_validate_json(Path(file).read_text())
        return await cmd.verify(
            deps, envelope=data.envelope, claim_ids=data.claim_ids, as_json=as_json
        )

    _emit(_guard(run()))


@app.command()
def eval(
    file: str,
    threshold: Annotated[float | None, typer.Option(help="min aggregate score to pass")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="machine-readable output")] = False,
) -> None:
    """Score a fixture suite; exit 1 below --threshold."""

    async def run() -> cmd.CommandResult:
        deps = await _build_deps(_load_config(Path.cwd()))
        data = EvalFile.model_validate_json(Path(file).read_text())
        cases = [(case.fixture, case.envelope) for case in data.cases]
        return await cmd.evaluate(
            deps, cases=cases, claim_ids=data.claim_ids, threshold=threshold, as_json=as_json
        )

    _emit(_guard(run()))


def main() -> None:
    app()
