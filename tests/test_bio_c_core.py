import pytest

from app.bio.c_core import (
    ALEOIDA_RULES,
    BodyContext,
    CACTOIDA_RULES,
    CONCHA_RULES,
    FONTICULUA_RULES,
    FRUTEXA_RULES,
    FUMEROLA_RULES,
    NormalizedRule,
    RuleEvaluation,
    RuleStatus,
    aggregate_species_evaluations,
    evaluate_aleoida,
    evaluate_cactoida,
    evaluate_concha,
    evaluate_fonticulua,
    evaluate_frutexa,
    evaluate_fumerola,
    evaluate_genus,
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


def test_concha_renibus_matches_via_fourth_of_five_rulesets() -> None:
    """Renibus has 5 alternative rulesets (the largest OR case converted
    so far). This body fails rulesets 1-3 and 5 but satisfies ruleset 4
    (Water atmosphere, volcanism None), so the aggregated verdict must be
    MATCH."""
    body = BodyContext(
        atmosphere="Water",
        gravity=0.3,
        temperature=None,
        pressure=None,
        body_type="Rocky body",
        volcanism="None",
    )

    result = evaluate_concha(body)[0]

    assert result.species_name == "Concha Renibus"
    assert result.status is RuleStatus.MATCH


def test_concha_renibus_is_no_match_when_all_five_rulesets_reject() -> None:
    body = BodyContext(
        atmosphere="Argon",
        gravity=0.3,
        temperature=None,
        pressure=None,
        body_type="Rocky body",
        volcanism="None",
    )

    result = evaluate_concha(body)[0]

    assert result.species_name == "Concha Renibus"
    assert result.status is RuleStatus.NO_MATCH


def test_concha_aureolas_ignores_volcanism_when_ruleset_has_no_constraint() -> None:
    body = BodyContext(
        atmosphere="Ammonia",
        gravity=0.10,
        temperature=160.0,
        pressure=0.01,
        body_type="Rocky body",
        volcanism=None,
    )

    result = evaluate_concha(body)[1]

    assert result.species_name == "Concha Aureolas"
    assert result.status is RuleStatus.MATCH


def test_concha_labiata_matches_boundary_values_inclusive() -> None:
    body = BodyContext(
        atmosphere="CarbonDioxide",
        gravity=0.04,
        temperature=150.0,
        pressure=0.002,
        body_type="Rocky body",
        volcanism="None",
    )

    result = evaluate_concha(body)[2]

    assert result.species_name == "Concha Labiata"
    assert result.status is RuleStatus.MATCH


def test_concha_biconcavis_matches_boundary_values_inclusive() -> None:
    body = BodyContext(
        atmosphere="Nitrogen",
        gravity=0.053,
        temperature=42.0,
        pressure=0.0047,
        body_type="Rocky body",
        volcanism="None",
    )

    result = evaluate_concha(body)[3]

    assert result.species_name == "Concha Biconcavis"
    assert result.status is RuleStatus.MATCH


def test_concha_biconcavis_value_uses_species_value_master_not_bioscan_raw() -> None:
    """BioScan's raw catalog value for Biconcavis is 16777215 (2**24-1, an
    integer-overflow-shaped number); species_value_master.py's
    cross-reference investigation corrected this to 19010800. The
    NormalizedRule must carry the corrected figure, never the raw one."""
    biconcavis_rules = [rule for rule in CONCHA_RULES if rule.species_code == "$Codex_Ent_Conchas_04_Name;"]

    assert len(biconcavis_rules) == 1
    assert biconcavis_rules[0].value == 19010800
    assert all(rule.value != 16777215 for rule in CONCHA_RULES)


def test_concha_values_match_species_value_master() -> None:
    from app.bio.species_value_master import SPECIES_VALUE_MASTER

    seen_codes: set[str] = set()
    for rule in CONCHA_RULES:
        seen_codes.add(rule.species_code)
        master_entry = SPECIES_VALUE_MASTER[rule.species_code]
        assert rule.species_name == master_entry.name
        assert rule.value == master_entry.value
    assert len(seen_codes) == 4


def test_concha_has_eight_rulesets_across_four_species() -> None:
    assert len(CONCHA_RULES) == 8
    body = BodyContext(
        atmosphere=None, gravity=None, temperature=None, pressure=None, body_type=None, volcanism=None,
    )
    assert len(evaluate_concha(body)) == 4


def test_fonticulua_segmentatus_matches_boundary_values_inclusive() -> None:
    body = BodyContext(
        atmosphere="Neon",
        gravity=0.25,
        temperature=50.0,
        pressure=0.006,
        body_type="Icy body",
        volcanism="None",
    )

    result = evaluate_fonticulua(body)[0]

    assert result.species_name == "Fonticulua Segmentatus"
    assert result.status is RuleStatus.MATCH


def test_fonticulua_campestris_ignores_volcanism_when_ruleset_has_no_constraint() -> None:
    """None of Fonticulua's 6 rulesets constrain volcanism at all --
    missing volcanism data must never become INSUFFICIENT_DATA here."""
    body = BodyContext(
        atmosphere="Argon",
        gravity=0.10,
        temperature=100.0,
        pressure=None,
        body_type="Rocky ice body",
        volcanism=None,
    )

    result = evaluate_fonticulua(body)[1]

    assert result.species_name == "Fonticulua Campestris"
    assert result.status is RuleStatus.MATCH


def test_fonticulua_fluctus_and_digitos_transcribed_values() -> None:
    fluctus = evaluate_fonticulua(
        BodyContext(
            atmosphere="Oxygen",
            gravity=0.25,
            temperature=150.0,
            pressure=0.02,
            body_type="Icy body",
            volcanism=None,
        )
    )[4]
    digitos = evaluate_fonticulua(
        BodyContext(
            atmosphere="Methane",
            gravity=0.05,
            temperature=90.0,
            pressure=0.05,
            body_type="Rocky ice body",
            volcanism=None,
        )
    )[5]

    assert fluctus.species_name == "Fonticulua Fluctus"
    assert fluctus.status is RuleStatus.MATCH
    assert digitos.species_name == "Fonticulua Digitos"
    assert digitos.status is RuleStatus.MATCH


def test_fonticulua_values_match_species_value_master() -> None:
    from app.bio.species_value_master import SPECIES_VALUE_MASTER

    seen_codes: set[str] = set()
    for rule in FONTICULUA_RULES:
        seen_codes.add(rule.species_code)
        master_entry = SPECIES_VALUE_MASTER[rule.species_code]
        assert rule.species_name == master_entry.name
        assert rule.value == master_entry.value
        assert master_entry.confidence == "confirmed"
    assert len(seen_codes) == 6


def test_fonticulua_has_six_rulesets_across_six_species() -> None:
    """One ruleset per species (like Aleoida) -- no OR case here."""
    assert len(FONTICULUA_RULES) == 6
    body = BodyContext(
        atmosphere=None, gravity=None, temperature=None, pressure=None, body_type=None, volcanism=None,
    )
    assert len(evaluate_fonticulua(body)) == 6


def test_frutexa_metallicum_matches_via_fourth_of_four_rulesets() -> None:
    """Metallicum has 4 alternative rulesets. This body fails the first
    three (wrong atmosphere) but satisfies the fourth (Water)."""
    body = BodyContext(
        atmosphere="Water",
        gravity=0.05,
        temperature=200.0,
        pressure=0.03,
        body_type="High metal content body",
        volcanism="None",
    )

    result = evaluate_frutexa(body)[2]

    assert result.species_name == "Frutexa Metallicum"
    assert result.status is RuleStatus.MATCH


def test_frutexa_metallicum_is_no_match_when_all_four_rulesets_reject() -> None:
    body = BodyContext(
        atmosphere="Argon",
        gravity=0.06,
        temperature=150.0,
        pressure=0.005,
        body_type="High metal content body",
        volcanism="None",
    )

    result = evaluate_frutexa(body)[2]

    assert result.species_name == "Frutexa Metallicum"
    assert result.status is RuleStatus.NO_MATCH


def test_frutexa_sponsae_matches_via_second_ruleset_when_first_rejects() -> None:
    body = BodyContext(
        atmosphere="Water",
        gravity=0.05,
        temperature=None,
        pressure=None,
        body_type="Rocky body",
        volcanism="water",
    )

    result = evaluate_frutexa(body)[5]

    assert result.species_name == "Frutexa Sponsae"
    assert result.status is RuleStatus.MATCH


def test_frutexa_collum_matches_via_second_ruleset_with_different_body_type() -> None:
    """Collum's first ruleset requires 'Rocky body'; its second requires
    'High metal content body' with a narrower gravity/temperature band.
    This body only satisfies the second."""
    body = BodyContext(
        atmosphere="SulphurDioxide",
        gravity=0.27,
        temperature=133.0,
        pressure=0.003,
        body_type="High metal content body",
        volcanism="None",
    )

    result = evaluate_frutexa(body)[6]

    assert result.species_name == "Frutexa Collum"
    assert result.status is RuleStatus.MATCH


def test_frutexa_flabellum_and_flammasis_region_conditions_are_inverted() -> None:
    """Flabellum and Flammasis share identical atmosphere/gravity/
    temperature/pressure/body_type conditions and differ only in region:
    Flabellum requires scutum-centaurus to be ABSENT, Flammasis requires
    it PRESENT (same pair pattern as Aleoida Spica/Laminiae)."""

    def body_with_regions(regions: frozenset[str]) -> BodyContext:
        return BodyContext(
            atmosphere="Ammonia",
            gravity=0.10,
            temperature=160.0,
            pressure=0.01,
            body_type="Rocky body",
            volcanism=None,
            regions=regions,
        )

    in_scutum = evaluate_frutexa(body_with_regions(frozenset({"scutum-centaurus"})))
    outside_scutum = evaluate_frutexa(body_with_regions(frozenset({"orion-cygnus"})))

    assert in_scutum[0].species_name == "Frutexa Flabellum"
    assert in_scutum[0].status is RuleStatus.NO_MATCH
    assert in_scutum[3].species_name == "Frutexa Flammasis"
    assert in_scutum[3].status is RuleStatus.MATCH

    assert outside_scutum[0].status is RuleStatus.MATCH
    assert outside_scutum[3].status is RuleStatus.NO_MATCH


def test_frutexa_values_match_species_value_master() -> None:
    from app.bio.species_value_master import SPECIES_VALUE_MASTER

    seen_codes: set[str] = set()
    for rule in FRUTEXA_RULES:
        seen_codes.add(rule.species_code)
        master_entry = SPECIES_VALUE_MASTER[rule.species_code]
        assert rule.species_name == master_entry.name
        assert rule.value == master_entry.value
        assert master_entry.confidence == "confirmed"
    assert len(seen_codes) == 7


def test_frutexa_has_twelve_rulesets_across_seven_species() -> None:
    assert len(FRUTEXA_RULES) == 12
    body = BodyContext(
        atmosphere=None, gravity=None, temperature=None, pressure=None, body_type=None, volcanism=None,
    )
    assert len(evaluate_frutexa(body)) == 7


def test_fumerola_carbosis_matches_via_one_of_seven_rulesets() -> None:
    body = BodyContext(
        atmosphere="Argon",
        gravity=0.2,
        temperature=100.0,
        pressure=None,
        body_type="Icy body",
        volcanism="carbon",
    )

    result = evaluate_fumerola(body)[0]

    assert result.species_name == "Fumerola Carbosis"
    assert result.status is RuleStatus.MATCH


def test_fumerola_extremus_matches_via_one_of_five_rulesets() -> None:
    body = BodyContext(
        atmosphere="Ammonia",
        gravity=0.05,
        temperature=170.0,
        pressure=0.01,
        body_type="Rocky body",
        volcanism="silicate",
    )

    result = evaluate_fumerola(body)[1]

    assert result.species_name == "Fumerola Extremus"
    assert result.status is RuleStatus.MATCH


def test_fumerola_nitris_matches_via_one_of_six_rulesets() -> None:
    body = BodyContext(
        atmosphere="Neon",
        gravity=0.1,
        temperature=100.0,
        pressure=None,
        body_type="Icy body",
        volcanism="nitrogen",
    )

    result = evaluate_fumerola(body)[2]

    assert result.species_name == "Fumerola Nitris"
    assert result.status is RuleStatus.MATCH


def test_fumerola_aquatis_matches_via_ninth_of_nine_rulesets() -> None:
    """Aquatis has 9 alternative rulesets, the largest single-species OR
    converted so far. This body fails rulesets 1-8 (wrong atmosphere) but
    satisfies the 9th (Water, no temperature/pressure constraint)."""
    body = BodyContext(
        atmosphere="Water",
        gravity=0.05,
        temperature=None,
        pressure=None,
        body_type="Rocky body",
        volcanism="water",
    )

    result = evaluate_fumerola(body)[3]

    assert result.species_name == "Fumerola Aquatis"
    assert result.status is RuleStatus.MATCH


def test_fumerola_aquatis_is_no_match_when_all_nine_rulesets_reject() -> None:
    body = BodyContext(
        atmosphere="Helium",
        gravity=0.05,
        temperature=None,
        pressure=None,
        body_type="Rocky body",
        volcanism="water",
    )

    result = evaluate_fumerola(body)[3]

    assert result.species_name == "Fumerola Aquatis"
    assert result.status is RuleStatus.NO_MATCH


def test_fumerola_aquatis_is_insufficient_data_when_no_ruleset_matches_and_some_lack_data() -> None:
    """No ruleset can MATCH (atmosphere is missing entirely), but three of
    the nine rulesets (1, 4, 8) have no other disqualifying field at this
    gravity, leaving only missing-data checks -- so the aggregated verdict
    must be INSUFFICIENT_DATA, not NO_MATCH, even though the other six
    rulesets are outright rejected by body_type or gravity."""
    body = BodyContext(
        atmosphere=None,
        gravity=0.276,
        temperature=None,
        pressure=None,
        body_type="Rocky body",
        volcanism=None,
    )

    result = evaluate_fumerola(body)[3]

    assert result.species_name == "Fumerola Aquatis"
    assert result.status is RuleStatus.INSUFFICIENT_DATA


def test_fumerola_values_match_species_value_master() -> None:
    from app.bio.species_value_master import SPECIES_VALUE_MASTER

    seen_codes: set[str] = set()
    for rule in FUMEROLA_RULES:
        seen_codes.add(rule.species_code)
        master_entry = SPECIES_VALUE_MASTER[rule.species_code]
        assert rule.species_name == master_entry.name
        assert rule.value == master_entry.value
        assert master_entry.confidence == "confirmed"
    assert len(seen_codes) == 4


def test_fumerola_has_twenty_seven_rulesets_across_four_species() -> None:
    """Every Fumerola species is an OR case (no single-ruleset species)."""
    assert len(FUMEROLA_RULES) == 27
    body = BodyContext(
        atmosphere=None, gravity=None, temperature=None, pressure=None, body_type=None, volcanism=None,
    )
    assert len(evaluate_fumerola(body)) == 4


def test_evaluate_genus_dispatches_by_name() -> None:
    body = BodyContext(
        atmosphere="CarbonDioxide",
        gravity=0.04,
        temperature=180.0,
        pressure=0.0161,
        body_type="Rocky body",
        volcanism="None",
    )
    assert evaluate_genus("Aleoida", body) == evaluate_aleoida(body)


def test_evaluate_genus_is_case_insensitive() -> None:
    body = BodyContext(
        atmosphere=None, gravity=None, temperature=None, pressure=None, body_type=None, volcanism=None,
    )
    assert evaluate_genus("FUMEROLA", body) == evaluate_genus("fumerola", body) == evaluate_fumerola(body)


def test_evaluate_genus_raises_key_error_for_an_unconverted_genus() -> None:
    """13 of 19 genera have no evaluator yet; asking for one must not silently return no candidates."""
    body = BodyContext(
        atmosphere=None, gravity=None, temperature=None, pressure=None, body_type=None, volcanism=None,
    )
    with pytest.raises(KeyError, match="(?i)tussock"):
        evaluate_genus("Tussock", body)
