"""Zweige, die der Alltagspfad nicht trifft."""

from __future__ import annotations

from datetime import date, datetime

import aiohttp
import probatio
import pytest
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    SOURCE_USER,
    ConfigEntryState,
)
from homeassistant.const import STATE_ON
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.ferien.api import (
    ApiError,
    FerienClient,
    RateLimited,
    _retry_after,
    _url,
    parse_termine,
)
from custom_components.ferien.config_flow import (
    FerienConfigFlow,
    FerienOptionsFlow,
    _datum,
)
from custom_components.ferien.const import (
    API_BASE_URL,
    CONF_LAND,
    DOMAIN,
    integration_version,
    normalisiere_land,
)
from custom_components.ferien.diagnostics import async_get_config_entry_diagnostics
from custom_components.ferien.logic import (
    EigenerTag,
    Termine,
    Zeitraum,
    erster_schultag,
    naechster_schultag,
)
from custom_components.ferien.repairs import async_sync_abruf
from custom_components.ferien.services import _als_datum, _typen, async_setup_services
from custom_components.ferien.store import parse_cache, parse_tage, termine_als_json
from tests.hilfe import (
    async_fire_time_changed_exact,
    lade_fixture,
    mock_region,
    mock_termine,
    richte_ein,
    termine_url,
)


def _ferien(start: date, ende: date) -> Zeitraum:
    return Zeitraum(
        id="f",
        name="Ferien",
        typ="ferien",
        start=start,
        ende=ende,
        frei_von=start,
        frei_bis=ende,
        bestaetigt=True,
        hinweis=None,
    )


def _termine(von: date, bis: date, ferien: tuple[Zeitraum, ...] = ()) -> Termine:
    return Termine(
        land_code="BY",
        land_name="Bayern",
        von=von,
        bis=bis,
        ferien=ferien,
        schulfrei=(),
        feiertage=(),
        quelle="",
        lizenz="",
        datenstand=None,
    )


def test_grenzen_von_zeitraum_und_schultag() -> None:
    """Ungültige Intervalle und ein Cache ohne folgenden Schultag."""
    with pytest.raises(ValueError, match="start"):
        _ferien(date(2026, 11, 12), date(2026, 11, 11))
    with pytest.raises(ValueError, match="Block"):
        Zeitraum(
            id="x",
            name="X",
            typ="ferien",
            start=date(2026, 11, 11),
            ende=date(2026, 11, 12),
            frei_von=date(2026, 11, 12),
            frei_bis=date(2026, 11, 12),
            bestaetigt=True,
            hinweis=None,
        )
    with pytest.raises(ValueError, match="von"):
        _termine(date(2026, 12, 1), date(2026, 11, 1))

    rand = _termine(
        date(2026, 11, 11),
        date(2026, 11, 14),
        (_ferien(date(2026, 11, 11), date(2026, 11, 14)),),
    )
    assert erster_schultag(date(2026, 11, 11), rand, (), regionale=False) is None
    eigene = (EigenerTag(start=date(2026, 11, 12), ende=date(2026, 11, 14), name="Zu"),)
    leer = _termine(date(2026, 11, 11), date(2026, 11, 14))
    assert naechster_schultag(date(2026, 11, 11), leer, eigene, regionale=False) is None


