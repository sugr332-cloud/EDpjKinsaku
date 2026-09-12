"""C-CORE ruleset normalization/evaluation.

Started with one genus (Aleoida, all species single-ruleset) so the
normalized rule representation and evaluator could be exercised before all
116 species are converted; Cactoida, Concha, Fonticulua, and Frutexa
followed with the same NormalizedRule/evaluate_rule schema unchanged.
BioScan ruleset wording is treated as the upstream input; the evaluator
does not copy BioScan's evaluator implementation.

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
three alternatives, or Concha Renibus' five): BioScan ORs them -- any one
ruleset matching makes the species a candidate. NormalizedRule stays
one-ruleset-per-entry (several entries may share a species_code), and
aggregate_species_evaluations() collapses per-ruleset evaluations down to
one verdict per species_code.
"""
from __future__ import annotations

from collections.abc import Callable
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


CONCHA_RULES: tuple[NormalizedRule, ...] = (
    # Concha Renibus has five alternative rulesets upstream (OR'd), the
    # largest species-level OR case converted so far (Cactoida Vermis had
    # three) -- collapsed the same way by aggregate_species_evaluations()
    # in evaluate_concha().
    NormalizedRule(
        species_code="$Codex_Ent_Conchas_01_Name;",
        species_name="Concha Renibus",
        value=4572400,
        atmospheres=frozenset({"Ammonia"}),
        min_gravity=0.04,
        max_gravity=0.045,
        min_temperature=176.0,
        max_temperature=177.0,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        volcanisms=frozenset({"silicate", "metallic"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Conchas_01_Name;",
        species_name="Concha Renibus",
        value=4572400,
        atmospheres=frozenset({"CarbonDioxide"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=180.0,
        min_pressure=0.025,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        volcanisms=frozenset({"None"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Conchas_01_Name;",
        species_name="Concha Renibus",
        value=4572400,
        atmospheres=frozenset({"Methane"}),
        min_gravity=0.04,
        max_gravity=0.15,
        min_temperature=78.0,
        max_temperature=100.0,
        min_pressure=0.01,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        volcanisms=frozenset({"silicate", "metallic"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Conchas_01_Name;",
        species_name="Concha Renibus",
        value=4572400,
        atmospheres=frozenset({"Water"}),
        min_gravity=0.04,
        max_gravity=0.65,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        volcanisms=frozenset({"None"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Conchas_01_Name;",
        species_name="Concha Renibus",
        value=4572400,
        atmospheres=frozenset({"Water"}),
        min_gravity=0.04,
        max_gravity=0.65,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        volcanisms=frozenset({"water"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Conchas_02_Name;",
        species_name="Concha Aureolas",
        value=7774700,
        atmospheres=frozenset({"Ammonia"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=152.0,
        max_temperature=177.0,
        max_pressure=0.0135,
        body_types=frozenset({"Rocky body", "High metal content body"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Conchas_03_Name;",
        species_name="Concha Labiata",
        value=2352400,
        atmospheres=frozenset({"CarbonDioxide"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=150.0,
        max_temperature=200.0,
        min_pressure=0.002,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        volcanisms=frozenset({"None"}),
    ),
    # BioScan's raw catalog value for Biconcavis is 16777215 (2**24-1, an
    # integer-overflow-shaped number) -- species_value_master.py's
    # cross-reference investigation already corrected this to 19010800
    # (confidence="disputed", matching Fonticulua Segmentatus/Tussock
    # Stigmasis). NormalizedRule.value uses that corrected figure, not the
    # BioScan raw value.
    NormalizedRule(
        species_code="$Codex_Ent_Conchas_04_Name;",
        species_name="Concha Biconcavis",
        value=19010800,
        atmospheres=frozenset({"Nitrogen"}),
        min_gravity=0.053,
        max_gravity=0.275,
        min_temperature=42.0,
        max_temperature=52.0,
        max_pressure=0.0047,
        body_types=frozenset({"Rocky body", "High metal content body"}),
        volcanisms=frozenset({"None"}),
    ),
)


def evaluate_concha(body: BodyContext) -> list[RuleEvaluation]:
    """Evaluate the four Concha species, OR-collapsing Renibus' five
    alternative rulesets via aggregate_species_evaluations() so the
    returned list has exactly one verdict per species, like evaluate_aleoida()
    and evaluate_cactoida().
    """
    per_ruleset = [evaluate_rule(rule, body) for rule in CONCHA_RULES]
    return aggregate_species_evaluations(per_ruleset)


# Fonticulua: all 6 species have exactly one ruleset each (like Aleoida),
# and none constrain volcanism at all.
FONTICULUA_RULES: tuple[NormalizedRule, ...] = (
    NormalizedRule(
        species_code="$Codex_Ent_Fonticulus_01_Name;",
        species_name="Fonticulua Segmentatus",
        value=19010800,
        atmospheres=frozenset({"Neon", "NeonRich"}),
        min_gravity=0.25,
        max_gravity=0.276,
        min_temperature=50.0,
        max_temperature=75.0,
        max_pressure=0.006,
        body_types=frozenset({"Icy body"}),
        volcanisms=frozenset({"None"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fonticulus_02_Name;",
        species_name="Fonticulua Campestris",
        value=1000000,
        atmospheres=frozenset({"Argon"}),
        min_gravity=0.027,
        max_gravity=0.276,
        min_temperature=50.0,
        max_temperature=150.0,
        body_types=frozenset({"Icy body", "Rocky ice body"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fonticulus_03_Name;",
        species_name="Fonticulua Upupam",
        value=5727600,
        atmospheres=frozenset({"ArgonRich"}),
        min_gravity=0.209,
        max_gravity=0.276,
        min_temperature=61.0,
        max_temperature=125.0,
        min_pressure=0.0175,
        body_types=frozenset({"Icy body", "Rocky ice body"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fonticulus_04_Name;",
        species_name="Fonticulua Lapida",
        value=3111000,
        atmospheres=frozenset({"Nitrogen"}),
        min_gravity=0.19,
        max_gravity=0.276,
        min_temperature=50.0,
        max_temperature=81.0,
        body_types=frozenset({"Icy body", "Rocky ice body"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fonticulus_05_Name;",
        species_name="Fonticulua Fluctus",
        value=20000000,
        atmospheres=frozenset({"Oxygen"}),
        min_gravity=0.235,
        max_gravity=0.276,
        min_temperature=143.0,
        max_temperature=200.0,
        min_pressure=0.012,
        body_types=frozenset({"Icy body"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fonticulus_06_Name;",
        species_name="Fonticulua Digitos",
        value=1804100,
        atmospheres=frozenset({"Methane"}),
        min_gravity=0.025,
        max_gravity=0.07,
        min_temperature=83.0,
        max_temperature=109.0,
        min_pressure=0.03,
        body_types=frozenset({"Icy body", "Rocky ice body"}),
    ),
)


def evaluate_fonticulua(body: BodyContext) -> list[RuleEvaluation]:
    """Evaluate the six Fonticulua species rules in deterministic order.

    Every species has exactly one ruleset (no OR case here), so this
    mirrors evaluate_aleoida() rather than the aggregate_species_evaluations()
    path used by evaluate_cactoida()/evaluate_concha() -- routing single-
    ruleset genera through the aggregator would be a no-op, not a bug fix.
    """
    return [evaluate_rule(rule, body) for rule in FONTICULUA_RULES]


# Frutexa: the first genus where more than one species has multiple
# alternative rulesets at once (Metallicum has 4, Sponsae and Collum have
# 2 each) -- exercises aggregate_species_evaluations() grouping several
# independent OR-species within a single evaluate_*() call, not just one
# species in isolation (Cactoida Vermis, Concha Renibus).
FRUTEXA_RULES: tuple[NormalizedRule, ...] = (
    NormalizedRule(
        species_code="$Codex_Ent_Shrubs_01_Name;",
        species_name="Frutexa Flabellum",
        value=1808900,
        atmospheres=frozenset({"Ammonia"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=152.0,
        max_temperature=177.0,
        max_pressure=0.0135,
        body_types=frozenset({"Rocky body"}),
        regions=("!scutum-centaurus",),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Shrubs_02_Name;",
        species_name="Frutexa Acus",
        value=7774700,
        atmospheres=frozenset({"CarbonDioxide"}),
        min_gravity=0.04,
        max_gravity=0.237,
        min_temperature=146.0,
        max_temperature=197.0,
        min_pressure=0.0029,
        body_types=frozenset({"Rocky body"}),
        volcanisms=frozenset({"None"}),
        regions=("orion-cygnus",),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Shrubs_03_Name;",
        species_name="Frutexa Metallicum",
        value=1632500,
        atmospheres=frozenset({"Ammonia"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=152.0,
        max_temperature=176.0,
        max_pressure=0.01,
        body_types=frozenset({"High metal content body"}),
        volcanisms=frozenset({"None"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Shrubs_03_Name;",
        species_name="Frutexa Metallicum",
        value=1632500,
        atmospheres=frozenset({"CarbonDioxide"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=146.0,
        max_temperature=197.0,
        min_pressure=0.002,
        body_types=frozenset({"High metal content body"}),
        volcanisms=frozenset({"None"}),
    ),
    # Upstream annotates this ruleset "Only two samples" -- kept as-is
    # (no pressure/volcanism constraint recorded), not strengthened based
    # on our own guesswork.
    NormalizedRule(
        species_code="$Codex_Ent_Shrubs_03_Name;",
        species_name="Frutexa Metallicum",
        value=1632500,
        atmospheres=frozenset({"Methane"}),
        min_gravity=0.05,
        max_gravity=0.1,
        min_temperature=100.0,
        max_temperature=300.0,
        body_types=frozenset({"High metal content body"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Shrubs_03_Name;",
        species_name="Frutexa Metallicum",
        value=1632500,
        atmospheres=frozenset({"Water"}),
        min_gravity=0.04,
        max_gravity=0.07,
        max_temperature=400.0,
        max_pressure=0.07,
        body_types=frozenset({"High metal content body"}),
        volcanisms=frozenset({"None"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Shrubs_04_Name;",
        species_name="Frutexa Flammasis",
        value=10326000,
        atmospheres=frozenset({"Ammonia"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=152.0,
        max_temperature=177.0,
        max_pressure=0.0135,
        body_types=frozenset({"Rocky body"}),
        regions=("scutum-centaurus",),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Shrubs_05_Name;",
        species_name="Frutexa Fera",
        value=1632500,
        atmospheres=frozenset({"CarbonDioxide"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=146.0,
        max_temperature=197.0,
        min_pressure=0.003,
        body_types=frozenset({"Rocky body"}),
        volcanisms=frozenset({"None"}),
        regions=("outer",),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Shrubs_06_Name;",
        species_name="Frutexa Sponsae",
        value=5988000,
        atmospheres=frozenset({"Water"}),
        min_gravity=0.04,
        max_gravity=0.056,
        body_types=frozenset({"Rocky body"}),
        volcanisms=frozenset({"None"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Shrubs_06_Name;",
        species_name="Frutexa Sponsae",
        value=5988000,
        atmospheres=frozenset({"Water"}),
        min_gravity=0.04,
        max_gravity=0.056,
        body_types=frozenset({"Rocky body"}),
        volcanisms=frozenset({"water"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Shrubs_07_Name;",
        species_name="Frutexa Collum",
        value=1639800,
        atmospheres=frozenset({"SulphurDioxide"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=132.0,
        max_temperature=215.0,
        max_pressure=0.004,
        body_types=frozenset({"Rocky body"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Shrubs_07_Name;",
        species_name="Frutexa Collum",
        value=1639800,
        atmospheres=frozenset({"SulphurDioxide"}),
        min_gravity=0.265,
        max_gravity=0.276,
        min_temperature=132.0,
        max_temperature=135.0,
        max_pressure=0.004,
        body_types=frozenset({"High metal content body"}),
        volcanisms=frozenset({"None"}),
    ),
)


def evaluate_frutexa(body: BodyContext) -> list[RuleEvaluation]:
    """Evaluate the seven Frutexa species, OR-collapsing Metallicum's four,
    Sponsae's two, and Collum's two alternative rulesets via
    aggregate_species_evaluations() -- three independent OR-species
    resolved by the same unmodified aggregator in one call.
    """
    per_ruleset = [evaluate_rule(rule, body) for rule in FRUTEXA_RULES]
    return aggregate_species_evaluations(per_ruleset)


# Fumerola: all 4 species have multiple alternative rulesets (7, 5, 6, 9),
# the largest single-species OR case converted so far (Aquatis' 9), and
# the highest ruleset-to-species ratio of any genus so far.
FUMEROLA_RULES: tuple[NormalizedRule, ...] = (
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_01_Name;",
        species_name="Fumerola Carbosis",
        value=6284600,
        atmospheres=frozenset({"Argon"}),
        min_gravity=0.168,
        max_gravity=0.276,
        min_temperature=57.0,
        max_temperature=150.0,
        body_types=frozenset({"Icy body", "Rocky ice body"}),
        volcanisms=frozenset({"carbon", "methane"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_01_Name;",
        species_name="Fumerola Carbosis",
        value=6284600,
        atmospheres=frozenset({"Methane"}),
        min_gravity=0.025,
        max_gravity=0.047,
        min_temperature=84.0,
        max_temperature=110.0,
        min_pressure=0.03,
        body_types=frozenset({"Icy body"}),
        volcanisms=frozenset({"methane magma"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_01_Name;",
        species_name="Fumerola Carbosis",
        value=6284600,
        atmospheres=frozenset({"Neon"}),
        min_gravity=0.26,
        max_gravity=0.276,
        min_temperature=40.0,
        max_temperature=60.0,
        body_types=frozenset({"Icy body"}),
        volcanisms=frozenset({"carbon", "methane"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_01_Name;",
        species_name="Fumerola Carbosis",
        value=6284600,
        atmospheres=frozenset({"Nitrogen"}),
        min_gravity=0.2,
        max_gravity=0.276,
        min_temperature=57.0,
        max_temperature=70.0,
        body_types=frozenset({"Icy body"}),
        volcanisms=frozenset({"carbon", "methane"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_01_Name;",
        species_name="Fumerola Carbosis",
        value=6284600,
        atmospheres=frozenset({"Oxygen"}),
        min_gravity=0.26,
        max_gravity=0.276,
        min_temperature=160.0,
        max_temperature=180.0,
        body_types=frozenset({"Icy body"}),
        volcanisms=frozenset({"carbon"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_01_Name;",
        species_name="Fumerola Carbosis",
        value=6284600,
        atmospheres=frozenset({"SulphurDioxide"}),
        min_gravity=0.185,
        max_gravity=0.276,
        min_temperature=149.0,
        max_temperature=272.0,
        body_types=frozenset({"Icy body", "Rocky ice body"}),
        volcanisms=frozenset({"carbon", "methane"}),
    ),
    # Upstream annotates this ruleset "Probably incomplete" -- kept as-is
    # (no min_gravity/temperature/pressure constraint recorded), not
    # strengthened based on our own guesswork.
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_01_Name;",
        species_name="Fumerola Carbosis",
        value=6284600,
        atmospheres=frozenset({"Ammonia", "ArgonRich", "CarbonDioxideRich"}),
        max_gravity=0.276,
        body_types=frozenset({"Icy body"}),
        volcanisms=frozenset({"carbon"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_02_Name;",
        species_name="Fumerola Extremus",
        value=16202800,
        atmospheres=frozenset({"Ammonia"}),
        min_gravity=0.04,
        max_gravity=0.09,
        min_temperature=161.0,
        max_temperature=177.0,
        max_pressure=0.0135,
        body_types=frozenset({"Rocky body", "Rocky ice body", "High metal content body"}),
        volcanisms=frozenset({"silicate", "metallic", "rocky"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_02_Name;",
        species_name="Fumerola Extremus",
        value=16202800,
        atmospheres=frozenset({"Argon"}),
        min_gravity=0.07,
        max_gravity=0.276,
        min_temperature=50.0,
        max_temperature=121.0,
        body_types=frozenset({"Rocky body", "Rocky ice body", "High metal content body"}),
        volcanisms=frozenset({"silicate", "metallic", "rocky"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_02_Name;",
        species_name="Fumerola Extremus",
        value=16202800,
        atmospheres=frozenset({"Methane"}),
        min_gravity=0.025,
        max_gravity=0.127,
        min_temperature=77.0,
        max_temperature=109.0,
        min_pressure=0.01,
        body_types=frozenset({"Rocky body", "Rocky ice body", "High metal content body"}),
        volcanisms=frozenset({"silicate", "metallic", "rocky"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_02_Name;",
        species_name="Fumerola Extremus",
        value=16202800,
        atmospheres=frozenset({"SulphurDioxide"}),
        min_gravity=0.07,
        max_gravity=0.276,
        min_temperature=54.0,
        max_temperature=210.0,
        body_types=frozenset({"Rocky body", "Rocky ice body"}),
        volcanisms=frozenset({"silicate", "metallic", "rocky"}),
    ),
    # Upstream has this ruleset's max_temperature commented out
    # (#'max_temperature': 210.0,) -- the active dict has no upper bound.
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_02_Name;",
        species_name="Fumerola Extremus",
        value=16202800,
        atmospheres=frozenset({"CarbonDioxide"}),
        min_gravity=0.05,
        max_gravity=0.276,
        min_temperature=500.0,
        body_types=frozenset({"High metal content body"}),
        volcanisms=frozenset({"silicate", "metallic", "rocky"}),
    ),
    # Upstream annotates this ruleset "Only one example".
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_03_Name;",
        species_name="Fumerola Nitris",
        value=7500900,
        atmospheres=frozenset({"Neon"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=30.0,
        max_temperature=129.0,
        body_types=frozenset({"Icy body"}),
        volcanisms=frozenset({"nitrogen", "ammonia"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_03_Name;",
        species_name="Fumerola Nitris",
        value=7500900,
        atmospheres=frozenset({"Argon", "ArgonRich", "NeonRich"}),
        min_gravity=0.044,
        max_gravity=0.276,
        min_temperature=50.0,
        max_temperature=141.0,
        body_types=frozenset({"Icy body"}),
        volcanisms=frozenset({"nitrogen", "ammonia"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_03_Name;",
        species_name="Fumerola Nitris",
        value=7500900,
        atmospheres=frozenset({"Methane"}),
        min_gravity=0.025,
        max_gravity=0.1,
        min_temperature=83.0,
        max_temperature=109.0,
        body_types=frozenset({"Icy body"}),
        volcanisms=frozenset({"nitrogen"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_03_Name;",
        species_name="Fumerola Nitris",
        value=7500900,
        atmospheres=frozenset({"Nitrogen"}),
        min_gravity=0.21,
        max_gravity=0.276,
        min_temperature=60.0,
        max_temperature=81.0,
        body_types=frozenset({"Icy body"}),
        volcanisms=frozenset({"nitrogen", "ammonia"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_03_Name;",
        species_name="Fumerola Nitris",
        value=7500900,
        atmospheres=frozenset({"Oxygen"}),
        max_gravity=0.276,
        min_temperature=150.0,
        body_types=frozenset({"Icy body"}),
        volcanisms=frozenset({"nitrogen", "ammonia"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_03_Name;",
        species_name="Fumerola Nitris",
        value=7500900,
        atmospheres=frozenset({"SulphurDioxide"}),
        min_gravity=0.21,
        max_gravity=0.276,
        min_temperature=160.0,
        max_temperature=250.0,
        body_types=frozenset({"Icy body"}),
        volcanisms=frozenset({"nitrogen", "ammonia"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_04_Name;",
        species_name="Fumerola Aquatis",
        value=6284600,
        atmospheres=frozenset({"Ammonia"}),
        min_gravity=0.028,
        max_gravity=0.276,
        min_temperature=161.0,
        max_temperature=177.0,
        min_pressure=0.002,
        max_pressure=0.02,
        body_types=frozenset({"Icy body", "Rocky ice body", "Rocky body"}),
        volcanisms=frozenset({"water"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_04_Name;",
        species_name="Fumerola Aquatis",
        value=6284600,
        atmospheres=frozenset({"Argon", "ArgonRich"}),
        min_gravity=0.166,
        max_gravity=0.276,
        min_temperature=57.0,
        max_temperature=150.0,
        body_types=frozenset({"Icy body", "Rocky ice body"}),
        volcanisms=frozenset({"water"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_04_Name;",
        species_name="Fumerola Aquatis",
        value=6284600,
        atmospheres=frozenset({"CarbonDioxide"}),
        min_gravity=0.25,
        max_gravity=0.276,
        min_temperature=160.0,
        max_temperature=180.0,
        min_pressure=0.01,
        max_pressure=0.03,
        body_types=frozenset({"Icy body"}),
        volcanisms=frozenset({"water"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_04_Name;",
        species_name="Fumerola Aquatis",
        value=6284600,
        atmospheres=frozenset({"Methane"}),
        min_gravity=0.04,
        max_gravity=0.276,
        min_temperature=80.0,
        max_temperature=100.0,
        min_pressure=0.01,
        body_types=frozenset({"Rocky body"}),
        volcanisms=frozenset({"water"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_04_Name;",
        species_name="Fumerola Aquatis",
        value=6284600,
        atmospheres=frozenset({"Neon"}),
        min_gravity=0.26,
        max_gravity=0.276,
        min_temperature=20.0,
        max_temperature=60.0,
        body_types=frozenset({"Icy body"}),
        volcanisms=frozenset({"water"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_04_Name;",
        species_name="Fumerola Aquatis",
        value=6284600,
        atmospheres=frozenset({"Nitrogen"}),
        min_gravity=0.195,
        max_gravity=0.245,
        min_temperature=56.0,
        max_temperature=80.0,
        body_types=frozenset({"Icy body"}),
        volcanisms=frozenset({"water"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_04_Name;",
        species_name="Fumerola Aquatis",
        value=6284600,
        atmospheres=frozenset({"Oxygen"}),
        min_gravity=0.23,
        max_gravity=0.276,
        min_temperature=153.0,
        max_temperature=190.0,
        min_pressure=0.01,
        body_types=frozenset({"Icy body"}),
        volcanisms=frozenset({"water"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_04_Name;",
        species_name="Fumerola Aquatis",
        value=6284600,
        atmospheres=frozenset({"SulphurDioxide"}),
        min_gravity=0.18,
        max_gravity=0.276,
        min_temperature=150.0,
        max_temperature=270.0,
        body_types=frozenset({"Icy body", "Rocky ice body", "Rocky body"}),
        volcanisms=frozenset({"water"}),
    ),
    NormalizedRule(
        species_code="$Codex_Ent_Fumerolas_04_Name;",
        species_name="Fumerola Aquatis",
        value=6284600,
        atmospheres=frozenset({"Water"}),
        min_gravity=0.04,
        max_gravity=0.06,
        body_types=frozenset({"Rocky body"}),
        volcanisms=frozenset({"water"}),
    ),
)


def evaluate_fumerola(body: BodyContext) -> list[RuleEvaluation]:
    """Evaluate the four Fumerola species, OR-collapsing Carbosis' 7,
    Extremus' 5, Nitris' 6, and Aquatis' 9 alternative rulesets via
    aggregate_species_evaluations() -- every species in this genus is an
    OR case, and Aquatis' 9 is the largest single-species OR converted
    so far.
    """
    per_ruleset = [evaluate_rule(rule, body) for rule in FUMEROLA_RULES]
    return aggregate_species_evaluations(per_ruleset)


_GENUS_EVALUATORS: dict[str, Callable[[BodyContext], list[RuleEvaluation]]] = {
    "aleoida": evaluate_aleoida,
    "cactoida": evaluate_cactoida,
    "concha": evaluate_concha,
    "fonticulua": evaluate_fonticulua,
    "frutexa": evaluate_frutexa,
    "fumerola": evaluate_fumerola,
}


def evaluate_genus(genus: str, body: BodyContext) -> list[RuleEvaluation]:
    """Dispatches to the per-genus evaluator by name (case-insensitive), for callers - such as an
    external CLI boundary - that only have a genus name at hand rather than an imported function
    reference.

    Raises KeyError, not a silent empty list, for a genus not yet converted: the caller asked for a
    verdict this module cannot give, which is a different situation from a body it evaluated and
    found had no candidates.
    """
    try:
        evaluator = _GENUS_EVALUATORS[genus.lower()]
    except KeyError:
        raise KeyError(
            f"no C-CORE evaluator for genus {genus!r} (converted so far: {sorted(_GENUS_EVALUATORS)})"
        ) from None
    return evaluator(body)
