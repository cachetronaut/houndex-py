"""Generic per-role model routing.

The framework does not bundle a model catalog or bind to any provider — that
belongs in application code. What it provides is the *shape* of a routing table:
a mapping from a named role to a model reference and its default generation
parameters.
"""

from __future__ import annotations

from pydantic import BaseModel

# An opaque, provider-agnostic model identifier (e.g. "openai/gpt-4o-mini").
ModelRef = str


class ModelConfig(BaseModel):
    model: ModelRef
    # Default sampling temperature for this role; callers may override.
    temperature: float | None = None


class EmbeddingConfig(BaseModel):
    model: ModelRef
    # Output vector dimension; must match the configured vector store.
    dimension: int


# A routing table keyed by an application-defined role name.
ModelRouting = dict[str, ModelConfig]
