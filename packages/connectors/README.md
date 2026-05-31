# houndex-connectors

Deterministic source connectors that feed the ingestion pipeline.

## What it provides

- **Connector contract** — custom connectors yield `ScrapedPage` values.
- **FileConnector** — walks UTF-8 text files in sorted path order and yields one
  page per included file.
- **WebConnector** — fetches an explicit list of URLs through an injected fetcher
  and yields one page per successful response.
- **GitHubConnector** — reads included repository files through an injected
  GitHub client and yields one page per successful file.
- **ingest_connector** — drains connector pages through
  `houndex-pipeline`'s `process_pages`, with optional source persistence.

## Usage

```python
from houndex_connectors import FileConnector, GitHubConnector, GitHubRepository, WebConnector, ingest_connector

connector = FileConnector(root="docs", base_url="file://docs")
result = await ingest_connector(connector, input, deps)

web = WebConnector(urls=["https://example.com/docs"])
repo = GitHubConnector(repository=GitHubRepository(owner="octo", repo="repo"))
```

The file connector is offline and deterministic. `WebConnector` does not crawl:
it fetches only the URLs supplied. `GitHubConnector` reads repository files only;
issues, pull requests, and docs-site crawling are follow-up slices.
