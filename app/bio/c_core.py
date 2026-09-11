"""C-CORE ruleset normalization/evaluation.

Started with one genus (Aleoida, all species single-ruleset) so the
normalized rule representation and evaluator could be exercised before all
116 species are converted; Cactoida followed as the second genus, converted
with the same NormalizedRule/evaluate_rule schema unchanged. BioScan ruleset
wording is treated as the upstream input; the evaluator does not copy
BioScan's evaluator implementation.

Statuses are explicit:
- MATCH: all available rule predicates are satisfied.
- NO_MATCH: a supplied predicate is known not to satisfy the rule.
- INSUFFICIENT_DATA: a required input is missing, so the rule cannot be
  decided without guessing.
- RULE_DEFINITION_ERROR: the normalized rule itself is internally invalid.

RULESET_INCONSISTENCY is reserved for the genus-level runtime signal raised
when a genus has been established by upstream evidence but every species rule
in that genus is rejected. Static rule-definition validation is intentionally
kept separate from that runtime signal.

Region semantics follow the ruleset representation: positive region names
must be present, while names prefixed with ``!`` must be absent.

A species can have more than one ruleset upstream (e.g. Cactoida Vermis'
three alternatives): BioScan ORs them -- any one ruleset matching makes the
species a candidate. NormalizedRule stays one-ruleset-per-entry (several
entries may share a species_code), and aggregate_species_evaluations()
collapses per-ruleset evaluations down to one verdict per species_code.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuleStatus(str, Enum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    RULE_DEFINITION_ERROR = "RULE_DEFINITION_ERROR"
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
        return RuleStatus.RULE_DEFINITION_ERROR, f"{field_name}: minimum exceeds maximum"
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

    if any(status is RuleStatus.RULE_DEFINITION_ERROR for status, _ in checks):
        status = RuleStatus.RULE_DEFINITION_ERROR
    elif any(status is RuleStatus.NO_MATCH for status, _ in checks):
        status = RuleStatus.NO_MATCH
    elif any(status is RuleStatus.INSUFFICIENT_DATA for status, _ in checks):
        status = RuleStatus.INSUFFICIENT_DATA
    else:
        status = RuleStatus.MATCH

    reason = "; ".join(reason for _, reason in checks) if checks else "all predicates satisfied"
    return RuleEvaluation(rule.species_code, rule.species_name, status, reason)


def evaluate_genus_consistency(
    genus_established: bool,
    evaluations: list[RuleEvaluation],
) -> RuleStatus | None:
    """Return the reserved runtime inconsistency signal for an established genus.

    A genus is inconsistent only when upstream evidence establishes the genus
    and every species rule in that genus is rejected. Missing data or static
    rule-definition errors are not silently converted into this signal.
    """
    if not genus_established or not evaluations:
        return None
    if all(result.status is RuleStatus.NO_MATCH for result in evaluations):
        return RuleStatus.RULESET_INCONSISTENCY
    return None


_SPECIES_AGGREGATE_PRIORITY: tuple[RuleStatus, ...] = (
    RuleStatus.MATCH,
    RuleStatus.INSUFFICIENT_DATA,
    RuleStatus.RULE_DEFINITION_ERROR,
    RuleStatus.NO_MATCH,
)


def aggregate_species_evaluations(evaluations: list[RuleEvaluation]) -> list[RuleEvaluation]:
    """Collapse multiple per-ruleset evaluations for the same species_code
    into one verdict, since BioScan's rulesets are ORed within a species:
    any one matching ruleset makes the species a candidate.

    Priority when no ruleset matches is
    MATCH > INSUFFICIENT_DATA > RULE_DEFINITION_ERROR > NO_MATCH -- an
    unresolved "might still be possible" (INSUFFICIENT_DATA) outranks a
    broken rule definition elsewhere in the same species, and only "every
    ruleset explicitly rejects this body" collapses to NO_MATCH.

    Species are returned in the order their species_code first appears;
    the reason is taken from the first evaluation matching the chosen
    status, for determinism.
    """
    by_species: dict[str, list[RuleEvaluation]] = {}
    order: list[str] = []
    for evaluation in evaluations:
        if evaluation.species_code not in by_species:
            by_species[evaluation.species_code] = []
            order.append(evaluation.species_code)
        by_species[evaluation.species_code].append(evaluation)

    aggregated: list[RuleEvaluation] = []
    for species_code in order:
        group = by_species[species_code]
        statuses = {result.status for result in group}
        chosen_status = next(status for status in _SPECIES_AGGREGATE_PRIORITY if status in statuses)
        winner = next(result for result in group if result.status is chosen_status)
        aggregated.append(RuleEvaluation(species_code, winner.species_name, chosen_status, winner.reason))
    return aggregated


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


CACTOIDA_RULES: tuple[NormalizedRule, ...] = (
    NormalizedRule(
        species_code="$Codex_Ent_Cactoid_01_Name;",
        species_name="Cactoida Cortexum",
        value=3667600,
        atmospheres=frozenset({"CarbonDioxide"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=180.0,
        max_temperature=197.0,
        min_pressure=0.025,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        volcanisms=frozenset({"None"}),
        regions=("orion-cygnus",),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Cactoid_02_Name;",
        species_name="Cactoida Lapis",
        value=2483600,
        atmospheres=frozenset({"Ammonia"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=160.0,
        max_temperature=177.0,
        max_pressure=0.0135,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        regions=("sagittarius-carina",),
    ),
    # Cactoida Vermis has three alternative rulesets upstream (OR'd) --
    # all three appear here sharing the same species_code, and
    # evaluate_cactoida() collapses them via aggregate_species_evaluations().
    NormalizedRule(
        species_code="$Codex_Ent_Cactoid_03_Name;",
        species_name="Cactoida Vermis",
        value=16202800,
        atmospheres=frozenset({"SulphurDioxide"}),
        min_gravity=0.265,
        max_gravity=0.276,
        min_temperature=160.0,
        max_temperature=210.0,
        max_pressure=0.005,
        body_types=frozenset({"Rocky body"}),
        volcanisms=frozenset({"None"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Cactoid_03_Name;",
        species_name="Cactoida Vermis",
        value=16202800,
        atmospheres=frozenset({"Water"}),
        min_gravity=0.04,
        max_gravity=0.276,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        volcanisms=frozenset({"None"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Cactoid_03_Name;",
        species_name="Cactoida Vermis",
        value=16202800,
        atmospheres=frozenset({"Water"}),
        min_gravity=0.04,
        max_gravity=0.276,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        volcanisms=frozenset({"water"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Cactoid_04_Name;",
        species_name="Cactoida Pullulanta",
        value=3667600,
        atmospheres=frozenset({"CarbonDioxide"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=180.0,
        max_temperature=197.0,
        min_pressure=0.025,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        volcanisms=frozenset({"None"}),
        regions=("perseus",),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Cactoid_05_Name;",
        species_name="Cactoida Peperatis",
        value=2483600,
        atmospheres=frozenset({"Ammonia"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=160.0,
        max_temperature=177.0,
        max_pressure=0.0135,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        regions=("scutum-centaurus",),
    ),
)


def evaluate_cactoida(body: BodyContext) -> list[RuleEvaluation]:
    """Evaluate the five Cactoida species, OR-collapsing Vermis' three
    alternative rulesets via aggregate_species_evaluations() so the
    returned list has exactly one verdict per species, like evaluate_aleoida().
    """
    per_ruleset = [evaluate_rule(rule, body) for rule in CACTOIDA_RULES]
    return aggregate_species_evaluations(per_ruleset)
