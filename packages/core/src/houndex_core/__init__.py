"""houndex-core — contracts for a storage-decoupled, last-mile RAG framework."""

from __future__ import annotations

from .canonical_json import canonical_json
from .hash import sha256_hex
from .identity import ClaimId, compute_claim_id
from .models import EmbeddingConfig, ModelConfig, ModelRef, ModelRouting
from .observability import (
    NoopTraceSink,
    TraceEvent,
    TraceSink,
    emit_trace,
    set_trace_sink,
)
from .tenant import (
    TenantContext,
    TenantRole,
    parse_tenant_context,
    parse_tenant_id,
    tenant_primary,
    tenant_secondary,
)

__all__ = [
    "ClaimId",
    "EmbeddingConfig",
    "ModelConfig",
    "ModelRef",
    "ModelRouting",
    "NoopTraceSink",
    "TenantContext",
    "TenantRole",
    "TraceEvent",
    "TraceSink",
    "canonical_json",
    "compute_claim_id",
    "emit_trace",
    "parse_tenant_context",
    "parse_tenant_id",
    "set_trace_sink",
    "sha256_hex",
    "tenant_primary",
    "tenant_secondary",
]
