"""Config Flow, Reconfigure und Optionen."""

from __future__ import annotations

from datetime import date

from homeassistant.config_entries import SOURCE_RECONFIGURE, SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ferien.const import (
    CONF_FEIERTAGE_IM_KALENDER,
    CONF_LAND,
    CONF_REGIONALE_FEIERTAGE,
    DOMAIN,
)
from tests.hilfe import (
    ENTRY_ID,
    feste_abrufzeit,
    lade_fixture,
    mock_region,
    mock_termine,
    richte_ein,
    termine_url,
)

try:
    from pytest_homeassistant.common import MockConfigEntry
except ImportError:  # pragma: no cover - CI-Matrix 2026.10
    from pytest_homeassistant_custom_component.common import MockConfigEntry


def _vorgabe(schema, schluessel: str):
    for marker in schema.schema:
        if getattr(marker, "schema", None) == schluessel:
            standard = marker.default
            if callable(standard):
                return standard()
    return None


async def test_flow_belegt_das_bundesland_vor(hass, aioclient_mock) -> None:
    """`/api/region` setzt die Vorbelegung. Der Eintrag heißt Ferien Bayern."""
    await hass.config.async_set_time_zone("Europe/Berlin")
    mock_region(aioclient_mock, "DE-BY")
    mock_termine(aioclient_mock)
    with feste_abrufzeit():
        ergebnis = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        assert ergebnis["type"] is FlowResultType.FORM
        assert _vorgabe(ergebnis["data_schema"], CONF_LAND) == "BY"
        erzeugt = await hass.config_entries.flow.async_configure(
            ergebnis["flow_id"], {CONF_LAND: "BY"}
        )
        await hass.async_block_till_done()
    assert erzeugt["type"] is FlowResultType.CREATE_ENTRY
    assert erzeugt["title"] == "Ferien Bayern"
    assert erzeugt["result"].unique_id == "BY"
    assert hass.states.get("binary_sensor.ferien_by_schulfrei_heute") is not None
    termine = [
        kopf
        for kopf in aioclient_mock.mock_calls
        if str(kopf[0]).lower() == "get" and "termine" in str(kopf[1])
    ]
    assert termine
    assert termine[-1][3]["User-Agent"].startswith("ha-ferien/")


async def test_region_fehler_ist_kein_fehler(hass, aioclient_mock) -> None:
    """Fällt die Vorbelegung aus, bleibt das Formular leer und ohne Fehler."""
    mock_region(aioclient_mock, exc=TimeoutError())
    ergebnis = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert ergebnis["type"] is FlowResultType.FORM
    assert not ergebnis["errors"]
    assert _vorgabe(ergebnis["data_schema"], CONF_LAND) in (None, {})


async def test_doppeltes_land_wird_abgebrochen(hass, aioclient_mock) -> None:
    """Ein Land nur einmal."""
    mock_region(aioclient_mock, None)
    MockConfigEntry(
        domain=DOMAIN,
        data={CONF_LAND: "BY"},
        unique_id="BY",
        entry_id=ENTRY_ID,
        title="Ferien Bayern",
    ).add_to_hass(hass)
    ergebnis = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    abbruch = await hass.config_entries.flow.async_configure(
        ergebnis["flow_id"], {CONF_LAND: "BY"}
    )
    assert abbruch["type"] is FlowResultType.ABORT
    assert abbruch["reason"] == "already_configured"


async def test_setup_ohne_api_wartet(hass, aioclient_mock) -> None:
    """Ohne Cache und ohne Netz bleibt der Eintrag im Retry."""
    from homeassistant.config_entries import ConfigEntryState

    eintrag = await richte_ein(hass, aioclient_mock, exc=TimeoutError())
    assert eintrag.state is ConfigEntryState.SETUP_RETRY
    assert hass.states.get("binary_sensor.ferien_by_schulfrei_heute") is None


async def test_reconfigure_behaelt_die_entity_id(hass, aioclient_mock) -> None:
    """Das Land wechselt, die entity_id behält das alte Kürzel."""
    eintrag = await richte_ein(hass, aioclient_mock)
    assert hass.states.get("binary_sensor.ferien_by_schulfrei_heute").state == "off"
    berlin = lade_fixture()
    berlin["land"] = {
        "code": "BE",
        "iso": "DE-BE",
        "slug": "berlin",
        "name": "Berlin",
    }
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        termine_url("BE"),
        json=berlin,
        headers={"ETag": "be-1"},
    )
    with feste_abrufzeit():
        formular = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_RECONFIGURE, "entry_id": eintrag.entry_id},
        )
        assert "by" in formular["description_placeholders"]["kuerzel"]
        ergebnis = await hass.config_entries.flow.async_configure(
            formular["flow_id"], {CONF_LAND: "BE"}
        )
        await hass.async_block_till_done()
    assert ergebnis["type"] is FlowResultType.ABORT
    assert ergebnis["reason"] == "reconfigure_successful"
    assert eintrag.unique_id == "BE"
    assert eintrag.data[CONF_LAND] == "BE"
    assert hass.states.get("binary_sensor.ferien_by_schulfrei_heute") is not None
    assert hass.states.get("binary_sensor.ferien_be_schulfrei_heute") is None


