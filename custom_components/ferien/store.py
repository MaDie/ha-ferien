"""HA-Store für Cache und eigene Tage.

Eigene Tage liegen unter `ferien.<entry_id>`, der Cache daneben. Beides
bleibt im Store von Home Assistant und nicht im Integrationsordner.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .api import ApiError, parse_termine
from .const import CACHE_KEY, STORAGE_VERSION, TAGE_KEY
from .logic import EigenerTag, Termine, Zeitraum


@dataclass(frozen=True, slots=True)
class CacheZustand:
    """Gespeicherter Abruf inklusive Zeitplan.

    `payload` ist die ursprüngliche API-Antwort. Sie wird unverändert
    zurückgeschrieben, damit der Cache ein Abbild des Vertrags bleibt.
    """

    etag: str | None
    abgerufen_am: datetime | None
    letzter_erfolg: datetime | None
    abruf_stunde: int | None
    abruf_minute: int | None
    letzter_fehler: str | None
    payload: dict[str, Any] | None
    termine: Termine | None


class FerienStore:
    """Zwei versionierte Stores pro Config-Eintrag."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Stores für diesen Eintrag öffnen."""
        self.cache: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            CACHE_KEY.format(entry_id=entry_id),
        )
        self.tage: Store[dict[str, Any]] = Store(
            hass,
            STORAGE_VERSION,
            TAGE_KEY.format(entry_id=entry_id),
        )

    async def async_lade_cache(self) -> CacheZustand | None:
        """Cache laden. Beschädigte Daten ergeben `None`."""
        roh = await self.cache.async_load()
        if roh is None:
            return None
        return parse_cache(roh)

    async def async_speichere_cache(self, zustand: CacheZustand) -> None:
        """Cache schreiben."""
        await self.cache.async_save(dump_cache(zustand))

    async def async_lade_tage(self) -> tuple[EigenerTag, ...]:
        """Eigene Tage laden. Beschädigte Einträge werden übersprungen."""
        roh = await self.tage.async_load()
        return parse_tage(roh)

    async def async_speichere_tage(self, tage: Sequence[EigenerTag]) -> None:
        """Eigene Tage schreiben."""
        await self.tage.async_save(dump_tage(tage))

    async def async_entfernen(self) -> None:
        """Cache und eigene Tage löschen, wenn der Eintrag entfernt wird."""
        await self.cache.async_remove()
        await self.tage.async_remove()


def parse_cache(roh: Mapping[str, Any]) -> CacheZustand | None:
    """Gespeichertes Cache-Dokument lesen."""
    roh_payload = roh.get("payload")
    payload = dict(roh_payload) if isinstance(roh_payload, Mapping) else None
    termine: Termine | None
    if payload is not None:
        try:
            termine = parse_termine(payload)
        except (ApiError, ValueError):
            return None
    else:
        termine = None
    stunde = roh.get("abruf_stunde")
    minute = roh.get("abruf_minute")
    return CacheZustand(
        etag=_str_oder_none(roh.get("etag")),
        abgerufen_am=_zeit(roh.get("abgerufen_am")),
        letzter_erfolg=_zeit(roh.get("letzter_erfolg")),
        abruf_stunde=stunde if isinstance(stunde, int) else None,
        abruf_minute=minute if isinstance(minute, int) else None,
        letzter_fehler=_str_oder_none(roh.get("letzter_fehler")),
        payload=payload,
        termine=termine,
    )


def dump_cache(zustand: CacheZustand) -> dict[str, Any]:
    """Cache für den Store serialisieren. Das Payload bleibt das API-JSON."""
    return {
        "etag": zustand.etag,
        "abgerufen_am": _iso(zustand.abgerufen_am),
        "letzter_erfolg": _iso(zustand.letzter_erfolg),
        "abruf_stunde": zustand.abruf_stunde,
        "abruf_minute": zustand.abruf_minute,
        "letzter_fehler": zustand.letzter_fehler,
        "payload": zustand.payload,
    }


def parse_tage(roh: Mapping[str, Any] | None) -> tuple[EigenerTag, ...]:
    """Eigene Tage aus dem Store. Ungültige Einträge fallen weg."""
    if roh is None:
        return ()
    liste = roh.get("tage")
    if not isinstance(liste, list):
        return ()
    tage: list[EigenerTag] = []
    for eintrag in liste:
        if not isinstance(eintrag, Mapping):
            continue
        try:
            start = date.fromisoformat(str(eintrag.get("start")))
            ende_roh = eintrag.get("ende")
            ende = (
                start if ende_roh in (None, "") else date.fromisoformat(str(ende_roh))
            )
            name = eintrag.get("name")
            if not isinstance(name, str):
                continue
            tage.append(EigenerTag(start=start, ende=ende, name=name.strip()))
        except (TypeError, ValueError):
            continue
    return tuple(sorted(tage, key=lambda tag: (tag.start, tag.name)))


def dump_tage(tage: Sequence[EigenerTag]) -> dict[str, Any]:
    """Eigene Tage serialisieren."""
    return {
        "tage": [
            {
                "start": tag.start.isoformat(),
                "ende": tag.ende.isoformat(),
                "name": tag.name,
            }
            for tag in tage
        ]
    }


def termine_als_json(termine: Termine) -> dict[str, Any]:
    """Termine zurück in das Vertragsformat schreiben, damit der Cache rundläuft."""
    return {
        "land": {
            "code": termine.land_code,
            "name": termine.land_name,
        },
        "von": termine.von.isoformat(),
        "bis": termine.bis.isoformat(),
        "ferien": [_zeitraum_json(zeitraum) for zeitraum in termine.ferien],
        "schulfrei": [_zeitraum_json(zeitraum) for zeitraum in termine.schulfrei],
        "feiertage": [
            {
                "name": feiertag.name,
                "datum": feiertag.datum.isoformat(),
                "bundesweit": feiertag.bundesweit,
                "teilweise": feiertag.teilweise,
                "lokal": feiertag.lokal,
                "hinweis": feiertag.hinweis,
            }
            for feiertag in termine.feiertage
        ],
        "quelle": termine.quelle,
        "lizenz": termine.lizenz,
        "datenstand": _iso(termine.datenstand),
    }


def _zeitraum_json(zeitraum: Zeitraum) -> dict[str, Any]:
    return {
        "id": zeitraum.id,
        "name": zeitraum.name,
        "typ": zeitraum.typ,
        "start": zeitraum.start.isoformat(),
        "ende": zeitraum.ende.isoformat(),
        "frei_von": zeitraum.frei_von.isoformat(),
        "frei_bis": zeitraum.frei_bis.isoformat(),
        "bestaetigt": zeitraum.bestaetigt,
        "hinweis": zeitraum.hinweis,
    }


def _zeit(wert: object) -> datetime | None:
    if not isinstance(wert, str) or not wert:
        return None
    try:
        geparst = datetime.fromisoformat(wert)
    except ValueError:
        return None
    if geparst.tzinfo is None:
        return None
    return geparst


def _iso(wert: datetime | None) -> str | None:
    if wert is None:
        return None
    return wert.isoformat()


def _str_oder_none(wert: object) -> str | None:
    if isinstance(wert, str) and wert:
        return wert
    return None
