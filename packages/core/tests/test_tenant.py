from __future__ import annotations

import pytest
from houndex_core import (
    TenantRole,
    parse_tenant_context,
    parse_tenant_id,
    tenant_primary,
    tenant_secondary,
)


@pytest.mark.parametrize("slug", ["a", "primary", "tenant-1", "a_b-c", "x" * 64])
def test_accepts_valid_slugs(slug: str) -> None:
    assert parse_tenant_id(slug) == slug


@pytest.mark.parametrize("slug", ["", "A", "Primary", "-lead", "trail-", "has space", "x" * 65])
def test_rejects_invalid_slugs(slug: str) -> None:
    with pytest.raises(ValueError):
        parse_tenant_id(slug)


def test_parse_context() -> None:
    ctx = parse_tenant_context({"tenant_id": "primary", "user_id": "u1", "role": "admin"})
    assert ctx.role is TenantRole.ADMIN


def test_parse_context_rejects_unknown_role() -> None:
    with pytest.raises(ValueError):
        parse_tenant_context({"tenant_id": "primary", "user_id": "u1", "role": "root"})


def test_fixtures_are_distinct() -> None:
    assert tenant_primary().tenant_id != tenant_secondary().tenant_id
    assert tenant_primary(role=TenantRole.VIEWER).role is TenantRole.VIEWER
