"""Adapt cached EDSM body parameters into the C-CORE BodyContext."""
from __future__ import annotations

from app.bio.c_core import BodyContext
from app.db.models.edsm import BodyPhysicalParameters


_ATMOSPHERE_ALIASES = {
    "Carbon dioxide": "CarbonDioxide",
    "CarbonDioxide": "CarbonDioxide",
    "Ammonia": "Ammonia",
}


def _normalize_optional(value: str | None) -> str | None:
    if value is None or value == "":
        return None
    return value


def _normalize_atmosphere(value: str | None) -> str | None:
    value = _normalize_optional(value)
    if value is None:
        return None
    return _ATMOSPHERE_ALIASES.get(value, value)


def body_context_from_parameters(parameters: BodyPhysicalParameters) -> BodyContext:
    """Map cached EDSM physical metadata to the C-CORE input contract.

    EDSM ``sub_type`` is used for C-CORE ``body_type`` because C-CORE rules
    distinguish planet classes such as ``Rocky body`` and ``High metal
    content body`` rather than the generic EDSM ``Planet`` type.

    Region information is not present in BodyPhysicalParameters, so it stays
    ``None`` rather than being guessed or replaced with an empty set.
    """
    return BodyContext(
        atmosphere=_normalize_atmosphere(parameters.atmosphere_type),
        gravity=parameters.gravity,
        temperature=parameters.surface_temperature,
        pressure=parameters.surface_pressure,
        body_type=_normalize_optional(parameters.sub_type),
        volcanism=_normalize_optional(parameters.volcanism_type),
        regions=None,
    )
