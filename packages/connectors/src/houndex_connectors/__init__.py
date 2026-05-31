"""houndex-connectors — deterministic source connectors for ingestion."""

from __future__ import annotations

from .connector import Connector, IngestConnectorOptions, SourceDraft, ingest_connector
from .docs_connector import (
    DocsConnector,
    extract_index_urls,
    extract_sitemap_urls,
    filter_doc_urls,
)
from .file_connector import FileConnector
from .github_connector import (
    DefaultGitHubClient,
    GitHubClient,
    GitHubConnector,
    GitHubConnectorError,
    GitHubFileRef,
    GitHubRepository,
)
from .web_connector import (
    DefaultFetcher,
    Fetcher,
    FetchResponse,
    WebConnector,
    WebConnectorError,
)

__all__ = [
    "Connector",
    "DefaultFetcher",
    "DefaultGitHubClient",
    "DocsConnector",
    "Fetcher",
    "FetchResponse",
    "FileConnector",
    "GitHubClient",
    "GitHubConnector",
    "GitHubConnectorError",
    "GitHubFileRef",
    "GitHubRepository",
    "IngestConnectorOptions",
    "SourceDraft",
    "WebConnector",
    "WebConnectorError",
    "extract_index_urls",
    "extract_sitemap_urls",
    "filter_doc_urls",
    "ingest_connector",
]
