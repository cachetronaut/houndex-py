# houndex-storage-supabase (Python)

Supabase (Postgres + pgvector) client adapter implementing the `houndex-core`
`StorageAdapter` contract. Mirrors the TypeScript `houndex/storage-supabase`
package and targets the **same SQL schema** — apply that package's
`migrations/0001_init.sql` to your database.

```python
from supabase import create_client
from houndex_storage_supabase import SupabaseStorageAdapter

client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
adapter = SupabaseStorageAdapter(client)
```

Install the real client with the `client` extra:

```bash
uv add "houndex-storage-supabase[client]"
```

The adapter is generic over a small client protocol (`table()` / `rpc()` with a
chainable builder and `.execute()`), so it is unit-tested behaviorally with an
in-memory fake (idempotency, subject filtering, tenant isolation). Every query
filters by `tenant_id`. The synchronous Supabase client is bridged to the async
`StorageAdapter` protocol with `asyncio.to_thread`. Live pgvector vector search
(`search_claims` with a query vector) needs a real database and is a follow-up.
