# houndex-cli (Python)

The `houndex` command — the **operator + CI surface** for the verification
engine. It does no verification itself: it loads config, builds the configured
`StorageAdapter`, and delegates to the same `houndex-core` + `houndex-evals`
engine your pipeline calls in-process. (Per-transaction verification belongs in
the library, on the hot path; the CLI is for setup, ingestion, and CI gates.)
Mirrors the TypeScript `@houndex/cli`.

```bash
houndex init                 # write houndex.config.json (adapter: local by default)
houndex doctor               # validate config + check adapter connectivity
houndex ingest claims.json   # load claims into the configured store
houndex ask "audit logging"  # grounded, verified answer envelope
houndex verify answer.json   # verify an answer against the store — exit 1 on failure
houndex eval suite.json      # score a fixture suite; exit 1 below --threshold
```

## Configuration

`houndex.config.json` is the same format as the TypeScript CLI (camelCase keys),
and **secrets come from env, never the file**:

```json
{
  "adapter": "local",
  "tenant": { "tenantId": "default", "userId": "cli", "role": "admin" },
  "embedding": { "provider": "synthetic", "dimensions": 1536 }
}
```

- `adapter`: `local` (in-memory, zero-config default) | `supabase` | `convex`.
  Remote adapters read `SUPABASE_URL`/`SUPABASE_SERVICE_ROLE_KEY` or `CONVEX_URL`
  from the environment; `doctor` reports anything missing. Install the client
  extra to use one: `uv add "houndex-cli[supabase]"` or `[convex]`.
- `local` is **ephemeral** — ideal for CI and self-contained fixtures. Point
  `adapter` at `supabase`/`convex` to verify a live pipeline across invocations.

## Verification semantics

`verify` floors `trace_resolution` and `envelope_validity` at `1.0`: an answer
that cites an unknown claim, or fails envelope schema validation, is a hard FAIL
(exit `1`). Exit codes: **`0`** pass · **`1`** verification/check failure (the CI
signal) · **`2`** operational error. `verify`/`eval` input files may carry a
self-contained `claim_ids` universe for ephemeral/CI runs, else they check
against the configured store.

## Synthetic provider

The default embedder is deterministic and synthetic (no API keys), so the CLI
runs offline with stable output. It is **not** a semantic model. The algorithm
is integer-exact and shared with the TypeScript CLI, so vectors match across
languages (covered by a parity test). Real embedders are wired via the library.

Input files use snake_case keys (matching the Python core models); the Python
client bridges the synchronous adapters to the async engine internally.
