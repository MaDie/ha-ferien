"""Sensoren, Kalender, Cache, Mitternacht und Ausfälle."""

from __future__ import annotations

from datetime import date, datetime

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.entity_component import DATA_INSTANCES

from custom_components.ferien.const import CONF_REGIONALE_FEIERTAGE, DOMAIN
from tests.hilfe import (
    async_fire_time_changed_exact,
    lade_fixture,
    mock_termine,
    richte_ein,
)


def _zustand(hass, entity_id: str):
    zustand = hass.states.get(entity_id)
    assert zustand is not None, entity_id
    return zustand


async def _am(hass, freezer, zeit: str) -> None:
    ziel = datetime.fromisoformat(zeit)
    freezer.move_to(ziel)
    async_fire_time_changed_exact(hass, ziel)
    await hass.async_block_till_done()


async def test_schultag_am_elften(hass, aioclient_mock) -> None:
    """Mittwoch, 43 Tage bis Weihnachten, 29 Schultage, nächster Feiertag der 25."""
    await richte_ein(hass, aioclient_mock)
    assert _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute").state == STATE_OFF
    assert _zustand(hass, "binary_sensor.ferien_by_ferien_heute").state == STATE_OFF
    assert _zustand(hass, "binary_sensor.ferien_by_feiertag_heute").state == STATE_OFF
    assert _zustand(hass, "binary_sensor.ferien_by_schulfrei_morgen").state == STATE_OFF
    assert _zustand(hass, "sensor.ferien_by_tage_bis_ferien").state == "43"
    assert _zustand(hass, "sensor.ferien_by_schultage_bis_ferien").state == "29"
    assert _zustand(hass, "sensor.ferien_by_ferientage_verbleibend").state == "0"
    assert _zustand(hass, "sensor.ferien_by_letzter_schultag").state == "2026-12-23"
    assert _zustand(hass, "sensor.ferien_by_erster_schultag").state == "2027-01-11"
    assert _zustand(hass, "sensor.ferien_by_naechster_schultag").state == "2026-11-12"
    assert _zustand(hass, "sensor.ferien_by_naechster_feiertag").state == "2026-12-25"
    naechste = _zustand(hass, "sensor.ferien_by_naechste_ferien")
    assert naechste.state == "2026-12-24"
    assert naechste.attributes["name"] == "Weihnachtsferien"
    assert naechste.attributes["frei_von"] == "2026-12-24"
    assert naechste.attributes["frei_bis"] == "2027-01-10"
    assert _zustand(hass, "sensor.ferien_by_daten_bis").state == "2028-12-31"
    assert _zustand(hass, "calendar.ferien_by").state == STATE_OFF


