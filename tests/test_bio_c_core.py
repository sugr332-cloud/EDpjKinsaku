from app.bio.c_core import (
    ALEOIDA_RULES,
    BodyContext,
    CACTOIDA_RULES,
    NormalizedRule,
    RuleEvaluation,
    RuleStatus,
    aggregate_species_evaluations,
    evaluate_aleoida,
    evaluate_cactoida,
    evaluate_genus_consistency,
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


def test_invalid_rule_is_reported_as_rule_definition_error() -> None:
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

    assert result.status is RuleStatus.RULE_DEFINITION_ERROR
    assert "minimum exceeds maximum" in result.reason


def test_genus_inconsistency_requires_established_genus_and_all_rejected() -> None:
    evaluations = [
        evaluate_rule(
            NormalizedRule(
                species_code=f"test-{index}",
                species_name=f"Test {index}",
                value=1,
                atmospheres=frozenset({"CarbonDioxide"}),
            ),
            BodyContext(
                atmosphere="Ammonia",
                gravity=None,
                temperature=None,
                pressure=None,
                body_type=None,
                volcanism=None,
            ),
        )
        for index in range(2)
    ]

    assert evaluate_genus_consistency(True, evaluations) is RuleStatus.RULESET_INCONSISTENCY
    assert evaluate_genus_consistency(False, evaluations) is None


def test_genus_inconsistency_does_not_mask_insufficient_data() -> None:
    evaluations = [
        RuleEvaluation(
            species_code="test",
            species_name="Test",
            status=RuleStatus.INSUFFICIENT_DATA,
            reason="missing",
        )
    ]

    assert evaluate_genus_consistency(True, evaluations) is None


def test_aleoida_has_five_rules() -> None:
    assert len(ALEOIDA_RULES) == 5


def test_cactoida_cortexum_matches_boundary_values_inclusive() -> None:
    body = BodyContext(
        atmosphere="CarbonDioxide",
        gravity=0.04,
        temperature=180.0,
        pressure=0.025,
        body_type="Rocky body",
        volcanism="None",
        regions=frozenset({"orion-cygnus"}),
    )

    result = evaluate_cactoida(body)[0]

    assert result.species_name == "Cactoida Cortexum"
    assert result.status is RuleStatus.MATCH


def test_cactoida_lapis_ignores_volcanism_when_ruleset_has_no_constraint() -> None:
    """Lapis' upstream ruleset has no 'volcanism' key at all -- unlike
    Aleoida Spica's region check, missing body data for an unconstrained
    field must never become INSUFFICIENT_DATA."""
    body = BodyContext(
        atmosphere="Ammonia",
        gravity=0.10,
        temperature=170.0,
        pressure=0.01,
        body_type="Rocky body",
        volcanism=None,
        regions=frozenset({"sagittarius-carina"}),
    )

    result = evaluate_cactoida(body)[1]

    assert result.species_name == "Cactoida Lapis"
    assert result.status is RuleStatus.MATCH


def test_cactoida_vermis_matches_via_second_ruleset_when_first_rejects() -> None:
    """Vermis has 3 alternative rulesets (OR semantics). This body fails
    ruleset 1 (wrong atmosphere/gravity) but satisfies ruleset 2, so the
    aggregated verdict must be MATCH, not NO_MATCH."""
    body = BodyContext(
        atmosphere="Water",
        gravity=0.10,
        temperature=None,
        pressure=None,
        body_type="Rocky body",
        volcanism="None",
    )

    result = evaluate_cactoida(body)[2]

    assert result.species_name == "Cactoida Vermis"
    assert result.status is RuleStatus.MATCH


def test_cactoida_vermis_is_no_match_when_all_three_rulesets_reject() -> None:
    body = BodyContext(
        atmosphere="Ammonia",
        gravity=0.10,
        temperature=None,
        pressure=None,
        body_type="Rocky body",
        volcanism="None",
    )

    result = evaluate_cactoida(body)[2]

    assert result.species_name == "Cactoida Vermis"
    assert result.status is RuleStatus.NO_MATCH


def test_cactoida_pullulanta_and_peperatis_transcribed_regions() -> None:
    pullulanta = evaluate_cactoida(
        BodyContext(
            atmosphere="CarbonDioxide",
            gravity=0.10,
            temperature=190.0,
            pressure=0.03,
            body_type="Rocky body",
            volcanism="None",
            regions=frozenset({"perseus"}),
        )
    )[3]
    peperatis = evaluate_cactoida(
        BodyContext(
            atmosphere="Ammonia",
            gravity=0.10,
            temperature=170.0,
            pressure=0.01,
            body_type="Rocky body",
            volcanism=None,
            regions=frozenset({"scutum-centaurus"}),
        )
    )[4]

    assert pullulanta.species_name == "Cactoida Pullulanta"
    assert pullulanta.status is RuleStatus.MATCH
    assert peperatis.species_name == "Cactoida Peperatis"
    assert peperatis.status is RuleStatus.MATCH


def test_cactoida_has_seven_rulesets_across_five_species() -> None:
    assert len(CACTOIDA_RULES) == 7
    body = BodyContext(
        atmosphere=None, gravity=None, temperature=None, pressure=None, body_type=None, volcanism=None,
    )
    assert len(evaluate_cactoida(body)) == 5


def test_aggregate_species_evaluations_prefers_match_over_any_other_status() -> None:
    evaluations = [
        RuleEvaluation(species_code="s", species_name="S", status=RuleStatus.NO_MATCH, reason="a"),
        RuleEvaluation(species_code="s", species_name="S", status=RuleStatus.MATCH, reason="b"),
        RuleEvaluation(species_code="s", species_name="S", status=RuleStatus.INSUFFICIENT_DATA, reason="c"),
    ]

    aggregated = aggregate_species_evaluations(evaluations)

    assert len(aggregated) == 1
    assert aggregated[0].status is RuleStatus.MATCH
    assert aggregated[0].reason == "b"


def test_aggregate_species_evaluations_prefers_insufficient_data_over_rule_definition_error() -> None:
    evaluations = [
        RuleEvaluation(species_code="s", species_name="S", status=RuleStatus.RULE_DEFINITION_ERROR, reason="a"),
        RuleEvaluation(species_code="s", species_name="S", status=RuleStatus.INSUFFICIENT_DATA, reason="b"),
        RuleEvaluation(species_code="s", species_name="S", status=RuleStatus.NO_MATCH, reason="c"),
    ]

    aggregated = aggregate_species_evaluations(evaluations)

    assert aggregated[0].status is RuleStatus.INSUFFICIENT_DATA


def test_aggregate_species_evaluations_falls_back_to_no_match_only_when_all_reject() -> None:
    evaluations = [
        RuleEvaluation(species_code="s", species_name="S", status=RuleStatus.NO_MATCH, reason="a"),
        RuleEvaluation(species_code="s", species_name="S", status=RuleStatus.NO_MATCH, reason="b"),
    ]

    aggregated = aggregate_species_evaluations(evaluations)

    assert aggregated[0].status is RuleStatus.NO_MATCH


def test_aggregate_species_evaluations_preserves_first_seen_species_order() -> None:
    evaluations = [
        RuleEvaluation(species_code="b", species_name="B", status=RuleStatus.NO_MATCH, reason=""),
        RuleEvaluation(species_code="a", species_name="A", status=RuleStatus.NO_MATCH, reason=""),
        RuleEvaluation(species_code="b", species_name="B", status=RuleStatus.MATCH, reason=""),
    ]

    aggregated = aggregate_species_evaluations(evaluations)

    assert [result.species_code for result in aggregated] == ["b", "a"]
