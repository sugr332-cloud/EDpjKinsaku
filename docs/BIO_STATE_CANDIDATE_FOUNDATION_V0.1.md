# EDpj Bio State / Candidate Generation Foundation

**Version:** 0.1
**Status:** Recovered normative content (BLOCK 6)
**Date:** 2026-09-13
**Scope:** Bio state detection and Bio candidate generation (`bio_current_body` / `bio_next_system` / `bio_return`) only. Value calculation (V1, species prediction) is out of scope — see `docs/PHASE_3_BIO_VALUE_MODEL_V1_DESIGN_BASELINE_V0.1.md` and `docs/BIO_EXTERNAL_DATA_VALIDATION_SPEC_V0.1.md` for that layer.

## 0. Provenance

This document does not introduce new policy. It re-places normative content that already existed, was deleted along with Mining/Trade-scoped material during the 2026-09-11 scope-narrowing cleanup, and is still cited by live code (`docs/PHASE_F_IMPLEMENTATION_DOC_CONSISTENCY_SPEC_V0.1.md` §8, BLOCK 6). Only the Bio-relevant portion of each source is carried forward; Mining-only sections of the same source documents are intentionally omitted.

| Rule (this doc) | Source document | Source section | Deletion commit |
|---|---|---|---|
| §1 Bio state fields | `SPECIFICATION_V0.4.md` | §6.2 | `be3631575282d3294d2a8d46af2155b3b398fc66` |
| §2 EDDN subscription for candidate discovery | `SPECIFICATION_V0.4.md` | §13.2 | same |
| §3 Candidate generation conditions | `PHASE_2_2_CANDIDATE_GENERATION_DESIGN_BASELINE_V0.1.md` | §5.1–5.3 | `4082ddc3e38809c2da769cddfd19f213e755f0c4` |
| §3 Bio state detection fields | `IMPLEMENTATION_SPEC_V0.2.md` | §8.2/§8.3 | `d61a5c8af3c09e29700b478ee6200b24b8446a0b` |
| §4 `distance_limit_ly` default | `IMPLEMENTATION_SPEC_V0.2.md` | §12.1 | same |
| §5 `BioTarget` fields | `IMPLEMENTATION_SPEC_V0.2.md` | §21 (Bio portion only; `MiningTarget` in the same section is not carried forward) | same |
| §6 Exploration-state horizon extension | `SPECIFICATION_V0.4.md` (identical text also in `IMPLEMENTATION_SPEC_V0.2.md` §20) | §21 | `be36315...` |

Each rule below is recovered only to the extent the current codebase already depends on it. This document does not add new behavior.

## 1. Bio state (detection layer)

The following are tracked as distinct, separately-derived facts about "the current situation," not conflated into one flag:

