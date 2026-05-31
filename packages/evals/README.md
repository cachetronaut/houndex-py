# houndex-evals (Python)

The verification engine: a deterministic, in-process rubric that scores an
`OutputEnvelope` against an evidence store. This is the per-transaction verifier
a pipeline calls on each answer. The `houndex-cli` `verify` and `eval` commands
wrap this same engine, so a CLI verdict and a library verdict are identical.
Mirrors the TypeScript `@houndex/evals` package.

## What it provides

- **`score_envelope(fixture, value, graph)`** — scores an envelope on three
  domain-agnostic dimensions:
  - `trace_resolution` — every claim id in the envelope's trace resolves to a
    known claim in the supplied graph state.
  - `envelope_validity` — the value round-trips through the `OutputEnvelope`
    model. A malformed envelope is a hard failure regardless of other scores.
  - `determinism` — canonical-JSON hash against the fixture's baseline; with no
    baseline this sub-score is skipped and the weight is renormalized.
- **`EvalFixture`** — declares structural expectations (minimum trace entries,
  required claim ids) and rubric configuration (weights, floors, baseline hash).
- **`format_report`** — renders scored fixtures as a Markdown regression report.

## Usage

```python
from houndex_evals import GraphState, score_envelope

score = score_envelope(fixture, answer_envelope, GraphState(claim_ids=claim_ids))
if not score.passed:
    ...  # the answer is not grounded in the evidence store
```

Set a floor of `1.0` on `trace_resolution` and `envelope_validity` to fail any
answer that cites an unknown claim or is structurally invalid.
