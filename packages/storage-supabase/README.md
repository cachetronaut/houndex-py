# houndex-storage-supabase (Python)

Supabase (Postgres + pgvector) client adapter implementing the `houndex-core`
`StorageAdapter` contract. Mirrors the TypeScript `@houndex/storage-supabase`
package and targets the **same SQL schema**.

```python
import os
from supabase import create_client
from houndex_storage_supabase import SupabaseStorageAdapter

client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
adapter = SupabaseStorageAdapter(client)
```

Install the real client with the `client` extra:

```bash
uv add "houndex-storage-supabase[client]"
```

## Schema

The schema is owned by the Supabase CLI and lives in `supabase/migrations/` at
the repo root — that is the single source of truth (`supabase db diff`
regenerates against it). Apply it one of two ways:

```bash
# Local development — boots a Dockerized Postgres + pgvector and applies migrations
supabase start
supabase db reset

# Linked cloud project — pushes pending migrations to the remote
supabase db push
```

The embedding column is `vector(1536)` (OpenAI `text-embedding-3-small`). Change
the dimension in the migration to match your model before applying.

Row-level security is enabled on every table with a `tenant_isolation` policy
keyed on the `tenant_id` JWT claim, so anon/authenticated keys can never read
across tenants. A trusted server using the service-role key bypasses RLS; the
adapter additionally filters every query by `tenant_id`, so isolation holds on
both paths.

## Testing

The adapter is generic over a small client protocol (`table()` / `rpc()` with a
chainable builder and `.execute()`), so it is unit-tested behaviorally with an
in-memory fake (idempotency, subject filtering, tenant isolation, run/edge/
curation/kb/override flows) — these run offline with no dependencies.

Live integration tests (`tests/test_supabase_integration.py`) exercise the real
client against a running Supabase, including pgvector cosine search via the
`houndex_search_claims` RPC. They are skipped unless `SUPABASE_URL` and a
service-role key are set:

```bash
supabase start && supabase db reset
export SUPABASE_URL=http://127.0.0.1:54321
export SUPABASE_SERVICE_ROLE_KEY=<service_role key printed by `supabase start`>
PYTHONSAFEPATH=1 pytest -k integration packages/storage-supabase
```

`PYTHONSAFEPATH=1` is required because the Supabase CLI directory (`supabase/`)
at the repo root shadows the installed `supabase` client library when the
working directory is on `sys.path`.

The synchronous Supabase client is bridged to the async `StorageAdapter`
protocol with `asyncio.to_thread`.
