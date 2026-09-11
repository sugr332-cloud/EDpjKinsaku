"""Run one live EDSM body through the Aleoida C-CORE vertical slice."""
from __future__ import annotations

from app.bio.body_context import body_context_from_parameters
from app.bio.c_core import evaluate_aleoida
from app.bio.body_parameters import _row_from_edsm_body, fetch_system_bodies
from app.db.models.edsm import BodyPhysicalParameters
import httpx


def main() -> None:
    with httpx.Client() as client:
        bodies = fetch_system_bodies("Sol", client)

    if not bodies:
        raise SystemExit("EDSM returned no bodies for Sol")

    candidates = [
        body
        for body in bodies
        if body.get("type") == "Planet"
        and body.get("bodyId") is not None
        and body.get("gravity") is not None
        and body.get("surfaceTemperature") is not None
    ]
    if not candidates:
        raise SystemExit("No usable planet record returned by EDSM for Sol")

    body = candidates[0]
    row = _row_from_edsm_body(10477373803, body)
    assert row is not None
    parameters = BodyPhysicalParameters(**row)
    context = body_context_from_parameters(parameters)
    evaluations = evaluate_aleoida(context)

    print("REAL_EDSM_ALEOIDA_PROBE")
    print(f"system=Sol system_address={parameters.system_address}")
    print(f"body_id={parameters.body_id}")
    print(f"body_type={parameters.body_type!r} sub_type={parameters.sub_type!r}")
    print(f"gravity={parameters.gravity!r}")
    print(f"surface_temperature={parameters.surface_temperature!r}")
    print(f"atmosphere_type={parameters.atmosphere_type!r}")
    print(f"volcanism_type={parameters.volcanism_type!r}")
    print(f"surface_pressure={parameters.surface_pressure!r}")
    print(f"body_context={context!r}")
    for result in evaluations:
        print(f"{result.species_name}: {result.status.value} — {result.reason}")


if __name__ == "__main__":
    main()
