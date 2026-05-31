# houndex-pipeline (Python)

Deterministic ingestion and enrichment transforms built on `houndex-core`. The
same input always produces the same output, so the pipeline is testable and its
results are reproducible. Mirrors the TypeScript `@houndex/pipeline` package.

## What it provides

- **Chunking** — splits source text on stable boundaries with a configurable
  preference order.
- **Content-hash dedupe** — drops duplicate pages so the same material is stored
  once.
- **Source-tier classification** — ranks a source as `authoritative`, `tier_2`,
  or `tier_3` from domain rules you supply.
- **Enrichment** — derives corroboration counts, contradiction counts, and
  source-tier distribution from a claim's edges.
- **Orchestrator** — `run_ingestion` ties the steps together over injected
  provider ports (scrape, extract, embed) and a `StorageAdapter`. The
  dependencies are parameters, so you choose the providers and storage.
- **Processing bridge** — `discover_pages` and `process_pages` expose the
  discovery and processing halves separately, so connector packages can reuse
  the deterministic classify/chunk/extract/embed/sink path.

## Usage

```python
from houndex_pipeline import run_ingestion

result = await run_ingestion(input, deps)
```

`deps` carries the provider implementations and the storage adapter; the pipeline
performs no network or database calls directly.
