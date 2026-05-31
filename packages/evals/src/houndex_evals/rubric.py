"""Generic ``OutputEnvelope`` rubric. Pure, deterministic. Scores an envelope on
trace resolution, envelope validity (a hard gate), and canonical-JSON
determinism. Mirrors the TypeScript rubric.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from houndex_core import canonical_json, sha256_hex
from houndex_core.schemas import OutputEnvelope
from pydantic import ValidationError

from .fixture import EvalFixture

SUB_SCORE_NAMES = ("trace_resolution", "envelope_validity", "determinism")
_DEFAULT_WEIGHTS = {name: 1 / 3 for name in SUB_SCORE_NAMES}

_EnvelopeModel = OutputEnvelope[object]


@dataclass(frozen=True)
class GraphState:
    claim_ids: Sequence[str]


@dataclass
class RubricScore:
    trace_resolution: float
    envelope_validity: float
    determinism: float | None
    total: float
    passed: bool
    notes: list[str] = field(default_factory=list)


def hash_envelope(value: Any) -> str:
    """Canonical-JSON SHA-256 of any JSON-serializable value, prefixed ``sha256:``."""
    return f"sha256:{sha256_hex(canonical_json(value))}"


def _trace_claim_ids(parsed: _EnvelopeModel) -> list[str]:
    return [entry.claim_id for entry in parsed.trace]


def score_trace_resolution(parsed: _EnvelopeModel, graph: GraphState) -> tuple[float, str]:
    cited = _trace_claim_ids(parsed)
    if not cited:
        return 1.0, "no trace entries to resolve"
    known = set(graph.claim_ids)
    resolved = [cid for cid in cited if cid in known]
    return len(resolved) / len(cited), (
        f"{len(resolved)}/{len(cited)} trace claim ids resolve in the graph"
    )


def score_envelope_validity(value: Any) -> tuple[float, str, _EnvelopeModel | None]:
    try:
        parsed = _EnvelopeModel.model_validate(value)
    except ValidationError as error:
        first = error.errors()[0]["msg"] if error.errors() else "unknown"
        return 0.0, f"envelope failed schema: {first}", None
    return 1.0, "envelope round-trips through the base schema", parsed


def score_determinism(
    parsed: _EnvelopeModel, value: Any, fixture: EvalFixture
) -> tuple[float | None, str]:
    baseline = fixture.rubric.baseline_hash
    if baseline is None:
        return None, "no baseline hash — sub-score skipped"
    if hash_envelope(value) == baseline:
        return 1.0, "envelope hash matches baseline exactly"
    required = set(fixture.expected.required_claim_ids)
    if not required:
        return 0.0, "hash drift; no required_claim_ids to fall back on"
    cited = set(_trace_claim_ids(parsed))
    intersection = len(required & cited)
    union = len(required | cited)
    jaccard = 0.0 if union == 0 else intersection / union
    return jaccard, f"hash drift; jaccard over required_claim_ids = {jaccard:.3f}"


def score_envelope(fixture: EvalFixture, value: Any, graph: GraphState) -> RubricScore:
    val_score, val_note, parsed = score_envelope_validity(value)
    if parsed is not None:
        res_score, res_note = score_trace_resolution(parsed, graph)
        det_score, det_note = score_determinism(parsed, value, fixture)
    else:
        res_score, res_note = 0.0, "skipped — envelope invalid"
        det_score, det_note = 0.0, "skipped — envelope invalid"

    measured: dict[str, float] = {"trace_resolution": res_score, "envelope_validity": val_score}
    if det_score is not None:
        measured["determinism"] = det_score

    weights = {**_DEFAULT_WEIGHTS, **fixture.rubric.weights}
    total_weight = sum(weights.get(key, 0.0) for key in measured)
    total = (
        0.0
        if total_weight == 0
        else sum(score * weights.get(key, 0.0) for key, score in measured.items()) / total_weight
    )

    floors = fixture.rubric.floors
    failures: list[str] = []
    for key, score in measured.items():
        floor = floors.get(key, 0.0)
        if score < floor:
            failures.append(f"{key}: {score:.3f} < floor {floor:.3f}")
    if val_score == 0:
        failures.append("envelope failed schema validation")
    trace_count = len(parsed.trace) if parsed is not None else 0
    if trace_count < fixture.expected.min_trace_entries:
        failures.append(f"trace entries {trace_count} < min {fixture.expected.min_trace_entries}")

    return RubricScore(
        trace_resolution=res_score,
        envelope_validity=val_score,
        determinism=det_score,
        total=total,
        passed=not failures,
        notes=[
            f"trace_resolution: {res_note}",
            f"envelope_validity: {val_note}",
            f"determinism: {det_note}",
            *([f"failures: {'; '.join(failures)}"] if failures else []),
        ],
    )