async def test_pflichttage(hass, aioclient_mock, freezer) -> None:
    """Ferientag, Freitag davor, Wochenende, Feiertag, schulfreier Tag."""
    await _am(hass, freezer, "2026-11-02T12:00:00+01:00")
    await richte_ein(hass, aioclient_mock)
    assert _zustand(hass, "binary_sensor.ferien_by_ferien_heute").state == STATE_ON
    assert (
        _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute").attributes["grund"]
        == "ferien"
    )
    assert _zustand(hass, "sensor.ferien_by_ferientage_verbleibend").state == "7"

    await _am(hass, freezer, "2026-10-30T12:00:00+01:00")
    await hass.config_entries.async_reload(
        hass.config_entries.async_entries(DOMAIN)[0].entry_id
    )
    await hass.async_block_till_done()
    assert _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute").state == STATE_OFF
    assert _zustand(hass, "sensor.ferien_by_tage_bis_ferien").state == "1"
    assert _zustand(hass, "sensor.ferien_by_schultage_bis_ferien").state == "0"
    assert _zustand(hass, "sensor.ferien_by_erster_schultag").state == "2026-11-09"

    await _am(hass, freezer, "2026-11-08T12:00:00+01:00")
    await hass.config_entries.async_reload(
        hass.config_entries.async_entries(DOMAIN)[0].entry_id
    )
    await hass.async_block_till_done()
    frei = _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute")
    assert frei.state == STATE_ON
    assert frei.attributes["grund"] == "wochenende"
    assert _zustand(hass, "binary_sensor.ferien_by_ferien_heute").state == STATE_OFF
    assert _zustand(hass, "sensor.ferien_by_ferientage_verbleibend").state == "1"
    assert _zustand(hass, "binary_sensor.ferien_by_schulfrei_morgen").state == STATE_OFF

    await _am(hass, freezer, "2026-11-18T12:00:00+01:00")
    await hass.config_entries.async_reload(
        hass.config_entries.async_entries(DOMAIN)[0].entry_id
    )
    await hass.async_block_till_done()
    tag = _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute")
    assert tag.state == STATE_ON
    assert tag.attributes["grund"] == "schulfrei"
    assert tag.attributes["name"] == "Buß- und Bettag"
    assert _zustand(hass, "binary_sensor.ferien_by_feiertag_heute").state == STATE_OFF

    await _am(hass, freezer, "2027-05-06T12:00:00+02:00")
    await hass.config_entries.async_reload(
        hass.config_entries.async_entries(DOMAIN)[0].entry_id
    )
    await hass.async_block_till_done()
    himmel = _zustand(hass, "binary_sensor.ferien_by_feiertag_heute")
    assert himmel.state == STATE_ON
    assert himmel.attributes["name"] == "Christi Himmelfahrt"
    assert _zustand(hass, "binary_sensor.ferien_by_ferien_heute").state == STATE_OFF

    await _am(hass, freezer, "2026-12-25T12:00:00+01:00")
    await hass.config_entries.async_reload(
        hass.config_entries.async_entries(DOMAIN)[0].entry_id
    )
    await hass.async_block_till_done()
    assert (
        _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute").attributes["grund"]
        == "ferien"
    )
    assert _zustand(hass, "binary_sensor.ferien_by_feiertag_heute").state == STATE_ON


async def test_mitternacht_ohne_neuen_abruf(hass, aioclient_mock, freezer) -> None:
    """Freitag auf Samstag. Der Zustand wechselt, das Netz bleibt still."""
    await _am(hass, freezer, "2026-10-30T12:00:00+01:00")
    await richte_ein(hass, aioclient_mock)
    assert _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute").state == STATE_OFF
    vorher = aioclient_mock.call_count
    await _am(hass, freezer, "2026-10-31T00:00:01+01:00")
    assert _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute").state == STATE_ON
    assert (
        _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute").attributes["grund"]
        == "wochenende"
    )
    assert aioclient_mock.call_count == vorher


async def test_entity_ids_auf_deutsch(hass, aioclient_mock) -> None:
    """Deutsche Oberfläche ändert die entity_id nicht."""
    eintrag = await richte_ein(hass, aioclient_mock, sprache="de")
    assert eintrag.state is ConfigEntryState.LOADED
    assert hass.states.get("binary_sensor.ferien_by_schulfrei_heute")
    assert hass.states.get("sensor.ferien_by_naechste_ferien")
    assert hass.states.get("calendar.ferien_by")


async def test_englische_entity_ids(hass, aioclient_mock) -> None:
    """Dieselbe ID bei Sprache Englisch."""
    await richte_ein(hass, aioclient_mock, sprache="en")
    assert hass.states.get("binary_sensor.ferien_by_schulfrei_heute")
    assert hass.states.get("calendar.ferien_by")


