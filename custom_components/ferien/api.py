"""HTTP-Client für schulferienrechner.de.

Nur Abruf und Parsing. Die Session kommt von außen, es wird keine eigene erzeugt.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

import aiohttp

from .const import (
    HTTP_TIMEOUT_SECONDS,
    USER_AGENT,
    normalisiere_land,
    region_url,
    termine_url,
)
from .logic import Feiertag, Termine, Zeitraum

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = aiohttp.ClientTimeout(total=HTTP_TIMEOUT_SECONDS)


class ApiError(Exception):
    """Die API hat geantwortet, aber nicht brauchbar."""

    def __init__(self, message: str, *, status: int | None = None) -> None:
        """Status fürs Log merken."""
        super().__init__(message)
        self.status = status


class RateLimited(ApiError):
    """HTTP 429. `retry_after` ist eine Wartezeit in Sekunden."""

    def __init__(self, retry_after: float) -> None:
        """Wartezeit übernehmen."""
        super().__init__("Zu viele Anfragen", status=429)
        self.retry_after = retry_after


class NotModified(Exception):
    """HTTP 304. Der gespeicherte Datensatz gilt weiter."""

    def __init__(self, etag: str | None) -> None:
        """ETag der unveränderten Antwort merken."""
        super().__init__("nicht geändert")
        self.etag = etag


class FerienClient:
    """Dünner Client um eine injizierte aiohttp-Session."""

    def __init__(self, session: aiohttp.ClientSession, *, basis_url: str) -> None:
        """Session und Basis-URL speichern. Die Basis dient Tests."""
        self._session = session
        self._basis = basis_url.rstrip("/")

    async def async_termine(
        self,
        code: str,
        etag: str | None,
    ) -> tuple[Termine, str | None, dict[str, Any]]:
        """Termine laden. Wirft `NotModified`, wenn der ETag noch gilt."""
        header = _header(etag)
        url = _url(self._basis, termine_url(code))
        status, header_werte, roh = await self._lesen(url, header)
        antwort_etag = _etag(header_werte)
        if status == 304:
            raise NotModified(antwort_etag or etag)
        if status == 429:
            raise RateLimited(_retry_after(header_werte))
        payload = _json(roh, status)
        if status >= 400:
            raise ApiError(_fehlertext(payload, status), status=status)
        if not isinstance(payload, dict):
            raise ApiError("Antwort ist kein Objekt", status=status)
        return parse_termine(payload), antwort_etag, payload

    async def async_region(self) -> str | None:
        """Bundesland aus `/api/region`. Fehler werden geschluckt."""
        try:
            status, _, roh = await self._lesen(
                _url(self._basis, region_url()),
                _header(None),
            )
        except (ApiError, RateLimited, NotModified):
            _LOGGER.debug("Region nicht ermittelt", exc_info=True)
            return None
        if status != 200:
            return None
        try:
            payload = _json(roh, status)
        except ApiError:
            return None
        if not isinstance(payload, Mapping):
            return None
        return normalisiere_land(payload.get("land"))

    async def _lesen(
        self,
        url: str,
        header: dict[str, str],
    ) -> tuple[int, Mapping[str, str], bytes]:
        try:
            async with self._session.get(url, headers=header, timeout=_TIMEOUT) as resp:
                inhalt = await resp.read()
                return resp.status, resp.headers, inhalt
        except TimeoutError as err:
            raise ApiError("Zeitüberschreitung") from err
        except aiohttp.ClientError as err:
            raise ApiError("Netzwerkfehler") from err


def parse_termine(payload: Mapping[str, Any]) -> Termine:
    """JSON des `/termine`-Vertrags in Dataclasses überführen.

    Unbekannte Felder werden ignoriert. Fehlende `frei_von`/`frei_bis`
    fallen auf `start`/`ende` zurück und werden so gezogen, dass der
    freie Block den offiziellen Zeitraum enthält.
    """
    land = payload.get("land")
    if not isinstance(land, Mapping):
        raise ApiError("Land fehlt")
    code = normalisiere_land(land.get("code"))
    name = land.get("name")
    if code is None or not isinstance(name, str) or not name.strip():
        raise ApiError("Land ist unvollständig")
    von = _datum(payload.get("von"), "von")
    bis = _datum(payload.get("bis"), "bis")
    ferien = tuple(
        sorted(
            (_zeitraum(eintrag, "ferien") for eintrag in _liste(payload, "ferien")),
            key=lambda zeitraum: (zeitraum.start, zeitraum.id),
        )
    )
    schulfrei = tuple(
        sorted(
            (
                _zeitraum(eintrag, "schulfrei")
                for eintrag in _liste(payload, "schulfrei")
            ),
            key=lambda zeitraum: (zeitraum.start, zeitraum.id),
        )
    )
    feiertage = tuple(
        sorted(
            (_feiertag(eintrag) for eintrag in _liste(payload, "feiertage")),
            key=lambda feiertag: (feiertag.datum, feiertag.name),
        )
    )
    try:
        return Termine(
            land_code=code,
            land_name=name.strip(),
            von=von,
            bis=bis,
            ferien=ferien,
            schulfrei=schulfrei,
            feiertage=feiertage,
            quelle=_text(payload.get("quelle")),
            lizenz=_text(payload.get("lizenz")),
            datenstand=_zeitpunkt(payload.get("datenstand")),
        )
    except ValueError as err:
        raise ApiError(str(err)) from err


def _zeitraum(eintrag: object, feld: str) -> Zeitraum:
    if not isinstance(eintrag, Mapping):
        raise ApiError(f"{feld} enthält keinen Eintrag")
    start = _datum(eintrag.get("start"), "start")
    ende = _datum(eintrag.get("ende"), "ende")
    frei_von = _datum_oder(eintrag.get("frei_von"), start)
    frei_bis = _datum_oder(eintrag.get("frei_bis"), ende)
    frei_von = min(frei_von, start)
    frei_bis = max(frei_bis, ende)
    name = eintrag.get("name")
    typ = eintrag.get("typ")
    if not isinstance(name, str) or not name.strip():
        name = typ if isinstance(typ, str) and typ.strip() else "Ferien"
    if not isinstance(typ, str) or not typ.strip():
        typ = "ferien"
    kennung = eintrag.get("id")
    if not isinstance(kennung, str) or not kennung.strip():
        kennung = f"{typ}-{start.isoformat()}"
    hinweis = eintrag.get("hinweis")
    try:
        return Zeitraum(
            id=kennung.strip(),
            name=name.strip(),
            typ=typ.strip(),
            start=start,
            ende=ende,
            frei_von=frei_von,
            frei_bis=frei_bis,
            bestaetigt=eintrag.get("bestaetigt") is not False,
            hinweis=hinweis if isinstance(hinweis, str) and hinweis else None,
        )
    except ValueError as err:
        raise ApiError(str(err)) from err


def _feiertag(eintrag: object) -> Feiertag:
    if not isinstance(eintrag, Mapping):
        raise ApiError("feiertage enthält keinen Eintrag")
    name = eintrag.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ApiError("Feiertag ohne Namen")
    hinweis = eintrag.get("hinweis")
    return Feiertag(
        name=name.strip(),
        datum=_datum(eintrag.get("datum"), "datum"),
        bundesweit=eintrag.get("bundesweit") is True,
        teilweise=eintrag.get("teilweise") is True,
        lokal=eintrag.get("lokal") is True,
        hinweis=hinweis if isinstance(hinweis, str) and hinweis else None,
    )


def _liste(payload: Mapping[str, Any], feld: str) -> list[object]:
    wert = payload.get(feld, [])
    if wert is None:
        return []
    if not isinstance(wert, list):
        raise ApiError(f"{feld} ist keine Liste")
    return wert


def _datum(wert: object, feld: str) -> date:
    if not isinstance(wert, str):
        raise ApiError(f"Feld {feld} fehlt")
    try:
        return date.fromisoformat(wert)
    except ValueError as err:
        raise ApiError(f"Feld {feld} ist kein Datum") from err


def _datum_oder(wert: object, fallback: date) -> date:
    if wert is None:
        return fallback
    return _datum(wert, "datum")


def _zeitpunkt(wert: object) -> datetime | None:
    if not isinstance(wert, str) or not wert:
        return None
    try:
        geparst = datetime.fromisoformat(wert)
    except ValueError:
        return None
    if geparst.tzinfo is None:
        return None
    return geparst


def _text(wert: object) -> str:
    if isinstance(wert, str):
        return wert
    return ""


def _json(roh: bytes, status: int) -> object:
    if not roh:
        return None
    try:
        return json.loads(roh)
    except (UnicodeDecodeError, json.JSONDecodeError) as err:
        raise ApiError("Antwort ist kein JSON", status=status) from err


def _fehlertext(payload: object, status: int) -> str:
    if isinstance(payload, Mapping):
        fehler = payload.get("fehler")
        if isinstance(fehler, Mapping):
            meldung = fehler.get("meldung")
            if isinstance(meldung, str) and meldung.strip():
                return meldung.strip()
    return f"HTTP {status}"


def _header(etag: str | None) -> dict[str, str]:
    header = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if etag:
        header["If-None-Match"] = etag
    return header


def _etag(header: Mapping[str, str]) -> str | None:
    wert = header.get("ETag") or header.get("etag")
    if isinstance(wert, str) and wert:
        return wert
    return None


def _retry_after(header: Mapping[str, str]) -> float:
    """Sekunden aus `Retry-After`. HTTP-Datum wird als 15 Minuten gelesen."""
    roh = header.get("Retry-After") or header.get("retry-after")
    if roh is None:
        return 900.0
    try:
        return max(0.0, float(roh))
    except (TypeError, ValueError):
        return 900.0


def _url(basis: str, absolut: str) -> str:
    """Absolute Vertrags-URL auf eine andere Basis umbiegen, falls gesetzt."""
    prefix = "https://schulferienrechner.de"
    if basis == prefix or not absolut.startswith(prefix):
        return absolut
    return basis + absolut[len(prefix) :]
