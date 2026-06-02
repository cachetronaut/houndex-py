# Houndex Python

<p align="center">
    <img src="./docs/assets/houndex-banner.png" alt="Houndex logo" height="500px"/>
</p>

**Houndex is a last-mile knowledge framework for building source-backed AI systems.**

Most RAG tools help you retrieve context. Houndex focuses on what happens after retrieval: turning sources, claims, evidence, citations, verification results, and provenance into typed artifacts your application can trust, inspect, store, and test.

Houndex is designed for teams building AI products where answers need receipts.

This repository contains the Python implementation. A companion TypeScript implementation tracks the same contracts, and shared cross-language parity fixtures keep the two cores aligned on their core primitives.

## What Houndex does

Houndex gives applications a small set of durable primitives:

- **Sources** — documents, pages, messages, files, APIs, or tool results.
- **Claims** — structured statements extracted from source material.
- **Evidence** — source-backed excerpts or records that support claims.
- **Edges** — relationships between claims, sources, evidence, contradictions, and outputs.
- **Output envelopes** — typed, versioned responses with citations and provenance.
- **Storage adapters** — pluggable persistence for claims, evidence, traces, and outputs.
- **Provider ports** — interfaces for search, scraping, embedding, reranking, and model calls.
- **Evals** — regression checks for citation quality, envelope validity, and unsupported claims.

The goal is not to replace your app, model provider, vector database, or RAG framework.

The goal is to make generated knowledge **traceable, reviewable, portable, and testable**.

## Why this exists

RAG demos are easy. Production knowledge systems are harder.

Common problems:

- Answers cite sources that do not actually support them.
- Claims are mixed with raw chunks and become hard to inspect.
- Retrieval traces disappear into logs.
- Human review is bolted on later.
- Outputs are plain text instead of typed application data.
- Storage choices are coupled to framework choices.
- Prompt, model, and retriever changes cause silent regressions.

Houndex treats knowledge as a set of source-backed artifacts rather than a one-shot chat response.

More importantly, modern AI workflows increasingly rely on agents moving information between systems. A sales operations agent may pull customer data from Salesforce, retrieve contract terms from Google Drive, check support history in Zendesk, and push recommendations into Jira or Slack. Each step creates new claims that influence downstream decisions.

Without a structured knowledge layer, teams are left asking:

- Which source produced this recommendation?
- Was the contract clause actually cited?
- Did the agent use the latest customer record?
- What changed when we updated the retrieval pipeline?

Houndex provides the connective tissue between retrieval and action. Instead of passing around opaque text, agents exchange source-backed claims, evidence, citations, and provenance that can be inspected, verified, stored, and reused across workflows.

For example, imagine a customer renewal workflow. An agent gathers account activity from a CRM, support escalations from a ticketing system, product usage metrics from an analytics platform, and contract obligations from a document repository. It then generates a renewal risk assessment and creates tasks for account managers. With Houndex, every recommendation can be traced back to the underlying records, reviewed by humans, validated against evidence, and audited later if questions arise. The result is not just better answers—it is higher confidence, faster reviews, reduced operational risk, and AI workflows that teams can trust in production.

## Pipeline

Houndex models the last-mile knowledge flow as:

```text
Ingest → Extract → Link → Curate → Answer → Verify → Evaluate
```

In plain English:

1. **Collect source material** from files, web pages, docs, APIs, or tools.
2. **Extract claims and evidence** from that material.
3. **Link related knowledge** through support, contradiction, citation, and provenance edges.
4. **Curate what is trusted** through human or application workflows.
5. **Generate typed outputs** for your application.
6. **Verify citations and claims** against evidence.
7. **Evaluate regressions** as prompts, models, storage, and retrieval change.

## Example use cases

Houndex can be used anywhere generated knowledge needs to show its work:

- Product documentation assistants.
- Compliance and policy assistants.
- Customer support knowledge systems.
- Research workbenches.
- Engineering decision record search.
- Source-backed analysis products.
- Internal tools that need citations, provenance, and review.
- Domain-specific AI products that need trusted output envelopes.

## What Houndex is not

Houndex is not:

- A chatbot.
- A model provider.
- A vector database.
- A hosted enterprise search product.
- A replacement for every RAG framework.
- A guarantee that generated text is true.

Verification in Houndex is evidence-relative. It can tell you whether an answer is supported by the available evidence, but it does not magically make weak sources correct.

