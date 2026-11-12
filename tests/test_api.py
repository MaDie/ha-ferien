"""Client und Parser, ohne die Integration zu starten."""

from __future__ import annotations

from datetime import date

import pytest
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.ferien.api import (
    ApiError,
    FerienClient,
    NotModified,
    RateLimited,
    parse_termine,
)
from custom_components.ferien.const import API_BASE_URL, USER_AGENT, normalisiere_land
from custom_components.ferien.logic import EigenerTag
from custom_components.ferien.store import (
    CacheZustand,
    dump_cache,
    dump_tage,
    parse_cache,
    parse_tage,
)
from tests.hilfe import lade_fixture, termine_url

pytestmark = pytest.mark.usefixtures("aioclient_mock")


def test_land_wird_aus_code_iso_und_slug() -> None:
    """Vorbelegung akzeptiert Kürzel, DE-ISO und Slug."""
    assert normalisiere_land("by") == "BY"
    assert normalisiere_land("DE-TH") == "TH"
    assert normalisiere_land("Baden-Württemberg") == "BW"
    assert normalisiere_land("thueringen") == "TH"
    assert normalisiere_land(None) is None
    assert normalisiere_land("atlantis") is None


def test_unbekannte_felder_und_fehlende_id() -> None:
    """Der Vertrag darf Felder dazubekommen. Fehlende Id wird ergänzt."""
    payload = lade_fixture()
    payload["zusaetzlich"] = {"egal": True}
    payload["ferien"][0].pop("id")
    payload["ferien"][0].pop("frei_von")
    payload["ferien"][0]["name"] = "  "
    termine = parse_termine(payload)
    erste = termine.ferien[0]
    assert erste.id
    assert erste.frei_von <= erste.start
    assert erste.name
    assert termine.land_code == "BY"


@pytest.mark.parametrize(
    "aenderung",
    ["land", "von", "liste", "datum", "feiertag"],
)
def test_kaputtes_payload_wird_abgelehnt(aenderung: str) -> None:
    """Pflichtfelder fehlen nicht stillschweigend."""
    payload = lade_fixture()
    if aenderung == "land":
        payload["land"] = "BY"
    elif aenderung == "von":
        payload["von"] = "gestern"
    elif aenderung == "liste":
        payload["feiertage"] = {}
    elif aenderung == "datum":
        payload["ferien"][0]["start"] = None
    else:
        payload["feiertage"][0]["name"] = ""
    with pytest.raises(ApiError):
        parse_termine(payload)


def test_store_behaelt_das_payload_und_ueberspringt_muell() -> None:
    """Der Cache schreibt die API-Antwort zurück, nicht eine eigene Form."""
    payload = lade_fixture()
    payload["zusaetzlich"] = 1
    termine = parse_termine(payload)
    zustand = CacheZustand(
        etag="abc",
        abgerufen_am=None,
        letzter_erfolg=None,
        abruf_stunde=3,
        abruf_minute=17,
        letzter_fehler=None,
        payload=payload,
        termine=termine,
    )
    gespeichert = dump_cache(zustand)
    assert gespeichert["payload"]["zusaetzlich"] == 1
    gelesen = parse_cache(gespeichert)
    assert gelesen is not None
    assert gelesen.termine is not None
    assert gelesen.abruf_stunde == 3
    assert parse_cache({"payload": {"land": "nein"}}) is None
    tage = parse_tage(
        {
            "tage": [
                {"start": "2026-11-12", "ende": "2026-11-13", "name": "Wandertag"},
                {"start": "kaputt", "name": "weg"},
                "text",
            ]
        }
    )
    assert tage == (
        EigenerTag(start=date(2026, 11, 12), ende=date(2026, 11, 13), name="Wandertag"),
    )
    assert parse_tage(None) == ()
    assert dump_tage(tage)["tage"][0]["name"] == "Wandertag"


async def test_client_status_und_user_agent(hass, aioclient_mock) -> None:
    """304, 429, Fehlertext und der User-Agent."""
    url = termine_url("BY")
    aioclient_mock.get(url, status=304, headers={"ETag": "gleich"})
    client = FerienClient(async_get_clientsession(hass), basis_url=API_BASE_URL)
    with pytest.raises(NotModified):
        await client.async_termine("BY", "gleich")
    gesendet = aioclient_mock.mock_calls[0][3]
    assert gesendet["User-Agent"] == USER_AGENT
    assert gesendet["If-None-Match"] == "gleich"

    aioclient_mock.clear_requests()
    aioclient_mock.get(url, status=429, headers={"Retry-After": "120"})
    with pytest.raises(RateLimited) as rate:
        await client.async_termine("BY", None)
    assert rate.value.retry_after == 120

    aioclient_mock.clear_requests()
    aioclient_mock.get(
        url,
        status=404,
        json={"fehler": {"code": "unbekanntes_land", "meldung": "Unbekanntes Land"}},
    )
    with pytest.raises(ApiError, match="Unbekanntes Land"):
        await client.async_termine("BY", None)

    aioclient_mock.clear_requests()
    aioclient_mock.get(url, status=200, content=b"kein-json")
    with pytest.raises(ApiError, match="JSON"):
        await client.async_termine("BY", None)

    aioclient_mock.clear_requests()
    aioclient_mock.get(url, exc=TimeoutError())
    with pytest.raises(ApiError, match="Zeit"):
        await client.async_termine("BY", None)


async def test_region_schluck_fehler_und_leeres_land(hass, aioclient_mock) -> None:
    """Eine kaputte Vorbelegung ist kein Fehler im Flow."""
    client = FerienClient(async_get_clientsession(hass), basis_url=API_BASE_URL)
    aioclient_mock.get("https://schulferienrechner.de/api/region", json={"land": None})
    assert await client.async_region() is None
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        "https://schulferienrechner.de/api/region",
        exc=TimeoutError(),
    )
    assert await client.async_region() is None
    aioclient_mock.clear_requests()
    aioclient_mock.get(
        "https://schulferienrechner.de/api/region",
        json={"land": "bayern"},
    )
    assert await client.async_region() == "BY"
