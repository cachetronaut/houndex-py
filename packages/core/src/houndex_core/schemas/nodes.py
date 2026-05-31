"""Node schemas for the claim graph. Pydantic models are the source of truth.
Every node carries ``tenant_id``. Node-id derivations live here (not on the
models) so they can change without altering the schema — backends never invent
ids.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from ..hash import sha256_hex
from .taxonomy import Category, Confidence, NodeKind, Polarity, Scope, SourceTier
from .url import canonicalize_url, extract_domain

_NODE_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9_:./@-]{0,254}$"


class Claim(BaseModel):
    tenant_id: str
    claim_id: str = Field(pattern=r"^[0-9a-f]{16}$")
    subject: str = Field(min_length=1)
    category: Category
    polarity: Polarity
    scope: Scope
    claim_text: str = Field(min_length=1)
    evidence_text: str = Field(min_length=1)
    confidence: Confidence
    source_url: str = Field(min_length=1)
    source_tier: SourceTier
    extracted_at: int


class Source(BaseModel):
    tenant_id: str
    url: str = Field(min_length=1)
    title: str = ""
    domain: str = ""
    tier: SourceTier = "tier_4"
    fetched_at: int


class Subject(BaseModel):
    tenant_id: str
    name: str = Field(min_length=1)


class CategoryNode(BaseModel):
    tenant_id: str
    value: Category


class Run(BaseModel):
    tenant_id: str
    run_id: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    signal: str | None = None
    status: Literal["pending", "running", "complete", "failed"]
    created_at: int


class GraphNode(BaseModel):
    id: str = Field(pattern=_NODE_ID_PATTERN)
    kind: NodeKind
    tenant_id: str
    attributes: dict[str, object] = Field(default_factory=dict)


# ── Node-id derivations ────────────────────────────────────────────────

_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_SLUG_TRIM = re.compile(r"^-+|-+$")


def slugify(value: str) -> str:
    lowered = _SLUG_NON_ALNUM.sub("-", value.strip().lower())
    return _SLUG_TRIM.sub("", lowered)


def tenant_node_id(tenant_id: str) -> str:
    return f"tenant:{tenant_id}"


def subject_node_id(name: str) -> str:
    return f"subject:{slugify(name)}"


def category_node_id(value: str) -> str:
    return f"category:{value}"


def run_node_id(run_id: str) -> str:
    return f"run:{run_id}"


def source_node_id(canonical_url: str) -> str:
    """Stable 16-hex source id over the canonical URL — same-URL claims collapse."""
    return f"source:{sha256_hex(canonical_url)[:16]}"


__all__ = [
    "Claim",
    "Source",
    "Subject",
    "CategoryNode",
    "Run",
    "GraphNode",
    "slugify",
    "tenant_node_id",
    "subject_node_id",
    "category_node_id",
    "run_node_id",
    "source_node_id",
    "canonicalize_url",
    "extract_domain",
]