async def test_regionaler_feiertag(hass, aioclient_mock, freezer) -> None:
    """Augsburg schaltet den Feiertag, Schulfrei bleibt wegen der Sommerferien an."""
    await _am(hass, freezer, "2026-08-08T12:00:00+02:00")
    await richte_ein(hass, aioclient_mock)
    assert _zustand(hass, "binary_sensor.ferien_by_feiertag_heute").state == STATE_OFF
    assert _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute").state == STATE_ON
    eintrag = hass.config_entries.async_entries(DOMAIN)[0]
    hass.config_entries.async_update_entry(
        eintrag, options={CONF_REGIONALE_FEIERTAGE: True}
    )
    await hass.config_entries.async_reload(eintrag.entry_id)
    await hass.async_block_till_done()
    assert _zustand(hass, "binary_sensor.ferien_by_feiertag_heute").state == STATE_ON
    assert _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute").state == STATE_ON
    assert (
        _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute").attributes["grund"]
        == "ferien"
    )


async def test_cache_ohne_netz_und_etag(hass, aioclient_mock, freezer) -> None:
    """Frischer Cache holt nichts. Nach 25 Stunden reicht ein 304."""
    await richte_ein(hass, aioclient_mock)
    assert aioclient_mock.call_count == 1
    eintrag = hass.config_entries.async_entries(DOMAIN)[0]
    await hass.config_entries.async_unload(eintrag.entry_id)
    aioclient_mock.clear_requests()
    await hass.config_entries.async_setup(eintrag.entry_id)
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == 0
    assert _zustand(hass, "sensor.ferien_by_tage_bis_ferien").state == "43"

    aioclient_mock.get(
        "https://schulferienrechner.de/api/v1/laender/BY/termine",
        status=304,
        headers={"ETag": "by-1"},
    )
    await _am(hass, freezer, "2026-11-12T15:00:00+01:00")
    await eintrag.runtime_data.coordinator.async_request_refresh()
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == 1
    assert aioclient_mock.mock_calls[0][3]["If-None-Match"] == "by-1"
    assert _zustand(hass, "sensor.ferien_by_tage_bis_ferien").state == "42"


async def test_ausfaelle_einzeln(hass, aioclient_mock, freezer) -> None:
    """Jeder Fehler lässt den Cache in Kraft. 429 hält die nächste Anfrage auf."""
    await richte_ein(hass, aioclient_mock)
    eintrag = hass.config_entries.async_entries(DOMAIN)[0]
    koordinaten = eintrag.runtime_data.coordinator
    vorher = _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute").state

    for kwargs in (
        {"exc": TimeoutError()},
        {"status": 500, "payload": {"fehler": {"code": "x", "meldung": "kaputt"}}},
        {"status": 200, "content": b"kein-json"},
    ):
        aioclient_mock.clear_requests()
        mock_termine(aioclient_mock, **kwargs)
        await _am(hass, freezer, "2026-11-12T16:00:00+01:00")
        assert await koordinaten.async_aktualisieren() is False
        await hass.async_block_till_done()
        assert _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute").state == vorher

    aioclient_mock.clear_requests()
    aioclient_mock.get(
        "https://schulferienrechner.de/api/v1/laender/BY/termine",
        status=429,
        headers={"Retry-After": "3600"},
    )
    await _am(hass, freezer, "2026-11-12T18:00:00+01:00")
    assert await koordinaten.async_aktualisieren() is False
    aufrufe = aioclient_mock.call_count
    await koordinaten.async_request_refresh()
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == aufrufe
    assert _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute").state == vorher


async def test_ohne_daten_nicht_aus(hass, aioclient_mock, freezer) -> None:
    """Vor der Abdeckung ist ein Wochentag unavailable, ein Samstag schulfrei."""
    await _am(hass, freezer, "2026-07-01T12:00:00+02:00")
    await richte_ein(hass, aioclient_mock)
    assert (
        _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute").state
        == STATE_UNAVAILABLE
    )
    assert (
        _zustand(hass, "binary_sensor.ferien_by_ferien_heute").state
        == STATE_UNAVAILABLE
    )
    assert _zustand(hass, "sensor.ferien_by_tage_bis_ferien").state == STATE_UNAVAILABLE
    assert _zustand(hass, "sensor.ferien_by_daten_bis").state == "2028-12-31"
    await _am(hass, freezer, "2026-07-04T12:00:00+02:00")
    assert _zustand(hass, "binary_sensor.ferien_by_schulfrei_heute").state == STATE_ON
    assert (
        _zustand(hass, "binary_sensor.ferien_by_ferien_heute").state
        == STATE_UNAVAILABLE
    )


