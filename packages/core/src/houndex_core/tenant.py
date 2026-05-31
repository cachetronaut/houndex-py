"""Tenant primitive — one type threaded through every storage call so that
"did we forget to scope this path to a tenant?" is structurally impossible
rather than a matter of policy. Mirrors the TypeScript ``TenantContext``.
"""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, field_validator

# Tenant slug grammar: lowercase ASCII / digits / `-` / `_`, alphanumeric
# endpoints, max 64 chars. A single alphanumeric char is valid.
_TENANT_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]$|^[a-z0-9]$")


class TenantRole(StrEnum):
    CURATOR = "curator"
    VIEWER = "viewer"
    ADMIN = "admin"


def parse_tenant_id(value: str) -> str:
    """Validate an untrusted tenant slug, raising ``ValueError`` on failure."""
    if len(value) > 64 or _TENANT_SLUG_RE.match(value) is None:
        raise ValueError(
            "tenant_id must be a lowercase slug (a-z0-9_-, alphanumeric endpoints, <=64 chars)"
        )
    return value


class TenantContext(BaseModel):
    tenant_id: str
    user_id: str
    role: TenantRole

    @field_validator("tenant_id")
    @classmethod
    def _validate_tenant_id(cls, value: str) -> str:
        return parse_tenant_id(value)


def parse_tenant_context(value: Any) -> TenantContext:
    """Validate a full tenant context (e.g. assembled from auth claims)."""
    return TenantContext.model_validate(value)


# ── Test fixtures ──────────────────────────────────────────────────────


def tenant_primary(**overrides: Any) -> TenantContext:
    data: dict[str, Any] = {
        "tenant_id": "primary",
        "user_id": "user_primary",
        "role": TenantRole.ADMIN,
    }
    data.update(overrides)
    return TenantContext(**data)


def tenant_secondary(**overrides: Any) -> TenantContext:
    data: dict[str, Any] = {
        "tenant_id": "secondary",
        "user_id": "user_secondary",
        "role": TenantRole.ADMIN,
    }
    data.update(overrides)
    return TenantContext(**data)
