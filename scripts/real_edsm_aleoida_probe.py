"""Run one known Aleoida body through the C-CORE vertical slice."""
from __future__ import annotations

from app.bio.body_context import body_context_from_parameters
from app.bio.c_core import evaluate_aleoida
from app.bio.body_parameters import _row_from_edsm_body, fetch_system_bodies
from app.db.models.edsm import BodyPhysicalParameters
import httpx

SYSTEM_NAME = "Hypio Flyao WD-H b15-24"
TARGET_BODY_NAME = "A 2 A"
SYSTEM_ADDRESS = None


def main() -> None:
    with httpx.Client() as client:
        bodies = fetch_system_bodies(SYSTEM_NAME, client)

    if not bodies:
        raise SystemExit(f"EDSM returned no bodies for {SYSTEM_NAME}")

    candidates = [
        body
        for body in bodies
        if body.get("name") == TARGET_BODY_NAME
        and body.get("bodyId") is not None
    ]
    if not candidates:
        available = [body.get("name") for body in bodies]
        raise SystemExit(f"Target body {TARGET_BODY_NAME!r} not found; available={available!r}")

    body = candidates[0]
    system_address = body.get("systemAddress")
    if system_address is None:
        raise SystemExit("EDSM target body has no systemAddress")

    row = _row_from_edsm_body(system_address, body)
    assert row is not None
    parameters = BodyPhysicalParameters(**row)
    context = body_context_from_parameters(parameters)
    evaluations = evaluate_aleoida(context)

    print("REAL_EDSM_ALEOIDA_PROBE")
    print(f"system={SYSTEM_NAME!r}")
    print(f"target_body={TARGET_BODY_NAME!r}")
    print(f"body_id={parameters.body_id!r}")
    print(f"EDSM raw type={parameters.body_type!r}")
    print(f"EDSM raw subType={parameters.sub_type!r}")
    print(f"EDSM raw atmosphereType={parameters.atmosphere_type!r}")
    print(f"EDSM raw gravity={parameters.gravity!r}")
    print(f"EDSM raw surfaceTemperature={parameters.surface_temperature!r}")
    print(f"EDSM raw surfacePressure={parameters.surface_pressure!r}")
    print(f"EDSM raw volcanismType={parameters.volcanism_type!r}")
    print(f"C-CORE body_type={context.body_type!r}")
    print(f"C-CORE atmosphere={context.atmosphere!r}")
    print(f"C-CORE gravity={context.gravity!r}")
    print(f"C-CORE temperature={context.temperature!r}")
    print(f"C-CORE pressure={context.pressure!r}")
    print(f"C-CORE volcanism={context.volcanism!r}")
    print("C-CORE expected body_types=['High metal content body', 'Rocky body']")
    for result in evaluations:
        print(f"{result.species_name}: {result.status.value} — {result.reason}")


if __name__ == "__main__":
    main()
