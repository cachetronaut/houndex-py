"""Structured I/O schemas for the generic RAG agents. These are the contracts an
agent declares as its structured-output target, so a malformed model response is
a validation error rather than a downstream surprise.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from .taxonomy import Category, Confidence, Polarity, ReconciliationDecision, Scope


class SearchQuery(BaseModel):
    query: str = Field(min_length=1)
    intent: str = Field(min_length=1)


class SearchPlan(BaseModel):
    subject: str = Field(min_length=1)
    signal_context: str | None = None
    queries: list[SearchQuery] = Field(min_length=1, max_length=12)


class ExtractedClaim(BaseModel):
    category: Category
    polarity: Polarity
    scope: Scope
    claim_text: str = Field(min_length=1)
    evidence_text: str = Field(min_length=1)
    confidence: Confidence


class ExtractedClaims(BaseModel):
    claims: list[ExtractedClaim]


class ReconciliationResult(BaseModel):
    decision: ReconciliationDecision
    matched_claim_id: str | None = Field(default=None, pattern=r"^[0-9a-f]{16}$")
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def _check_match(self) -> ReconciliationResult:
        has_match = self.matched_claim_id is not None
        if self.decision == "new_claim" and has_match:
            raise ValueError("new_claim must not carry matched_claim_id")
        if self.decision != "new_claim" and not has_match:
            raise ValueError(f"{self.decision} requires matched_claim_id")
        return self


# Traffic-light grounding verdict for one assertion against its cited evidence:
# ``green`` fully grounded, ``yellow`` partially, ``red`` unsupported.
Verdict = Literal["red", "yellow", "green"]


class CitationVerdict(BaseModel):
    verdict: Verdict
    evidence: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1)
