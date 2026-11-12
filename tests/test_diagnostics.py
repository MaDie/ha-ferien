"""Diagnose ohne den Terminbestand."""

from __future__ import annotations

try:
    from pytest_homeassistant.components.diagnostics import (
        get_diagnostics_for_config_entry,
    )
except ImportError:  # pragma: no cover - CI-Matrix 2026.10
    from pytest_homeassistant_custom_component.components.diagnostics import (
        get_diagnostics_for_config_entry,
    )

from tests.hilfe import richte_ein


async def test_diagnostics_snapshot(
    hass, hass_client, aioclient_mock, snapshot
) -> None:
    """Stabiler Ausschnitt: kein Payload, feste Abrufminute."""
    eintrag = await richte_ein(hass, aioclient_mock)
    daten = await get_diagnostics_for_config_entry(hass, hass_client, eintrag)
    assert "termine" not in daten
    assert daten["land"] == "BY"
    assert daten["abruf"] == {"stunde": 3, "minute": 17}
    assert daten["anzahl"]["ferien"] > 0
    assert daten == snapshot
