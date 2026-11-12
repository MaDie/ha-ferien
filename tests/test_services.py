"""Actions, inklusive Persistenz über einen Neustart des Eintrags."""

from __future__ import annotations

import pytest
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.ferien.const import DOMAIN
from tests.hilfe import mock_termine, richte_ein


async def test_eigener_tag_bleibt_nach_neustart(hass, aioclient_mock) -> None:
    """Hinzufügen und Entfernen liegen im Store, nicht im Integrationsordner."""
    eintrag = await richte_ein(hass, aioclient_mock)
    await hass.services.async_call(
        DOMAIN,
        "tag_hinzufuegen",
        {
            "config_entry_id": eintrag.entry_id,
            "start": "2026-11-12",
            "ende": "2026-11-13",
            "name": "Wandertag",
        },
        blocking=True,
    )
    await hass.async_block_till_done()
    pruefung = await hass.services.async_call(
        DOMAIN,
        "schultag_pruefen",
        {"config_entry_id": eintrag.entry_id, "datum": "2026-11-12"},
        blocking=True,
        return_response=True,
    )
    assert pruefung["schulfrei"] is True
    assert pruefung["grund"] == "eigener_tag"
    assert pruefung["name"] == "Wandertag"

    await hass.config_entries.async_unload(eintrag.entry_id)
    await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    erneut = await hass.services.async_call(
        DOMAIN,
        "schultag_pruefen",
        {"config_entry_id": eintrag.entry_id, "datum": "2026-11-13"},
        blocking=True,
        return_response=True,
    )
    assert erneut["schulfrei"] is True

    await hass.services.async_call(
        DOMAIN,
        "tag_entfernen",
        {"config_entry_id": eintrag.entry_id, "start": "2026-11-12"},
        blocking=True,
    )
    danach = await hass.services.async_call(
        DOMAIN,
        "schultag_pruefen",
        {"config_entry_id": eintrag.entry_id, "datum": "2026-11-12"},
        blocking=True,
        return_response=True,
    )
    assert danach["schulfrei"] is False
    assert danach["grund"] is None


async def test_termine_und_grenzen(hass, aioclient_mock) -> None:
    """Herbstferien in der Liste. Außerhalb der Abdeckung kein Ersatz."""
    eintrag = await richte_ein(hass, aioclient_mock)
    antwort = await hass.services.async_call(
        DOMAIN,
        "termine_abrufen",
        {
            "config_entry_id": eintrag.entry_id,
            "von": "2026-11-01",
            "bis": "2026-11-18",
            "typen": ["herbstferien", "schulfrei"],
        },
        blocking=True,
        return_response=True,
    )
    namen = {eintrag["name"] for eintrag in antwort["termine"]}
    assert namen == {"Herbstferien", "Buß- und Bettag"}

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "termine_abrufen",
            {
                "config_entry_id": eintrag.entry_id,
                "von": "2026-01-01",
                "bis": "2026-01-02",
            },
            blocking=True,
            return_response=True,
        )
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "schultag_pruefen",
            {"config_entry_id": eintrag.entry_id, "datum": "2026-07-01"},
            blocking=True,
            return_response=True,
        )


async def test_ungueltige_actions(hass, aioclient_mock) -> None:
    """Name, Zeitraum und unbekannter Tag werden abgelehnt."""
    eintrag = await richte_ein(hass, aioclient_mock)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "tag_hinzufuegen",
            {
                "config_entry_id": eintrag.entry_id,
                "start": "2026-11-12",
                "ende": "2026-11-01",
                "name": "Falsch",
            },
            blocking=True,
        )
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "tag_entfernen",
            {"config_entry_id": eintrag.entry_id, "start": "2026-01-01"},
            blocking=True,
        )
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "tag_hinzufuegen",
            {"config_entry_id": "fehlt", "start": "2026-11-12", "name": "Nein"},
            blocking=True,
        )


async def test_aktualisieren_meldet_den_fehler(hass, aioclient_mock) -> None:
    """Die Action wirft, die Entität wird unavailable und nicht aus."""
    eintrag = await richte_ein(hass, aioclient_mock)
    aioclient_mock.clear_requests()
    mock_termine(aioclient_mock, exc=TimeoutError())
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN,
            "aktualisieren",
            {"config_entry_id": eintrag.entry_id},
            blocking=True,
        )
    assert hass.states.get("sensor.ferien_by_tage_bis_ferien").state == "unavailable"
