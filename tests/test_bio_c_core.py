from app.bio.c_core import (
    ALEOIDA_RULES,
    BodyContext,
    NormalizedRule,
    RuleStatus,
    evaluate_aleoida,
    evaluate_rule,
)


def test_aleoida_arcus_matches_boundary_values_inclusive() -> None:
    body = BodyContext(
        atmosphere="CarbonDioxide",
        gravity=0.04,
        temperature=180.0,
        pressure=0.0161,
        body_type="Rocky body",
        volcanism="None",
    )

    result = evaluate_aleoida(body)[0]

    assert result.status is RuleStatus.MATCH


def test_aleoida_arcus_rejects_temperature_above_range() -> None:
    body = BodyContext(
        atmosphere="CarbonDioxide",
        gravity=0.10,
        temperature=180.1,
        pressure=0.02,
        body_type="Rocky body",
        volcanism="None",
    )

    result = evaluate_aleoida(body)[0]

    assert result.status is RuleStatus.NO_MATCH
    assert "temperature" in result.reason


def test_aleoida_spica_requires_excluded_regions_to_be_absent() -> None:
    body = BodyContext(
        atmosphere="Ammonia",
        gravity=0.10,
        temperature=175.0,
        pressure=0.01,
        body_type="Rocky body",
        volcanism="None",
        regions=frozenset({"orion-cygnus-core"}),
    )

    result = evaluate_aleoida(body)[2]

    assert result.status is RuleStatus.NO_MATCH
    assert "excluded region" in result.reason


def test_aleoida_spica_is_insufficient_without_region_data() -> None:
    body = BodyContext(
        atmosphere="Ammonia",
        gravity=0.10,
        temperature=175.0,
        pressure=0.01,
        body_type="Rocky body",
        volcanism="None",
        regions=None,
    )

    result = evaluate_aleoida(body)[2]

    assert result.status is RuleStatus.INSUFFICIENT_DATA


def test_invalid_rule_is_reported_as_ruleset_inconsistency() -> None:
    rule = NormalizedRule(
        species_code="test",
        species_name="Test",
        value=1,
        min_temperature=200.0,
        max_temperature=100.0,
    )
    body = BodyContext(
        atmosphere=None,
        gravity=None,
        temperature=150.0,
        pressure=None,
        body_type=None,
        volcanism=None,
    )

    result = evaluate_rule(rule, body)

    assert result.status is RuleStatus.RULESET_INCONSISTENCY
    assert "minimum exceeds maximum" in result.reason


def test_aleoida_has_five_rules() -> None:
    assert len(ALEOIDA_RULES) == 5
