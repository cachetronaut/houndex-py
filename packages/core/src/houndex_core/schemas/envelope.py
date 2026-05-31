"""Versioned, self-describing ``OutputEnvelope``. A downstream consumer can
validate against ``schema_url`` and reason from the embedded provenance
``trace`` instead of guessing how a result was produced. Generic over the
payload type.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

ENVELOPE_SCHEMA_VERSION = "v1.0.0"
ENVELOPE_SCHEMA_URL = "https://houndex.example/schemas/output_envelope.v1.json"
ENGINE_VERSION = "0.1.0"

PayloadT = TypeVar("PayloadT")


class TraceEntry(BaseModel):
    claim_id: str
    mechanism: str = Field(min_length=1)
    semantic_score: float | None = None


class OutputEnvelope(BaseModel, Generic[PayloadT]):
    schema_version: str = ENVELOPE_SCHEMA_VERSION
    schema_url: str = ENVELOPE_SCHEMA_URL
    tenant_id: str = Field(min_length=1, max_length=64)
    generated_at: int
    engine_version: str = ENGINE_VERSION
    trace: list[TraceEntry] = Field(default_factory=list)
    payload: PayloadT