async def test_kein_naechster_feiertag_ist_unknown(
    hass, aioclient_mock, freezer
) -> None:
    """Am letzten Tag der Abdeckung gibt es keinen nächsten Feiertag."""
    await _am(hass, freezer, "2028-12-31T12:00:00+01:00")
    await richte_ein(hass, aioclient_mock)
    assert _zustand(hass, "sensor.ferien_by_naechster_feiertag").state == STATE_UNKNOWN
    assert _zustand(hass, "sensor.ferien_by_naechster_schultag").state == STATE_UNKNOWN


async def test_repairs_und_entfernen(hass, aioclient_mock, freezer) -> None:
    """Kurzer Horizont und 14 Tage ohne Abruf erzeugen Issues. Entfernen löscht sie."""
    payload = lade_fixture()
    payload["bis"] = "2026-12-01"
    await richte_ein(hass, aioclient_mock, payload=payload)
    eintrag = hass.config_entries.async_entries(DOMAIN)[0]
    registry = ir.async_get(hass)
    assert (
        registry.async_get_issue(DOMAIN, f"daten_enden_{eintrag.entry_id}") is not None
    )
    aioclient_mock.clear_requests()
    mock_termine(aioclient_mock, exc=TimeoutError())
    await _am(hass, freezer, "2026-11-26T12:00:00+01:00")
    assert await eintrag.runtime_data.coordinator.async_aktualisieren() is False
    await hass.async_block_till_done()
    assert (
        registry.async_get_issue(DOMAIN, f"abruf_veraltet_{eintrag.entry_id}")
        is not None
    )
    await hass.config_entries.async_remove(eintrag.entry_id)
    await hass.async_block_till_done()
    assert (
        registry.async_get_issue(DOMAIN, f"abruf_veraltet_{eintrag.entry_id}") is None
    )
    assert registry.async_get_issue(DOMAIN, f"daten_enden_{eintrag.entry_id}") is None


async def test_kalender_liefert_den_buss_und_bettag(hass, aioclient_mock) -> None:
    """Ganztägig, Ende exklusiv, uid aus der API."""
    await richte_ein(hass, aioclient_mock)
    antwort = await hass.services.async_call(
        "calendar",
        "get_events",
        {
            "entity_id": "calendar.ferien_by",
            "start_date_time": "2026-11-18T00:00:00+01:00",
            "end_date_time": "2026-11-19T00:00:00+01:00",
        },
        blocking=True,
        return_response=True,
    )
    text = str(antwort)
    assert "Buß- und Bettag" in text
    assert "2026-11-19" in text
    kalender = hass.data[DATA_INSTANCES]["calendar"].get_entity("calendar.ferien_by")
    assert kalender is not None
    events = await kalender.async_get_events(
        hass,
        datetime.fromisoformat("2026-11-18T00:00:00+01:00"),
        datetime.fromisoformat("2026-11-19T00:00:00+01:00"),
    )
    assert events[0].uid == "by-schulfrei-2026-11-18"
    assert events[0].end == date(2026, 11, 19)


async def test_falsches_land_im_payload_wird_verworfen(hass, aioclient_mock) -> None:
    """Eine Antwort für ein anderes Land ist kein Cache."""
    payload = lade_fixture()
    payload["land"]["code"] = "BE"
    eintrag = await richte_ein(hass, aioclient_mock, payload=payload)
    assert eintrag.state is ConfigEntryState.SETUP_RETRY
