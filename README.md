# Houndex Python

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

## Package status

| Package | Status | Purpose |
|---|---|---|
| `houndex-core` | Active | Schemas, output envelopes, claims, evidence, traces, provider ports, storage contracts |
| `houndex-storage-local` | Planned | Zero-service reference adapter |
| `houndex-storage-supabase` | Planned | Postgres + pgvector adapter |
| `houndex-cli` | Planned | `init`, `ingest`, `ask`, `trace`, `eval`, `doctor` |
| `houndex-evals` | Planned | Regression harness for citation quality and envelope validity |

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

## Current status

Houndex is early and under active development.

The first milestone is a clean core with shared contracts across TypeScript and Python, followed by local storage, Supabase storage, basic ingestion, typed output envelopes, and citation verification.

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

## License

[MIT](./LICENSE)
