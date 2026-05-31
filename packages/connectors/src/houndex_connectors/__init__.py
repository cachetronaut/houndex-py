"""houndex-connectors — deterministic source connectors for ingestion."""

from __future__ import annotations

from .connector import Connector, IngestConnectorOptions, SourceDraft, ingest_connector
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
    "ingest_connector",
]
