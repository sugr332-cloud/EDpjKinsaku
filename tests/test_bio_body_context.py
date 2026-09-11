from app.bio.body_context import body_context_from_parameters
from app.db.models.edsm import BodyPhysicalParameters


def test_body_context_maps_edsm_fields_without_guessing():
    parameters = BodyPhysicalParameters(
        system_address=1,
        body_id=2,
        body_type="Planet",
        sub_type="High metal content body",
        gravity=0.25,
        surface_temperature=180.0,
        atmosphere_type="Carbon dioxide",
        volcanism_type=None,
        surface_pressure=0.02,
    )

    context = body_context_from_parameters(parameters)

    assert context.atmosphere == "CarbonDioxide"
    assert context.gravity == 0.25
    assert context.temperature == 180.0
    assert context.pressure == 0.02
    assert context.body_type == "High metal content body"
    assert context.volcanism is None
    assert context.regions is None
