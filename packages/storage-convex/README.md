# houndex-storage-convex (Python)

Convex client adapter implementing the `houndex-core` `StorageAdapter`
contract. It is a thin RPC layer: it calls the tenant-scoped functions shipped
by the TypeScript `houndex-storage-convex` package, which is the deployable
Convex backend (schema, functions, and the `vectorSearchClaims` action).

```python
import os
from convex import ConvexClient
from houndex_storage_convex import ConvexStorageAdapter

adapter = ConvexStorageAdapter(ConvexClient(os.environ["CONVEX_URL"]))
```

Install the real client with the `client` extra:

```bash
uv add "houndex-storage-convex[client]"
```

## Vector search

`search_claims` with a `query_vector` routes to the Convex `vectorSearchClaims`
**action** (cosine ANN over the `by_embedding` vector index), scoped to the
tenant at the index with `subject`/`category` post-filtered. Without a
`query_vector`, it calls the indexed `searchClaims` query. The vector dimension
(`1536`) is fixed in the backend's `convex/schema.ts`.

## Testing

- The adapter is generic over a small client protocol (`query` / `mutation` /
  `action`), so it is unit-tested offline with a fake client (RPC wiring, camel/
  snake mapping, and that a `query_vector` routes to the action). The backend's
  behavior — including cosine ordering and tenant-scoped vector search — is
  covered by the TypeScript package's `convex-test` suite against the same
  functions.
- Live integration tests (`tests/test_convex_integration.py`) run the real
  `convex` client against a deployment. Skipped unless `CONVEX_URL` is set:

  ```bash
  # from the houndex-ts storage-convex package, which owns the backend:
  pnpm exec convex dev --once
  export CONVEX_URL=https://<your-deployment>.convex.cloud
  pytest -k convex_integration packages/storage-convex
  ```

The Convex Python client is synchronous; the adapter bridges it to the async
`StorageAdapter` protocol with `asyncio.to_thread`. Mirrors the TypeScript
`ConvexStorageAdapter`.
