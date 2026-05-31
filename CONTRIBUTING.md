# Contributing

Thanks for your interest in the project.

## Getting started

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ty check
uv run python scripts/cleanroom_guard.py
```

## Conventions

- **Pydantic models are the source of truth** for data shapes; mirror the
  TypeScript `houndex/core` contracts.
- **Closed vocabularies are code-owned** as `Literal` types backed by a single
  value tuple — never duplicated string literals.
- Keep the public primitives (claim identity, edge keys, URL canonicalization,
  canonical JSON) byte-for-byte compatible with the TypeScript implementation;
  the shared parity fixture (`tests/parity/core-vectors.json`) enforces this.
- New behavior ships with a test.

## Clean-room guard

CI runs `scripts/cleanroom_guard.py`, which fails if any disallowed token
appears in tracked files. This keeps the framework free of names and
terminology from the applications that use it.
