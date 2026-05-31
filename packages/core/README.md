# houndex-core (Python)

The contracts every other Houndex package depends on: schemas, identity, the
output envelope, tenant context, provider ports, and the storage adapter
protocol. Pure and I/O-free — it validates and types data, and binds to no
database or model provider. Mirrors the TypeScript `@houndex/core` package.

## What it provides

- **Schemas** (Pydantic v2) — `Claim`, `Source`, `Edge`, `Enrichment`, the agent
  input/output types, and the versioned `OutputEnvelope`. A neutral default
  taxonomy ships as `Literal` types you can replace with your own closed set.
- **Identity** — `compute_claim_id` (content-addressed claim ids) and
  `edge_idempotency_key`, built on canonical JSON and `sha256_hex`.
- **Tenant context** — `TenantContext` and `TenantRole`. Every storage call
  takes a `TenantContext`, so forgetting to scope a query to a tenant is a type
  error rather than a policy mistake.
- **Provider ports** — `Protocol` interfaces for search, scraping, embedding,
  reranking, and model calls. Houndex bundles no provider.
- **Storage contract** — the `StorageAdapter` protocol and its input models.
  This is the seam that decouples Houndex from any specific database.

## Usage

```python
from houndex_core import compute_claim_id

claim_id = compute_claim_id(
    tenant_id="acme",
    subject="Acme",
    claim_text="Has an audit log",
    source_url="https://example.com/security",
)
```

Claim identity, canonical JSON, and URL canonicalization are held byte-for-byte
identical to the TypeScript `@houndex/core` package by a shared parity fixture.