def test_parser_und_store(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fehlende Felder, leere Listen und ein Cache, der sich nicht lesen lässt."""
    payload = lade_fixture()
    payload["ferien"] = ["kein-objekt"]
    with pytest.raises(ApiError, match="keinen Eintrag"):
        parse_termine(payload)

    payload = lade_fixture()
    payload["feiertage"] = [{"datum": "2027-01-01"}]
    with pytest.raises(ApiError, match="Namen"):
        parse_termine(payload)

    payload = lade_fixture()
    payload["ferien"][0]["name"] = " "
    payload["ferien"][0]["typ"] = ""
    payload["ferien"][0]["id"] = ""
    payload["schulfrei"] = None
    payload["feiertage"] = None
    payload["datenstand"] = "kein-zeitpunkt"
    payload["quelle"] = None
    erste = parse_termine(payload).ferien[0]
    assert erste.name == "Ferien"
    assert erste.typ == "ferien"
    assert erste.id == f"ferien-{erste.start.isoformat()}"
    assert parse_termine(payload).datenstand is None

    payload = lade_fixture()
    payload["land"] = "BY"
    with pytest.raises(ApiError, match="Land fehlt"):
        parse_termine(payload)
    payload = lade_fixture()
    payload["ferien"] = {"nein": True}
    with pytest.raises(ApiError, match="Liste"):
        parse_termine(payload)
    payload = lade_fixture()
    payload["von"] = "gestern"
    with pytest.raises(ApiError, match="Datum"):
        parse_termine(payload)

    assert _retry_after({}) == 900
    assert _retry_after({"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"}) == 900
    assert _url("http://lokal", "https://schulferienrechner.de/api/v1/meta") == (
        "http://lokal/api/v1/meta"
    )
    assert normalisiere_land("  ") is None
    assert parse_cache({"payload": {"land": "x"}}) is None
    assert parse_tage(None) == ()
    assert parse_tage({"tage": "nein"}) == ()
    assert parse_tage({"tage": [{"start": "2026-11-12", "name": 1}]}) == ()
    assert parse_tage({"tage": ["text"]}) == ()
    rund = termine_als_json(parse_termine(lade_fixture()))
    assert parse_termine(rund).land_code == "BY"
    assert parse_cache({"abgerufen_am": "gestern", "payload": rund}) is not None

    monkeypatch.setattr(
        "custom_components.ferien.const.json.loads",
        lambda *_args, **_kwargs: {"version": ""},
    )
    with pytest.raises(RuntimeError, match="Version"):
        integration_version()


def test_datum_und_typen() -> None:
    """Options-Helfer und der Validator der Termin-Typen."""
    assert _datum("2026-11-11") == date(2026, 11, 11)
    assert _datum("gestern") is None
    assert _datum(1) is None
    assert _als_datum(date(2026, 11, 11)) == date(2026, 11, 11)
    with pytest.raises(ServiceValidationError):
        _als_datum("2026-11-11")
    assert _typen("feiertag") == ["feiertag"]
    with pytest.raises(probatio.Invalid):
        _typen([1])
    with pytest.raises(ValueError, match="Domain"):
        FerienConfigFlow.async_get_options_flow(type("Eintrag", (), {"domain": "x"})())


async def test_client_fehlerbilder(hass, aioclient_mock) -> None:
    """Liste, leerer Körper, Netzwerk und eine andere Basis-URL."""
    url = termine_url("BY")
    client = FerienClient(async_get_clientsession(hass), basis_url=API_BASE_URL)
    aioclient_mock.get(url, status=200, json=["liste"])
    with pytest.raises(ApiError, match="Objekt"):
        await client.async_termine("BY", None)

    aioclient_mock.clear_requests()
    aioclient_mock.get(url, status=200, content=b"")
    with pytest.raises(ApiError, match="Objekt"):
        await client.async_termine("BY", None)

    aioclient_mock.clear_requests()
    aioclient_mock.get(url, status=500, content=b"")
    with pytest.raises(ApiError, match="HTTP 500"):
        await client.async_termine("BY", None)

    aioclient_mock.clear_requests()
    aioclient_mock.get(url, status=429)
    with pytest.raises(RateLimited) as begrenzt:
        await client.async_termine("BY", None)
    assert begrenzt.value.retry_after == 900

    aioclient_mock.clear_requests()
    aioclient_mock.get(url, exc=aiohttp.ClientError())
    with pytest.raises(ApiError, match="Netzwerk"):
        await client.async_termine("BY", None)

    aioclient_mock.clear_requests()
    aioclient_mock.get(
        "https://schulferienrechner.de/api/region", status=200, content=b"kein-json"
    )
    assert await client.async_region() is None
    aioclient_mock.clear_requests()
    aioclient_mock.get("https://schulferienrechner.de/api/region", status=503)
    assert await client.async_region() is None
    aioclient_mock.clear_requests()
    aioclient_mock.get("https://schulferienrechner.de/api/region", json=["BY"])
    assert await client.async_region() is None

    lokal = FerienClient(async_get_clientsession(hass), basis_url="http://lokal.test")
    aioclient_mock.get(
        "http://lokal.test/api/v1/laender/BY/termine",
        json=lade_fixture(),
    )
    termine, _, _payload = await lokal.async_termine("BY", None)
    assert termine.land_code == "BY"


async def test_erster_abruf_304_und_429(hass, aioclient_mock) -> None:
    """Ohne Cache bleibt der Eintrag beim Warten. 304 ist dann kein Erfolg."""
    eintrag = await richte_ein(hass, aioclient_mock, status=304, content=b"")
    assert eintrag.state is ConfigEntryState.SETUP_RETRY

    aioclient_mock.clear_requests()
    nochmal = await richte_ein(
        hass, aioclient_mock, entry_id="ferien-by-429", status=429, content=b""
    )
    assert nochmal.state is ConfigEntryState.SETUP_RETRY


async def test_retry_after_haelt_den_abruf_an(hass, aioclient_mock, freezer) -> None:
    """Während Retry-After holt weder ein Refresh noch der Plan neue Daten."""
    eintrag = await richte_ein(hass, aioclient_mock)
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        termine_url("BY"),
        status=429,
        headers={"Retry-After": "172800"},
    )
    coordinator = eintrag.runtime_data.coordinator
    assert await coordinator.async_aktualisieren() is False
    await coordinator.async_request_refresh()
    assert aioclient_mock.call_count == 1

    ziel = datetime.fromisoformat("2026-11-12T03:17:00+01:00")
    freezer.move_to(ziel)
    async_fire_time_changed_exact(hass, ziel)
    await hass.async_block_till_done()
    await coordinator._geplanter_abruf(ziel)
    assert aioclient_mock.call_count == 1
    assert hass.states.get("sensor.ferien_by_tage_bis_ferien").state == "42"


async def test_reconfigure_gleich_oder_unbekannt(hass, aioclient_mock) -> None:
    """Dasselbe Land braucht keinen Abruf. Eine 404 ist ein unbekannter Fehler."""
    eintrag = await richte_ein(hass, aioclient_mock)
    vorher = aioclient_mock.call_count
    formular = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": eintrag.entry_id},
    )
    gleich = await hass.config_entries.flow.async_configure(
        formular["flow_id"], {CONF_LAND: "BY"}
    )
    await hass.async_block_till_done()
    assert gleich["reason"] == "reconfigure_successful"
    assert aioclient_mock.call_count == vorher

    aioclient_mock.clear_requests()
    mock_termine(
        aioclient_mock,
        "BE",
        status=404,
        payload={"fehler": {"code": "unbekanntes_land", "meldung": "Nein"}},
    )
    formular = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_RECONFIGURE, "entry_id": eintrag.entry_id},
    )
    fehler = await hass.config_entries.flow.async_configure(
        formular["flow_id"], {CONF_LAND: "BE"}
    )
    assert fehler["errors"]["base"] == "unknown"


async def test_options_lehnt_eingaben_ab_und_schreibt_ohne_laufzeit(
    hass, aioclient_mock
) -> None:
    """Datum, Name und der Store-Pfad, wenn der Coordinator nicht läuft."""
    eintrag = await richte_ein(hass, aioclient_mock)
    menu = await hass.config_entries.options.async_init(eintrag.entry_id)
    form = await hass.config_entries.options.async_configure(
        menu["flow_id"], {"next_step_id": "tag_hinzufuegen"}
    )
    schlecht = await hass.config_entries.options.async_configure(
        form["flow_id"],
        {"start": date(2026, 11, 12), "ende": date(2026, 11, 1), "name": "Zu"},
    )
    assert schlecht["errors"]["ende"] == "zeitraum_ungueltig"
    lang = await hass.config_entries.options.async_configure(
        schlecht["flow_id"],
        {"start": date(2026, 11, 12), "name": "x" * 81},
    )
    assert lang["errors"]["name"] == "name_ungueltig"

    flow = FerienOptionsFlow()
    flow.hass = hass
    flow.handler = eintrag.entry_id
    ungueltig = await flow.async_step_tag_hinzufuegen({"start": "gestern", "name": "A"})
    assert ungueltig["errors"]["start"] == "datum_ungueltig"

    laufzeit = eintrag.runtime_data
    eintrag.runtime_data = None
    assert await flow._tage() == ()
    await flow._tage_schreiben(())
    eintrag.runtime_data = laufzeit

    await hass.services.async_call(
        DOMAIN,
        "tag_hinzufuegen",
        {"config_entry_id": eintrag.entry_id, "start": "2026-11-20", "name": "Ausflug"},
        blocking=True,
    )
    menu = await hass.config_entries.options.async_init(eintrag.entry_id)
    form = await hass.config_entries.options.async_configure(
        menu["flow_id"], {"next_step_id": "tag_entfernen"}
    )
    weg = await flow.async_step_tag_entfernen({"start": "kein-datum"})
    assert weg["errors"]["start"] == "datum_ungueltig"
    unbekannt = await flow.async_step_tag_entfernen({"start": "2026-01-01"})
    assert unbekannt["errors"]["start"] == "tag_unbekannt"
    assert form["type"] == "form"


async def test_services_filtern_und_aktualisieren_alles(hass, aioclient_mock) -> None:
    """Feiertage, eigene Tage und ein Abruf über alle Einträge."""
    eintrag = await richte_ein(hass, aioclient_mock)
    await hass.services.async_call(
        DOMAIN,
        "tag_hinzufuegen",
        {"config_entry_id": eintrag.entry_id, "start": "2026-11-20", "name": "Ausflug"},
        blocking=True,
    )
    antwort = await hass.services.async_call(
        DOMAIN,
        "termine_abrufen",
        {
            "config_entry_id": eintrag.entry_id,
            "von": "2026-08-01",
            "bis": "2026-11-20",
            "typen": ["feiertag", "eigener_tag"],
        },
        blocking=True,
        return_response=True,
    )
    namen = {punkt["name"] for punkt in antwort["termine"]}
    assert "Allerheiligen" in namen
    assert "Ausflug" in namen
    assert "Augsburger Friedensfest" not in namen

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "termine_abrufen",
            {
                "config_entry_id": eintrag.entry_id,
                "von": "2026-11-20",
                "bis": "2026-11-01",
            },
            blocking=True,
            return_response=True,
        )
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "tag_hinzufuegen",
            {"config_entry_id": eintrag.entry_id, "start": "2026-11-21", "name": " "},
            blocking=True,
        )
    await async_setup_services(hass)

    aioclient_mock.clear_requests()
    mock_termine(aioclient_mock, exc=TimeoutError())
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(DOMAIN, "aktualisieren", {}, blocking=True)
    assert hass.states.get("sensor.ferien_by_tage_bis_ferien").state == "43"

    eintrag.runtime_data = None
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            "tag_entfernen",
            {"config_entry_id": eintrag.entry_id, "start": "2026-11-20"},
            blocking=True,
        )


async def test_aktualisieren_ohne_eintrag(hass) -> None:
    """Ohne geladenen Eintrag gibt es nichts zu holen."""
    await async_setup_services(hass)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "aktualisieren", {}, blocking=True)


async def test_diagnose_und_repair_ohne_erfolg(hass) -> None:
    """Ein Eintrag ohne Coordinator hat keine Diagnose und kein Abruf-Issue."""
    from pytest_homeassistant.common import MockConfigEntry

    eintrag = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_LAND: "BY"},
        unique_id="BY",
        entry_id="ferien-leer",
        title="Ferien Bayern",
    )
    eintrag.add_to_hass(hass)
    daten = await async_get_config_entry_diagnostics(hass, eintrag)
    assert daten == {"land": "BY", "optionen": {}, "bereit": False}
    async_sync_abruf(
        hass,
        entry_id=eintrag.entry_id,
        letzter_erfolg=None,
        land_name="Bayern",
        heute=date(2026, 11, 11),
    )


async def test_zu_viele_anfragen_im_flow(hass, aioclient_mock) -> None:
    """429 im Flow ist ein Verbindungsfehler."""
    aioclient_mock.get(
        termine_url("BY"),
        status=429,
        headers={"Retry-After": "30"},
    )
    mock_region(aioclient_mock, None)
    ergebnis = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    fehler = await hass.config_entries.flow.async_configure(
        ergebnis["flow_id"], {CONF_LAND: "BY"}
    )
    assert fehler["errors"]["base"] == "cannot_connect"


async def test_feiertag_traegt_den_namen(hass, aioclient_mock, freezer) -> None:
    """An Christi Himmelfahrt steht der Name am Binärsensor."""
    await richte_ein(hass, aioclient_mock)
    ziel = datetime.fromisoformat("2027-05-06T12:00:00+02:00")
    freezer.move_to(ziel)
    async_fire_time_changed_exact(hass, ziel)
    await hass.async_block_till_done()
    zustand = hass.states.get("binary_sensor.ferien_by_feiertag_heute")
    assert zustand is not None
    assert zustand.state == STATE_ON
    assert zustand.attributes["name"] == "Christi Himmelfahrt"
