"""Pure glue between parsed CLI input and the framework engine (core + evals).
No I/O, no process state — so every command's logic is unit-testable in memory.
Mirrors the TypeScript ``engine.ts``.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from houndex_core import compute_claim_id
from houndex_core.schemas import Claim, OutputEnvelope, TraceEntry
from houndex_core.storage import ClaimSearchInput, StorageAdapter
from houndex_core.tenant import TenantContext
from houndex_evals import EvalFixture, EvalRubricConfig, GraphState
from pydantic import BaseModel


def build_claim(tenant_id: str, content: Mapping[str, Any]) -> Claim:
    """Attach tenant + content-addressed id to supplied claim content (snake_case)."""
    claim_id = compute_claim_id(
        tenant_id=tenant_id,
        subject=content["subject"],
        claim_text=content["claim_text"],
        source_url=content["source_url"],
    )
    return Claim.model_validate({**content, "tenant_id": tenant_id, "claim_id": claim_id})


def parse_claims(text: str, fmt: Literal["json", "jsonl"]) -> list[dict[str, Any]]:
    """Parse a claims file: a JSON array, or JSONL (one claim object per line)."""
    if fmt == "jsonl":
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    else:
        loaded = json.loads(text)
        if not isinstance(loaded, list):
            raise ValueError("claims file must be a JSON array")
        rows = loaded
    return [dict(row) for row in rows]


def build_answer_envelope(
    tenant_id: str, query: str, claims: Sequence[Claim], generated_at: int
) -> OutputEnvelope[dict[str, Any]]:
    """An extractive, verified-by-construction answer envelope from retrieved claims."""
    return OutputEnvelope[dict[str, Any]](
        tenant_id=tenant_id,
        generated_at=generated_at,
        trace=[TraceEntry(claim_id=claim.claim_id, mechanism="vector_search") for claim in claims],
        payload={
            "query": query,
            "answer": " ".join(claim.claim_text for claim in claims),
            "citations": [claim.claim_id for claim in claims],
        },
    )


def default_verify_fixture() -> EvalFixture:
    """Floor trace_resolution + envelope_validity at 1.0, so an answer citing an
    unknown claim or failing schema validation is a hard FAIL."""
    return EvalFixture(
        name="cli-verify",
        description="Ad-hoc CLI verification of a supplied answer envelope.",
        rubric=EvalRubricConfig(floors={"trace_resolution": 1, "envelope_validity": 1}),
    )


async def resolve_graph(
    adapter: StorageAdapter, tenant: TenantContext, claim_ids: Sequence[str] | None = None
) -> GraphState:
    """Known-claim universe: an explicit id list (self-contained / ephemeral runs)
    or every claim the configured store holds for the tenant."""
    if claim_ids is not None:
        return GraphState(claim_ids=list(claim_ids))
    claims = await adapter.search_claims(ClaimSearchInput(tenant=tenant))
    return GraphState(claim_ids=[claim.claim_id for claim in claims])


class VerifyFile(BaseModel):
    """``verify <file>`` input: an answer envelope + optional self-contained claim universe."""

    envelope: Any = None
    claim_ids: list[str] | None = None


class EvalCase(BaseModel):
    fixture: EvalFixture
    envelope: Any = None


class EvalFile(BaseModel):
    """``eval <file>`` input: fixture + envelope cases + optional claim universe."""

    claim_ids: list[str] | None = None
    cases: list[EvalCase]
