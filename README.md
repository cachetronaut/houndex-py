# Houndex (Python)

A storage-decoupled, last-mile RAG framework. It provides the pieces that sit
*after* retrieval and *before* your application logic: typed output envelopes
with an embedded provenance trace, tenant-aware evidence stores, a small generic
vocabulary for claims and the edges between them, provider ports, and one
pluggable `StorageAdapter` contract.

This repository is the Python implementation. A companion TypeScript
implementation tracks the same contracts, and a shared cross-language parity
fixture keeps the two cores byte-for-byte compatible on their core primitives.

## Packages

| Package | Status | Purpose |
|---|---|---|
| `houndex-core` | **active** | Contracts: schemas, envelopes, tenant, provider ports, storage adapter interface |
| `houndex-storage-local` | planned | Zero-service reference adapter |
| `houndex-storage-supabase` | planned | Postgres + pgvector adapter |
| `houndex-cli` | planned | `init`, `ingest`, `ask`, `eval`, `doctor` |
| `houndex-evals` | planned | Regression / evaluation harness |

## Development

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest          # tests, including cross-language parity
uv run ruff check .    # lint
uv run ruff format --check .
uv run ty check        # type check
uv run python scripts/cleanroom_guard.py
```

## License

[MIT](./LICENSE)
