import json

from typer.testing import CliRunner

from app.cli.__main__ import app

runner = CliRunner()


def _invoke(request: dict) -> "object":
    # Through the full `edpj` app, not bio_app standalone: a single-command Typer sub-app collapses
    # away its command name when run on its own, so testing bio_app directly would pass "evaluate" as
    # an unexpected extra argument instead of exercising the real `edpj bio evaluate` invocation.
    return runner.invoke(app, ["bio", "evaluate"], input=json.dumps(request))


def test_evaluate_reads_stdin_json_and_writes_aggregated_verdicts() -> None:
    request = {
        "genus": "Aleoida",
        "body": {
            "atmosphere": "CarbonDioxide",
            "gravity": 0.04,
            "temperature": 180.0,
            "pressure": 0.0161,
            "body_type": "Rocky body",
            "volcanism": "None",
        },
    }

    result = _invoke(request)

    assert result.exit_code == 0, result.output
    evaluations = json.loads(result.output)
    assert isinstance(evaluations, list)
    assert all({"species_code", "species_name", "status", "reason"} <= e.keys() for e in evaluations)
    assert any(e["status"] == "MATCH" for e in evaluations)


def test_evaluate_treats_a_null_body_field_as_missing_data() -> None:
    request = {
        "genus": "Fumerola",
        "body": {
            "atmosphere": None,
            "gravity": None,
            "temperature": None,
            "pressure": None,
            "body_type": None,
            "volcanism": None,
        },
    }

    result = _invoke(request)

    assert result.exit_code == 0, result.output
    evaluations = json.loads(result.output)
    assert len(evaluations) == 4  # one entry per Fumerola species, aggregated
    assert all(e["status"] == "INSUFFICIENT_DATA" for e in evaluations)


def test_evaluate_fails_cleanly_for_an_unconverted_genus() -> None:
    result = _invoke({"genus": "Tussock", "body": {}})

    assert result.exit_code == 1
    error = json.loads(result.output)
    assert "tussock" in error["error"].lower()


def test_evaluate_fails_cleanly_for_malformed_json() -> None:
    result = runner.invoke(app, ["bio", "evaluate"], input="not json")

    assert result.exit_code == 1
    error = json.loads(result.output)
    assert "error" in error


def test_evaluate_fails_cleanly_when_genus_or_body_is_missing() -> None:
    result = _invoke({"genus": "Aleoida"})

    assert result.exit_code == 1
    error = json.loads(result.output)
    assert "error" in error
