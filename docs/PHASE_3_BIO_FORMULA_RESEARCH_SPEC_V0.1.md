# Phase 3 Bio Formula Research Specification

**Version:** 0.1  
**Status:** Binding Phase 3 Research Gate  
**Date:** 2026-09-13

## 0. Purpose

Before implementing or validating the Bio V1 Formula Validation Gate, investigate existing Elite Dangerous Exobiology value-calculation methods and determine what can be used as an evidence-based reference for C-CORE.

The current V1 formula is:

```text
signal_count × user-calibrated expected value per signal
```

This formula is currently specified and implemented, but its empirical validity has not been demonstrated by a V1-specific historical backtest.

This phase MUST NOT treat the existing 61.4% result as validation of V1. That result belongs to the separate species-prediction-derived model:

```text
Σ p(s) × base_value(s)
```

## 1. Research Before Implementation

Perform read-only research first. Do not modify `app/**`, `tests/**`, or production Formula code during this research gate.

Investigate existing public Elite Dangerous Exobiology tools and documented calculation methods, including at minimum where available:

- EDMC-BioScan
- ExoBioSearch
- EDMC-Pioneer / related value-calculation code
- other credible public Exobiology value calculators or documented payout models

Prefer primary project repositories, source code, and maintained documentation over forum summaries.

## 2. Questions To Answer

For each relevant external implementation, determine:

1. What inputs are used to estimate Exobiology value?
2. Is value calculated per species, per biological signal, per body, or per system?
3. How are candidate species probabilities or possible species handled?
4. How are multiple biological signals combined?
5. How are First Discovery / First Footfall / other bonuses handled?
6. Does the tool distinguish expected value from confirmed value?
7. Does it use static species values, observed historical values, or user-specific calibration?
8. Does the tool expose a formula that can serve as a reference for C-CORE?
9. What parts are directly supported by game data versus heuristic estimation?
10. What assumptions would be required to transform a species-level value model into a signal-level expected value?

## 3. C-CORE Comparison

Compare the external models against the C-CORE V1 formula.

Explicitly determine whether:

```text
signal_count × expected_value_per_signal
```

is:

- directly supported by an existing established calculation model,
- a defensible simplification of an established model,
- a heuristic requiring empirical validation,
- or unsupported by the available evidence.

Do not silently redefine `expected_value_per_signal`.

If external tools calculate a more defensible expected value, document the mathematical relationship and whether C-CORE should adopt it as a candidate Formula 3-1 revision.

## 4. Evidence Classification

Classify each finding as one of:

- `PRIMARY_GAME_RULE` — directly supported by game/system data or authoritative game behavior.
- `ESTABLISHED_TOOL_MODEL` — implemented by a maintained third-party tool with identifiable source logic.
- `DOCUMENTED_HEURISTIC` — explicitly documented approximation or heuristic.
- `COMMUNITY_REPORT` — forum/Reddit/community observation.
- `UNVERIFIED` — insufficient evidence.

Do not use `COMMUNITY_REPORT` or `UNVERIFIED` as the sole basis for changing the production formula.

## 5. Required Output

Produce a read-only research report containing:

- source/project
- source URL or repository
- formula / calculation logic
- required inputs
- treatment of multiple signals/species
- treatment of bonuses
- evidence classification
- relevance to C-CORE V1
- recommended candidate formula, if any
- unresolved questions

The report MUST explicitly state whether the current V1 formula has an external evidence basis.

## 6. Gate

No V1 Formula Validation Gate implementation begins until this research is complete.

After research:

```text
External model research
        ↓
Define V1 expected-value semantics
        ↓
Freeze V1 baseline formula
        ↓
Implement V1 Historical Replay / backtest
        ↓
Validation ≥ 0.60
        ↓
Chronological holdout ≥ 0.60
        ↓
Production adoption decision
```

If research shows that the current V1 formula is not sufficiently grounded, do not implement a validation harness around an undefined or unjustified formula. First define and document the candidate formula and its assumptions.

## 7. Non-Goals

This phase does NOT:

- change `species_value_master.py`
- resolve BUD-003
- promote V1 to production
- reuse the 61.4% species-prediction result as V1 validation
- implement the V1 backtest
- change production scoring behavior
- introduce a new formula without evidence and explicit approval
