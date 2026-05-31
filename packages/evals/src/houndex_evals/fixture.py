"""Regression-fixture schema. A fixture declares structural expectations about
an ``OutputEnvelope`` — never byte-exact bodies, so model/prompt drift doesn't
break the suite; only a real regression does. Mirrors the TypeScript
``EvalFixture``.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class EvalExpected(BaseModel):
    min_trace_entries: int = 0
    required_claim_ids: list[str] = Field(default_factory=list)


class EvalRubricConfig(BaseModel):
    weights: dict[str, float] = Field(default_factory=dict)
    floors: dict[str, float] = Field(default_factory=dict)
    baseline_hash: str | None = None


class EvalFixture(BaseModel):
    name: str
    description: str = Field(min_length=1)
    expected: EvalExpected = Field(default_factory=EvalExpected)
    rubric: EvalRubricConfig = Field(default_factory=EvalRubricConfig)

    @field_validator("name")
    @classmethod
    def _kebab(cls, value: str) -> str:
        if _KEBAB.match(value) is None:
            raise ValueError("name must be kebab-case")
        return value