## Module status

`houndex` is published as one Python distribution with optional extras for heavier runtime surfaces.

| Import package | Status | Purpose |
|---|---|---|
| `houndex_core` | Active | Schemas, output envelopes, claims, evidence, traces, provider ports, storage contracts |
| `houndex_pipeline` | Active | Deterministic ingestion/enrichment: chunking, dedupe, source tiering, claim assembly |
| `houndex_storage_local` | Active | Zero-service in-memory reference adapter |
| `houndex_storage_supabase` | Active | Postgres + pgvector adapter (HNSW cosine search, RLS) |
| `houndex_storage_convex` | Active | Convex client adapter (vector index + tenant-scoped search action) |
| `houndex_evals` | Active | Regression harness: fixture schema, envelope rubric scoring, reports |
| `houndex_cli` | Active | `init`, `doctor`, `ingest`, `ask`, `verify`, `eval` over a configured adapter |
| `houndex_connectors` | Active | Deterministic source connectors for files, explicit web URLs, GitHub repositories, and documentation sites |
| `houndex_surface_api` | Active | Optional FastAPI service exposing verify, ask, and ingest over HTTP |

The companion TypeScript repository tracks the same contracts. Shared parity
fixtures keep claim identity, canonical JSON, and the synthetic embedder
byte-for-byte identical across the two languages.

## Quickstart

Install the base framework:

```bash
pip install houndex
```

Install optional surfaces as needed:

```bash
pip install "houndex[cli]"
pip install "houndex[api]"
pip install "houndex[storage-supabase]"
pip install "houndex[storage-convex]"
pip install "houndex[all]"
```

Run the repo test suite from a clone:

```bash
git clone https://github.com/cachetronaut/houndex-py
cd houndex-py
uv sync
uv run pytest
```

Verify a model answer against an evidence store with the CLI. The CLI reads
`houndex.config.json` and defaults to an in-memory store, so it needs no
services:

```bash
uv run houndex init
uv run houndex verify answer.json
```

`verify` checks that the answer envelope is schema-valid and that every cited
claim resolves to a stored claim. It exits `0` when the answer is grounded, `1`
when a citation does not resolve or the envelope is invalid, and `2` on an
operational error such as a missing file. Use the exit code as a CI gate.

In application code, call the same engine in-process on each answer through
`houndex-evals` (`score_envelope`). The CLI and the library share one engine, so
their verdicts are identical.

## Design principles

### Storage-decoupled

Houndex defines storage contracts instead of forcing one database. Use local storage for development, Supabase/Postgres for production, Convex for reactive apps, or implement your own adapter.

### Source-agnostic

Houndex does not care whether knowledge comes from PDFs, Markdown files, Slack, Notion, GitHub, MCP tools, or custom APIs. Connectors normalize source material into common primitives.

### Typed by default

Outputs are wrapped in versioned envelopes so downstream applications can validate, render, store, and audit them.

### Provenance-first

Claims, citations, evidence, traces, and outputs should be inspectable. The system should be able to answer: “Where did this come from?”

### Human-review friendly

Houndex is designed for workflows where humans may approve, reject, edit, or override knowledge before it becomes trusted.

### Eval-ready

Every serious knowledge system needs regression tests. Houndex treats evals as part of the framework, not an afterthought.

## Roadmap

Houndex is early and under active development. The contracts are stable enough to
build on; the surface area is still growing.

Shipped, in both TypeScript and Python:

- `core` contracts, the deterministic `pipeline`, three storage adapters
  (`storage-local`, `storage-supabase`, `storage-convex`), the `evals` harness,
  the `cli`, and `connectors` for files, explicit web URLs, GitHub repositories,
  and documentation sites.

Planned, in roughly this order:

1. `surface-next` — the TypeScript Next.js review UI.
2. Publishing to PyPI, with semantic-versioned releases.

## Development

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run python scripts/cleanroom_guard.py
```

The Supabase and Convex adapters carry live integration tests that are skipped
unless their environment is configured:

- Supabase: run `supabase start && supabase db reset`, set `SUPABASE_URL` and
  `SUPABASE_SERVICE_ROLE_KEY`, then run the tests with `PYTHONSAFEPATH=1` (the
  `supabase/` CLI directory otherwise shadows the installed `supabase` client).
- Convex: deploy the backend from the TypeScript repository, then set
  `CONVEX_URL`.

## License

[MIT](./LICENSE)
