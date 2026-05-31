# houndex-surface-api

FastAPI service exposing the Houndex engine over HTTP.

## What it provides

- `POST /verify` — verifies an answer envelope with the same engine as
  `houndex verify`.
- `POST /ask` — searches the configured store and builds the same extractive
  answer envelope as `houndex ask`.
- `POST /ingest` — processes caller-supplied pages through the connector
  ingestion bridge and stores extracted claims in the configured adapter.

Every endpoint requires `X-Houndex-Tenant`. The service uses
`houndex.config.json` when present and otherwise falls back to the same local
adapter defaults as the CLI.
