# houndex-storage-convex (Python)

Convex client adapter implementing the `houndex-core` `StorageAdapter`
contract. It is a thin RPC layer: it calls the tenant-scoped functions shipped
by the TypeScript `houndex/storage-convex` package, which is the deployable
Convex backend.

```python
from convex import ConvexClient
from houndex_storage_convex import ConvexStorageAdapter

adapter = ConvexStorageAdapter(ConvexClient(os.environ["CONVEX_URL"]))
```

Install the real client with the `client` extra:

```bash
uv add "houndex-storage-convex[client]"
```

The adapter is generic over a small client protocol (`query` / `mutation`), so
it can be unit-tested with a fake client; the backend's behavior (idempotency,
tenant isolation) is covered by the TypeScript package's `convex-test` suite
against the same functions. Mirrors the TypeScript `ConvexStorageAdapter`.