- whether the current body has an active biological signal (`has_bio_signals`)
- whether the player has personally scanned the current body — **cannot currently be determined** (see §3's `USER_UNSCANNED_UNKNOWN_CONFIDENCE` note; the `system_discovery`/`body_discovery` tables §6 describes, which would make this determinable, do not exist yet)
- whether unsold organic data exists (`unsold_bio_value` concept — see `app/bio/conditions.py`'s unsold-count detector; the credit-value conversion of this count is Value-layer, out of this document's scope)
- nearest station offering Vista Genomics redemption

Current code: `app/api/state.py`, `app/bio/conditions.py`.

## 2. EDDN subscription for Bio candidate discovery

Bio candidate generation (unlike population-level formula validation, which uses `scanorganic/1` per `docs/BIO_EXTERNAL_DATA_VALIDATION_SPEC_V0.1.md`) is designed around two different EDDN schemas:

```text
journal/1          — other commanders' exploration-journal-like events
                      (FSSDiscoveryScan, FSSAllBodiesFound, Scan, ...)
fssbodysignals/1    — per-body signal type/count reports
```

These are deliberately kept structurally separate from the player's own journal (`journal_events`): EDDN rows describe *other* commanders' observations of the galaxy, not "me," and must never be picked up by code that assumes every row is the player's own state (e.g. the Phase 0-A state reducer). Current table names: `eddn_journal_observations`, `body_bio_signals`.

Market observations alone must never be treated as sufficient evidence that a Bio candidate exists.

Current code: `app/collectors/eddn.py`, `app/db/models/eddn.py`.

## 3. Candidate generation

### 3.1 `bio_current_body`

```text
condition: has_bio_signals == true on the current body
target: the current body itself
```

Known limitation: since the player's own `FSSBodySignals` journal event is not merged into `body_bio_signals` (only EDDN-sourced rows are), a body the player's own game has flagged will not be detected here until independently reported over EDDN.

### 3.2 `bio_next_system`

```text
1. take the current system's coordinates
2. search locally-cached systems within distance_limit_ly (straight-line, not jump distance)
3. for each candidate system, find bodies with a biological signal via body_bio_signals
4. "personally unscanned" cannot be determined — never assert scanned or unscanned;
   always candidate, with generation_confidence lowered to reflect the uncertainty
5. First Discovery upside is not computed here (Value-layer concern)
```

The local-DB-only constraint (§2) applies directly: a system within `distance_limit_ly` that has never been cached locally will not appear as a candidate, regardless of actual in-game distance.

### 3.3 `bio_return`

```text
condition: unsold organic sample count > 0
target: nearest station with Vista Genomics (straight-line distance)
```

The unsold count is derived from `ScanOrganic` event count minus `SellOrganicData` event count. Converting this count into a credit value is explicitly a Value-layer concern (see the canonical V1/species-prediction docs), not this document's.

Current code: `app/bio/candidates.py`, `app/bio/conditions.py`.

## 4. `distance_limit_ly` default

```python
DEFAULT_DISTANCE_LIMIT_LY = 200.0
```

Current code: `app/bio/candidates.py`.

## 5. `BioTarget` DTO (Bio portion only)

```python
class BioTarget:
    body_name: str
    system_name: str          # from Journal StarSystem / System.name — never derived by splitting body_name
    body_suffix: str
    arrival_dist_from_star_ls: float | None
    gravity: float | None = None
    colony_spacing_m: int | None = None
    predicted_species: list = field(default_factory=list)   # populated by Value stage, not candidate generation
    system_address: int | None = None
    body_id: int | None = None
```

`predicted_species`/`colony_spacing_m` are Value-stage fields; candidate generation leaves them empty/`None`. The corresponding `MiningTarget` fields defined alongside this DTO in the original source are Mining-scoped and are not carried forward here.

Current code: `app/scoring/models.py`.

## 6. Exploration-state horizon extension (not yet implemented)

This section is recovered for traceability even though nothing currently implements it — it is a known, documented gap, not an accidental omission.

```sql
CREATE TABLE system_discovery (
    system_address    BIGINT PRIMARY KEY,
    honked            BOOLEAN NOT NULL DEFAULT FALSE,
    body_count        INTEGER,
    all_bodies_found  BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE body_discovery (
    body_id      BIGINT PRIMARY KEY,
    fss_scanned  BOOLEAN NOT NULL DEFAULT FALSE,
    dss_scanned  BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Once these exist, a Bio candidate's horizon should account for outstanding exploration steps:

```text
bio_horizon =
    route(current location → target system)
  + honk_time              if system scan incomplete
  + fss_time(body_count)   if body scan incomplete
  + supercruise_time
  + dss_time               if probe incomplete
  + descent + sample + ascent
```

This is also why `app/bio/conditions.py`'s "personally scanned" determination is currently impossible (§3.2): the tables that would make it possible do not exist yet.

## 7. Explicit non-goals of this document

- Does not define or restate `expected_value_base = Σ p(s) × base_value(s)`. That concept already lives in, and is superseded by, `docs/PHASE_3_BIO_VALUE_MODEL_V1_DESIGN_BASELINE_V0.1.md` and `docs/BIO_EXTERNAL_DATA_VALIDATION_SPEC_V0.1.md`.
- Does not define or change V1 (`signal_count × user-calibrated expected value per signal`). See `docs/EXOBIOLOGY_RANKING_CANONICAL_SPEC_V0.1.md` §1 for that definition.
- Does not include Mining-specific candidate generation, state detection, or DTO fields (`MiningTarget`, `mining_active`, ring detection, etc.) — those remain out of current Bio/C-CORE scope per `README.md`.
- Does not modify `app/**`, `tests/**`, `known_dangling.txt`, any existing canonical spec, or `README.md`.

## 8. Change history

- 2026-09-13: v0.1 — Recovered from `SPECIFICATION_V0.4.md`, `IMPLEMENTATION_SPEC_V0.2.md`, and `PHASE_2_2_CANDIDATE_GENERATION_DESIGN_BASELINE_V0.1.md` (all deleted 2026-09-11 during Mining/Trade/Market scope removal) per BLOCK 6 of `docs/PHASE_F_IMPLEMENTATION_DOC_CONSISTENCY_SPEC_V0.1.md` §8. Only content the current codebase actually depends on is included; Mining-only sections of the same source documents are not carried forward.
