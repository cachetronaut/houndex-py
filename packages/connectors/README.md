# houndex-connectors

Deterministic source connectors that feed the ingestion pipeline.

## What it provides

- **Connector contract** — custom connectors yield `ScrapedPage` values.
- **FileConnector** — walks UTF-8 text files in sorted path order and yields one
  page per included file.
- **ingest_connector** — drains connector pages through
  `houndex-pipeline`'s `process_pages`, with optional source persistence.

## Usage

```python
from houndex_connectors import FileConnector, ingest_connector

connector = FileConnector(root="docs", base_url="file://docs")
result = await ingest_connector(connector, input, deps)
```

The MVP is offline and deterministic. Web, GitHub, and docs-site connectors are
follow-up slices.
