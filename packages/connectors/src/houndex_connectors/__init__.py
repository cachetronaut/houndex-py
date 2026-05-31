"""houndex-connectors — deterministic source connectors for ingestion."""

from __future__ import annotations

from .connector import Connector, IngestConnectorOptions, SourceDraft, ingest_connector
from .file_connector import FileConnector
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
    "Fetcher",
    "FetchResponse",
    "FileConnector",
    "IngestConnectorOptions",
    "SourceDraft",
    "WebConnector",
    "WebConnectorError",
    "ingest_connector",
]
