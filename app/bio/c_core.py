"""C-CORE ruleset normalization/evaluation — first vertical slice.

This module deliberately starts with one genus (Aleoida) so the normalized
rule representation and evaluator can be exercised before all 116 species
are converted. BioScan ruleset wording is treated as the upstream input;
the evaluator does not copy BioScan's evaluator implementation.

Statuses are explicit:
- MATCH: all available rule predicates are satisfied.
- NO_MATCH: a supplied predicate is known not to satisfy the rule.
- INSUFFICIENT_DATA: a required input is missing, so the rule cannot be
  decided without guessing.
- RULESET_INCONSISTENCY: the normalized rule itself is internally invalid.

Region semantics follow the ruleset representation: positive region names
must be present, while names prefixed with ``!`` must be absent.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuleStatus(str, Enum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    RULESET_INCONSISTENCY = "RULESET_INCONSISTENCY"


@dataclass(frozen=True)
class BodyContext:
    atmosphere: str | None
    gravity: float | None
    temperature: float | None
    pressure: float | None
    body_type: str | None
    volcanism: str | None
    regions: frozenset[str] | None = None


@dataclass(frozen=True)
class NormalizedRule:
    species_code: str
    species_name: str
    value: int
    atmospheres: frozenset[str] = frozenset()
    min_gravity: float | None = None
    max_gravity: float | None = None
    min_temperature: float | None = None
    max_temperature: float | None = None
    min_pressure: float | None = None
    max_pressure: float | None = None
    body_types: frozenset[str] = frozenset()
    volcanisms: frozenset[str] = frozenset()
    regions: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuleEvaluation:
    species_code: str
    species_name: str
    status: RuleStatus
    reason: str


def _range_status(
    value: float | None,
    minimum: float | None,
    maximum: float | None,
    field_name: str,
) -> tuple[RuleStatus, str] | None:
    if minimum is not None and maximum is not None and minimum > maximum:
        return RuleStatus.RULESET_INCONSISTENCY, f"{field_name}: minimum exceeds maximum"
    if minimum is not None or maximum is not None:
        if value is None:
            return RuleStatus.INSUFFICIENT_DATA, f"{field_name}: value is missing"
        if minimum is not None and value < minimum:
            return RuleStatus.NO_MATCH, f"{field_name}: below minimum"
        if maximum is not None and value > maximum:
            return RuleStatus.NO_MATCH, f"{field_name}: above maximum"
    return None


def evaluate_rule(rule: NormalizedRule, body: BodyContext) -> RuleEvaluation:
    """Evaluate one normalized rule without falling back to guesses."""
    checks: list[tuple[RuleStatus, str]] = []

    if rule.atmospheres:
        if body.atmosphere is None:
            checks.append((RuleStatus.INSUFFICIENT_DATA, "atmosphere: value is missing"))
        elif body.atmosphere not in rule.atmospheres:
            checks.append((RuleStatus.NO_MATCH, "atmosphere: not allowed"))

    for value, minimum, maximum, field_name in (
        (body.gravity, rule.min_gravity, rule.max_gravity, "gravity"),
        (body.temperature, rule.min_temperature, rule.max_temperature, "temperature"),
        (body.pressure, rule.min_pressure, rule.max_pressure, "pressure"),
    ):
        result = _range_status(value, minimum, maximum, field_name)
        if result is not None:
            checks.append(result)

    if rule.body_types:
        if body.body_type is None:
            checks.append((RuleStatus.INSUFFICIENT_DATA, "body_type: value is missing"))
        elif body.body_type not in rule.body_types:
            checks.append((RuleStatus.NO_MATCH, "body_type: not allowed"))

    if rule.volcanisms:
        if body.volcanism is None:
            checks.append((RuleStatus.INSUFFICIENT_DATA, "volcanism: value is missing"))
        elif body.volcanism not in rule.volcanisms:
            checks.append((RuleStatus.NO_MATCH, "volcanism: not allowed"))

    if rule.regions:
        if body.regions is None:
            checks.append((RuleStatus.INSUFFICIENT_DATA, "regions: value is missing"))
        else:
            for region in rule.regions:
                if region.startswith("!"):
                    if region[1:] in body.regions:
                        checks.append((RuleStatus.NO_MATCH, f"regions: excluded region {region[1:]}"))
                elif region not in body.regions:
                    checks.append((RuleStatus.NO_MATCH, f"regions: required region {region} is absent"))

    if any(status is RuleStatus.RULESET_INCONSISTENCY for status, _ in checks):
        status = RuleStatus.RULESET_INCONSISTENCY
    elif any(status is RuleStatus.NO_MATCH for status, _ in checks):
        status = RuleStatus.NO_MATCH
    elif any(status is RuleStatus.INSUFFICIENT_DATA for status, _ in checks):
        status = RuleStatus.INSUFFICIENT_DATA
    else:
        status = RuleStatus.MATCH

    reason = "; ".join(reason for _, reason in checks) if checks else "all predicates satisfied"
    return RuleEvaluation(rule.species_code, rule.species_name, status, reason)


ALEOIDA_RULES: tuple[NormalizedRule, ...] = (
    NormalizedRule(
        species_code="$Codex_Ent_Aleoids_01_Name;",
        species_name="Aleoida Arcus",
        value=7252500,
        atmospheres=frozenset({"CarbonDioxide"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=175.0,
        max_temperature=180.0,
        min_pressure=0.0161,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        volcanisms=frozenset({"None"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Aleoids_02_Name;",
        species_name="Aleoida Coronamus",
        value=6284600,
        atmospheres=frozenset({"CarbonDioxide"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=180.0,
        max_temperature=190.0,
        min_pressure=0.025,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        volcanisms=frozenset({"None"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Aleoids_03_Name;",
        species_name="Aleoida Spica",
        value=3385200,
        atmospheres=frozenset({"Ammonia"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=170.0,
        max_temperature=177.0,
        max_pressure=0.0135,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        regions=("!orion-cygnus-core", "!sagittarius-carina-core"),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Aleoids_04_Name;",
        species_name="Aleoida Laminiae",
        value=3385200,
        atmospheres=frozenset({"Ammonia"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=152.0,
        max_temperature=177.0,
        max_pressure=0.0135,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        regions=("orion-cygnus", "sagittarius-carina"),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Aleoids_05_Name;",
        species_name="Aleoida Gravis",
        value=12934900,
        atmospheres=frozenset({"CarbonDioxide"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=190.0,
        max_temperature=197.0,
        min_pressure=0.054,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        volcanisms=frozenset({"None"}),
    ),
)


def evaluate_aleoida(body: BodyContext) -> list[RuleEvaluation]:
    """Evaluate the five Aleoida species rules in deterministic order."""
    return [evaluate_rule(rule, body) for rule in ALEOIDA_RULES]
