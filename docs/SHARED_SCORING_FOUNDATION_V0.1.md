# EDpj Shared Scoring Foundation

**Version:** 0.1
**Status:** Recovered normative content (BLOCK 6)
**Date:** 2026-09-13
**Scope:** The unified Filter → Horizon → Value → Confidence → Score → Ranking pipeline that both Bio and (historically) Mining action candidates flow through. Documents only what the current codebase depends on; does not restate Mining-only candidate generation or value formulas.

## 0. Provenance

This document recovers normative content that was deleted during the 2026-09-11 Mining/Trade/Market scope-narrowing cleanup, but that the shared `app/scoring/**` pipeline — which Bio candidates (`bio_current_body`/`bio_next_system`/`bio_return`) pass through today — still depends on (`docs/PHASE_F_IMPLEMENTATION_DOC_CONSISTENCY_SPEC_V0.1.md` §8, BLOCK 6).

| Rule (this doc) | Source document | Source section | Deletion commit |
|---|---|---|---|
| §1.1 Component confidence constants | `docs/PHASE_2_0_DESIGN_BASELINE_V0.1.md` | §1.1 | `415b425c4f7bdc4863e5534000a01bbabe6269e3` |
| §1.2 Confidence propagation formula | `docs/PHASE_2_5_CONFIDENCE_EXPLAINABILITY_DESIGN_BASELINE_V0.1.md` | §7.2 | `adca45c2b432bdc76879ab6ba013f0eeb5b3191d` |
| §1.3 Candidate-selection confidence gate | `docs/PHASE_2_4_RANKING_DESIGN_BASELINE_V0.1.md` (adopting `IMPLEMENTATION_SPEC_V0.2.md` §12.3 unchanged) | §2 | `27bbe21bef2265a00aafde91fccf0074cf833784` |
| §1.4 Species-value confidence vocabulary | *(not recovered here — already current; cross-referenced only)* | — | — |
| §2 Ranking key / tie-break | `docs/PHASE_2_4_RANKING_DESIGN_BASELINE_V0.1.md` | §3 | `27bbe21bef2265a00aafde91fccf0074cf833784` |
| §3 DTOs (Recommendation/RejectedCandidate/IncompleteCandidate/DataSource/ReasonFact/NextActionResponse) | `docs/PHASE_2_0_DESIGN_BASELINE_V0.1.md`, `docs/RECOMMENDATION_EXPLAINABILITY_SPEC_V0.1.md`, `docs/PHASE_2_4_RANKING_DESIGN_BASELINE_V0.1.md` | §2.1–2.7 / §2–4 / §5 | `415b425c4f7bdc4863e5534000a01bbabe6269e3` / `e7989a6efb17c773d0f172ecf5bd3046e857378f` / `27bbe21bef2265a00aafde91fccf0074cf833784` |
| §4 ReasonFact generation | `docs/PHASE_2_5D_EXPLAINABILITY_DESIGN_BASELINE_V0.1.md` | §1–2 | `32801e9808c73e74ad48f47931cb2edb3d5f85ef` |

## 1. Confidence — four separate axes

The word "confidence" is used in this codebase for **four distinct concepts that must not be conflated**. Recovering these documents surfaced exactly this risk: they look similar and were never previously listed side by side.

### 1.1 Component confidence (per time-segment)

How trustworthy a single `HorizonComponent`/`TimeEstimate` is, based on how it was obtained:

```python
MEASURED_CONFIDENCE = 1.00
ESTIMATED_CONFIDENCE = 0.85
UNAVAILABLE_CONFIDENCE = 0.60   # reserved — not used by any current confidence calculation
```

These are the currently-live values (they replaced an earlier Phase 0-C provisional scale of `0.75`/`0.20`/`0.50`, which no longer applies).

Current code: `app/routing/time.py`.

### 1.2 Confidence propagation (per candidate)

How a candidate's overall confidence is composed from its component confidences plus generation-time uncertainty and data freshness:

```text
final_confidence
  = generation_confidence
  × Π(HorizonComponent confidence)
  × market_freshness
```

`generation_confidence` is Candidate Generation's own per-candidate uncertainty (e.g., an unverifiable "personally unscanned" assumption — see `docs/BIO_STATE_CANDIDATE_FOUNDATION_V0.1.md` §3.2's `USER_UNSCANNED_UNKNOWN_CONFIDENCE`). `market_freshness` is `1.0` whenever a candidate did not depend on any market observation at all (true for all three Bio actions today), so this factor is a no-op for Bio.

Current code: `app/scoring/confidence.py`.

### 1.3 Candidate-selection confidence gate

A separate threshold used only to decide which scoreable candidates are eligible for ranking — never blended into the ranking order itself:

```python
MIN_ACTION_CONFIDENCE = 0.50

eligible = [c for c in complete if c.confidence >= MIN_ACTION_CONFIDENCE]
below_threshold = [c for c in complete if c.confidence < MIN_ACTION_CONFIDENCE]
```

A candidate below this threshold is not discarded — it is kept as an auditable `RejectedCandidate(category="score", reason_code="confidence_below_threshold")` (§3).

Current code: `app/scoring/ranking.py`.

### 1.4 Species-value confidence (cross-reference only, not recovered here)