async def test_reconfigure_auf_belegtes_land(hass, aioclient_mock) -> None:
    """Ein zweiter Eintrag für dasselbe Land wird abgelehnt."""
    erster = await richte_ein(hass, aioclient_mock)
    MockConfigEntry(
        domain=DOMAIN,
        data={CONF_LAND: "BE"},
        unique_id="BE",
        entry_id="ferien-be-test",
        title="Ferien Berlin",
    ).add_to_hass(hass)
    formular = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": erster.entry_id},
    )
    abbruch = await hass.config_entries.flow.async_configure(
        formular["flow_id"], {CONF_LAND: "BE"}
    )
    assert abbruch["reason"] == "already_configured"
    assert erster.data[CONF_LAND] == "BY"


async def test_optionen_und_eigener_tag(hass, aioclient_mock) -> None:
    """Schalter und ein eigener Tag über den Options-Flow."""
    eintrag = await richte_ein(hass, aioclient_mock)
    menu = await hass.config_entries.options.async_init(eintrag.entry_id)
    assert menu["type"] is FlowResultType.MENU
    schalter = await hass.config_entries.options.async_configure(
        menu["flow_id"], {"next_step_id": "einstellungen"}
    )
    gespeichert = await hass.config_entries.options.async_configure(
        schalter["flow_id"],
        {
            CONF_FEIERTAGE_IM_KALENDER: False,
            CONF_REGIONALE_FEIERTAGE: True,
        },
    )
    await hass.async_block_till_done()
    assert gespeichert["type"] is FlowResultType.CREATE_ENTRY
    assert eintrag.options[CONF_REGIONALE_FEIERTAGE] is True

    menu = await hass.config_entries.options.async_init(eintrag.entry_id)
    form = await hass.config_entries.options.async_configure(
        menu["flow_id"], {"next_step_id": "tag_hinzufuegen"}
    )
    abbruch = await hass.config_entries.options.async_configure(
        form["flow_id"],
        {"start": date(2026, 11, 11), "name": "Wandertag"},
    )
    await hass.async_block_till_done()
    assert abbruch["reason"] == "tag_gespeichert"
    zustand = hass.states.get("binary_sensor.ferien_by_schulfrei_heute")
    assert zustand.state == "on"
    assert zustand.attributes["grund"] == "eigener_tag"

    menu = await hass.config_entries.options.async_init(eintrag.entry_id)
    form = await hass.config_entries.options.async_configure(
        menu["flow_id"], {"next_step_id": "tag_entfernen"}
    )
    weg = await hass.config_entries.options.async_configure(
        form["flow_id"], {"start": "2026-11-11"}
    )
    await hass.async_block_till_done()
    assert weg["reason"] == "tag_gespeichert"
    assert hass.states.get("binary_sensor.ferien_by_schulfrei_heute").state == "off"


async def test_entfernen_ohne_eigene_tage(hass, aioclient_mock) -> None:
    """Leere Liste bricht den Schritt ab."""
    eintrag = await richte_ein(hass, aioclient_mock)
    menu = await hass.config_entries.options.async_init(eintrag.entry_id)
    abbruch = await hass.config_entries.options.async_configure(
        menu["flow_id"], {"next_step_id": "tag_entfernen"}
    )
    assert abbruch["reason"] == "keine_eigenen_tage"


async def test_verbindung_fehlt(hass, aioclient_mock) -> None:
    """Ohne erreichbare API wird nichts angelegt."""
    mock_region(aioclient_mock, None)
    mock_termine(aioclient_mock, exc=TimeoutError())
    ergebnis = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    fehler = await hass.config_entries.flow.async_configure(
        ergebnis["flow_id"], {CONF_LAND: "BY"}
    )
    assert fehler["type"] is FlowResultType.FORM
    assert fehler["errors"]["base"] == "cannot_connect"
    assert hass.config_entries.async_entries(DOMAIN) == []
