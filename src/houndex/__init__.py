"""Public facade for the Houndex Python distribution."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from houndex_core import (
    ClaimId,
    EmbeddingConfig,
    ModelConfig,
    ModelRef,
    ModelRouting,
    NoopTraceSink,
    TenantContext,
    TenantRole,
    TraceEvent,
    TraceSink,
    canonical_json,
    compute_claim_id,
    emit_trace,
    parse_tenant_context,
    parse_tenant_id,
    set_trace_sink,
    sha256_hex,
    tenant_primary,
    tenant_secondary,
)

try:
    __version__ = version("houndex")
except PackageNotFoundError:  # pragma: no cover - editable source tree fallback
    __version__ = "0.0.0"

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
    "__version__",
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