`docs/EXOBIOLOGY_RANKING_CANONICAL_SPEC_V0.1.md` §5 defines `HIGH`/`MEDIUM`/`DISPUTED` for how trustworthy a *species' fixed base value* is — a property of `SpeciesValueMaster`, unrelated to any action candidate's confidence above. **This document does not assume §1.1–1.3 and this vocabulary are, or should become, the same axis.** Whether they should be unified or kept independent is left as an open question for a future confidence-vocabulary decision, not decided here.

## 2. Ranking key (action-candidate ranking — distinct from species ranking)

Once candidates pass the confidence gate (§1.3), they are ordered by a fully deterministic sort key:

```text
1. score_per_hour         DESC   (primary key)
2. expected_value         DESC   (tie-break 1: prefer larger total at equal rate)
3. action_horizon_seconds ASC    (tie-break 2: prefer shorter time at equal rate and value)
4. target_id              ASC    (final deterministic tie-break)
```

`target_id` is a display/comparison-only identifier, not a DB key, relying on the invariant that the same `(action, target)` pair is never generated twice within one pipeline run.

**This is not the same concept as `docs/EXOBIOLOGY_RANKING_CANONICAL_SPEC_V0.1.md`'s ranking.** This section ranks *which action to take next* (e.g. `bio_current_body` vs. `bio_next_system` vs., historically, `mining_sell`); the canonical spec ranks *which species within one body's biology* to prioritize. The two must not be conflated — they operate at different levels of the same overall recommendation.

Current code: `app/scoring/ranking.py`.

## 3. DTOs

```python
class RejectedCandidate:
    category: str        # "filter" (excluded before scoring) | "score" (ranked below the winner)
    action: str
    target_id: str
    reason_code: str
    value: float | None = None
    comparison: float | None = None

class IncompleteCandidate:
    action: str
    target: BioTarget | MiningTarget
    breakdown: dict[str, HorizonComponent]
    blocking_segments: list[str]
    reason: str
    expected_value: float | None = None
    value_unavailable_reason: str | None = None

class DataSource:
    name: str
    observed_at: dt.datetime | None
    received_at: dt.datetime | None
    freshness: float | None

class ReasonFact:
    factor: str
    effect: str            # "positive" | "negative"
    value: float
    comparison: float | None

class Recommendation:
    action: str
    target: BioTarget | MiningTarget
    expected_value: float
    action_horizon_seconds: float
    score_per_hour: float
    confidence: float
    breakdown: dict[str, HorizonComponent]
    data_sources: list[DataSource] = field(default_factory=list)
    reasons: list[ReasonFact] = field(default_factory=list)
    rejected: list[RejectedCandidate] = field(default_factory=list)
    narration: str | None = None

class NextActionResponse:
    next_action: str | None
    recommendation: Recommendation | None
    alternatives: list[Recommendation]
    incomplete: list[IncompleteCandidate]
    rejected: list[RejectedCandidate]
    reason: str | None
```

`incomplete` is never a `RejectedCandidate` — a candidate that is merely missing an input (e.g. `value_unavailable_reason="species value model not implemented"`, historically true for all three Bio actions) is kept separate so it can recover automatically once the missing input exists, without any change to candidate generation.

Current code: `app/scoring/models.py`, `app/scoring/ranking.py`.

## 4. ReasonFact generation (explainability)

Each `ReasonFact.effect` is either `"positive"` or `"negative"`, describing whether that factor pushed the candidate's standing up or down relative to `comparison`. `ReasonFact`/`DataSource` population is retrofitted onto the Horizon/Value/Confidence/Score stages, not generated by a separate narration step.

Current code: `app/scoring/reason_facts.py`, `app/scoring/data_sources.py`.

## 5. Explicit non-goals of this document

- Does not define or restate `expected_value_base = Σ p(s) × base_value(s)`, or any Bio value formula. See `docs/PHASE_3_BIO_VALUE_MODEL_V1_DESIGN_BASELINE_V0.1.md` and `docs/BIO_EXTERNAL_DATA_VALIDATION_SPEC_V0.1.md`.
- Does not define or change V1 (`signal_count × user-calibrated expected value per signal`). See `docs/EXOBIOLOGY_RANKING_CANONICAL_SPEC_V0.1.md` §1.
- Does not unify or otherwise decide the relationship between §1.1–1.3's action-candidate confidence and §1.4's species-value confidence vocabulary — left open.
- Does not restate Mining-specific scoring content (effective price, mining cycle calibration, `MiningTarget` fields) — out of current Bio/C-CORE scope per `README.md`.
- Does not modify `app/**`, `tests/**`, `known_dangling.txt`, any existing canonical spec, or `README.md`.

## 6. Change history

- 2026-09-13: v0.1 — Recovered from `docs/PHASE_2_0_DESIGN_BASELINE_V0.1.md`, `docs/PHASE_2_4_RANKING_DESIGN_BASELINE_V0.1.md`, `docs/PHASE_2_5_CONFIDENCE_EXPLAINABILITY_DESIGN_BASELINE_V0.1.md`, `docs/PHASE_2_5D_EXPLAINABILITY_DESIGN_BASELINE_V0.1.md`, and `docs/RECOMMENDATION_EXPLAINABILITY_SPEC_V0.1.md` (all deleted 2026-09-11 during Mining/Trade/Market scope removal) per BLOCK 6 of `docs/PHASE_F_IMPLEMENTATION_DOC_CONSISTENCY_SPEC_V0.1.md` §8. The four confidence axes and the two ranking concepts are recorded as explicitly separate to prevent the conflation risk their similar naming creates.
