"""Edge schema for the claim graph. Both endpoints are required and ``kind`` is
a closed-vocabulary ``EdgeKind``. The idempotency key is a deterministic 16-hex
digest over ``(src_id, dst_id, kind)``, so a backend treats repeat writes as a
no-op; tenant is the partition the edge lives in, not part of the key.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..hash import sha256_hex
from .taxonomy import EdgeKind

_NODE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_:./@-]{0,254}$"


class Edge(BaseModel):
    tenant_id: str
    src_id: str = Field(pattern=_NODE_ID_PATTERN)
    dst_id: str = Field(pattern=_NODE_ID_PATTERN)
    kind: EdgeKind
    attributes: dict[str, object] = Field(default_factory=dict)


def edge_idempotency_key(*, src_id: str, dst_id: str, kind: str) -> str:
    """Deterministic 16-hex digest over (src_id, dst_id, kind). Two edges with
    the same triple share a key regardless of attribute drift."""
    return sha256_hex("\0".join([src_id, dst_id, kind]))[:16]
