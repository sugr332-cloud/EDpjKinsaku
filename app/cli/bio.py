"""`edpj bio evaluate` — C-CORE species evaluation over stdin/stdout JSON.

This is the boundary CLI for a caller that cannot import this project's Python
directly (see docs/ELITEINTEL_INTEGRATION_PLAN.md in the EliteIntel fork, Phase 4
decision 1: subprocess + stdio JSON). It wraps app.bio.c_core.evaluate_genus()
and does not duplicate any evaluation logic.
"""
from __future__ import annotations

import json
import sys
from typing import NoReturn

import typer

from app.bio.c_core import BodyContext, RuleEvaluation, evaluate_genus

bio_app = typer.Typer(help="C-CORE species evaluation commands")


@bio_app.command("evaluate")
def evaluate(
    input_file: typer.FileText = typer.Option(
        None, "--input", help="Read the request JSON from this file instead of stdin."
    ),
) -> None:
    """Reads one request object and writes the aggregated per-species verdicts as JSON.

    Request shape: {"genus": "Aleoida", "body": {"atmosphere": str|null,
    "gravity": float|null, "temperature": float|null, "pressure": float|null,
    "body_type": str|null, "volcanism": str|null, "regions": [str, ...]|null}}.

    Response: a JSON array of {"species_code", "species_name", "status", "reason"},
    one entry per species C-CORE has a rule for in that genus, already aggregated
    across that species' rulesets (see aggregate_species_evaluations()).
    """
    raw = (input_file or sys.stdin).read()
    try:
        request = json.loads(raw)
    except json.JSONDecodeError as error:
        _fail(f"invalid JSON on input: {error}")

    try:
        genus = request["genus"]
        body_fields = request["body"]
    except (KeyError, TypeError):
        _fail('request must be a JSON object with "genus" and "body" keys')

    body = _body_context_from_json(body_fields)

    try:
        evaluations = evaluate_genus(genus, body)
    except KeyError as error:
        _fail(str(error))

    typer.echo(json.dumps([_evaluation_to_json(e) for e in evaluations]))


def _body_context_from_json(fields: dict) -> BodyContext:
    regions = fields.get("regions")
    return BodyContext(
        atmosphere=fields.get("atmosphere"),
        gravity=fields.get("gravity"),
        temperature=fields.get("temperature"),
        pressure=fields.get("pressure"),
        body_type=fields.get("body_type"),
        volcanism=fields.get("volcanism"),
        regions=frozenset(regions) if regions else None,
    )


def _evaluation_to_json(evaluation: RuleEvaluation) -> dict:
    return {
        "species_code": evaluation.species_code,
        "species_name": evaluation.species_name,
        "status": evaluation.status.value,
        "reason": evaluation.reason,
    }


def _fail(message: str) -> NoReturn:
    typer.echo(json.dumps({"error": message}), err=True)
    raise typer.Exit(code=1)
