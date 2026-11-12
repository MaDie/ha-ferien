"""Coordinator: Abruf, Cache, Mitternacht.

Der tägliche Abruf liegt zufällig zwischen 03:00 und 05:00 Ortszeit.
Um 00:00 Europe/Berlin werden die Zustände neu berechnet, ohne Netz.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.event import (
    async_track_point_in_utc_time,
    async_track_time_change,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .api import ApiError, FerienClient, NotModified, RateLimited
from .const import (
    ABRUF_STUNDE_MAX,
    ABRUF_STUNDE_MIN,
    CACHE_MAX_AGE_HOURS,
    CONF_FEIERTAGE_IM_KALENDER,
    CONF_LAND,
    CONF_REGIONALE_FEIERTAGE,
    DEFAULT_FEIERTAGE_IM_KALENDER,
    DEFAULT_REGIONALE_FEIERTAGE,
    DOMAIN,
)
from .logic import (
    BERLIN,
    EigenerTag,
    Termine,
    heute_in_berlin,
    naechste_mitternacht,
    waehle_abrufzeit,
)
from .repairs import async_sync_issues
from .store import CacheZustand, FerienStore

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Lage:
    """Daten, aus denen die Entitäten ihren Zustand rechnen."""

    termine: Termine
    eigene_tage: tuple[EigenerTag, ...]
    heute: date
    regionale_feiertage: bool
    feiertage_im_kalender: bool
    abgerufen_am: datetime | None


class FerienCoordinator(DataUpdateCoordinator[Lage]):
    """Hält Termine, eigene Tage und den Berliner Kalendertag."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: FerienConfigEntry,
        client: FerienClient,
    ) -> None:
        """Coordinator an den Eintrag binden."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=None,
        )
        self.entry = entry
        self.client = client
        self.store = FerienStore(hass, entry.entry_id)
        self.land_code = str(entry.data[CONF_LAND])
        self._termine: Termine | None = None
        self._payload: dict[str, Any] | None = None
        self._etag: str | None = None
        self._abgerufen_am: datetime | None = None
        self._letzter_erfolg: datetime | None = None
        self._letzter_fehler: str | None = None
        self._abruf_stunde: int | None = None
        self._abruf_minute: int | None = None
        self._eigene: tuple[EigenerTag, ...] = ()
        self._nicht_vor: datetime | None = None
        self._erzwingen = False
        self._versuch_ok = True
        self._geloggt: set[str] = set()
        self._unsub_mitternacht: CALLBACK_TYPE | None = None
        self._unsub_abruf: CALLBACK_TYPE | None = None
        self._geladen = False

    @property
    def eigene_tage(self) -> tuple[EigenerTag, ...]:
        """Gespeicherte eigene Tage."""
        return self._eigene

    @property
    def etag(self) -> str | None:
        """ETag des letzten Abrufs."""
        return self._etag

    @property
    def letzter_fehler(self) -> str | None:
        """Letzter Abruffehler, bis ein Abruf wieder klappt."""
        return self._letzter_fehler

    @property
    def letzter_erfolg(self) -> datetime | None:
        """Zeitpunkt des letzten erfolgreichen Abrufs, inklusive 304."""
        return self._letzter_erfolg

    @property
    def abruf_stunde(self) -> int | None:
        """Stunde des täglichen Abrufs."""
        return self._abruf_stunde

    @property
    def abruf_minute(self) -> int | None:
        """Minute des täglichen Abrufs."""
        return self._abruf_minute

    async def async_shutdown(self) -> None:
        """Zeitpläne lösen und den Coordinator stoppen."""
        self._zeit_abbrechen()
        await super().async_shutdown()

    @callback
    def async_planen(self) -> None:
        """Mitternacht in Berlin und den täglichen Abruf planen."""
        self._zeit_abbrechen()
        stunde = (
            self._abruf_stunde if self._abruf_stunde is not None else ABRUF_STUNDE_MIN
        )
        minute = self._abruf_minute if self._abruf_minute is not None else 0
        self._unsub_mitternacht = async_track_point_in_utc_time(
            self.hass,
            self._um_mitternacht,
            naechste_mitternacht(self._jetzt()),
        )
        self._unsub_abruf = async_track_time_change(
            self.hass,
            self._geplanter_abruf,
            hour=stunde,
            minute=minute,
            second=0,
        )

    async def async_aktualisieren(self) -> bool:
        """Sofort abrufen. `False`, wenn der Abruf scheitert und der Cache bleibt."""
        self._erzwingen = True
        try:
            await self.async_request_refresh()
        finally:
            self._erzwingen = False
        return self._versuch_ok

    async def async_tage_setzen(self, tage: tuple[EigenerTag, ...]) -> None:
        """Eigene Tage ersetzen und die Entitäten neu rechnen."""
        self._eigene = tage
        await self.store.async_speichere_tage(tage)
        if self._termine is not None:
            self.async_set_updated_data(self._lage())

    async def _async_update_data(self) -> Lage:
        """Cache nutzen und nur bei Bedarf das Netz fragen."""
        if not self._geladen:
            await self._laden()
        self._versuch_ok = True
        if self._soll_abrufen():
            await self._abrufen()
        if self._termine is None:
            raise ConfigEntryNotReady(
                "schulferienrechner.de nicht erreichbar",
                retry_after=self._wartezeit(),
            )
        self._reparaturen()
        return self._lage()

    async def _laden(self) -> None:
        self._eigene = await self.store.async_lade_tage()
        cache = await self.store.async_lade_cache()
        self._geladen = True
        if cache is None or cache.termine is None:
            self._zeit_festlegen(None, None)
            return
        self._zeit_festlegen(cache.abruf_stunde, cache.abruf_minute)
        if cache.termine.land_code != self.land_code:
            _LOGGER.info(
                "Cache für %s gehört zu %s und wird verworfen",
                self.land_code,
                cache.termine.land_code,
            )
            return
        self._termine = cache.termine
        self._payload = cache.payload
        self._etag = cache.etag
        self._abgerufen_am = cache.abgerufen_am
        self._letzter_erfolg = cache.letzter_erfolg or cache.abgerufen_am
        self._letzter_fehler = cache.letzter_fehler

    async def _abrufen(self) -> None:
        try:
            termine, etag, payload = await self.client.async_termine(
                self.land_code,
                self._etag,
            )
        except NotModified as err:
            if self._termine is None:
                self._fehlschlag("304 ohne gespeicherte Daten")
                return
            self._uebernehmen(
                jetzt=self._jetzt(),
                etag=err.etag or self._etag,
                payload=self._payload,
                termine=self._termine,
            )
        except RateLimited as err:
            self._fehlschlag(
                f"429, erneut in {err.retry_after:.0f}s",
                retry_after=err.retry_after,
            )
        except ApiError as err:
            self._fehlschlag(str(err))
        else:
            if termine.land_code != self.land_code:
                self._fehlschlag(
                    f"Antwort gilt für {termine.land_code}, erwartet {self.land_code}"
                )
                return
            self._uebernehmen(
                jetzt=self._jetzt(),
                etag=etag,
                payload=payload,
                termine=termine,
            )
        if self._termine is not None:
            await self._cache_schreiben()

    def _uebernehmen(
        self,
        *,
        jetzt: datetime,
        etag: str | None,
        payload: dict[str, Any] | None,
        termine: Termine,
    ) -> None:
        self._termine = termine
        self._payload = payload
        self._etag = etag
        self._abgerufen_am = jetzt
        self._letzter_erfolg = jetzt
        self._letzter_fehler = None
        self._nicht_vor = None
        self._geloggt.clear()
        self._versuch_ok = True

    def _fehlschlag(self, text: str, *, retry_after: float | None = None) -> None:
        self._versuch_ok = False
        self._letzter_fehler = text
        if retry_after is not None:
            self._nicht_vor = self._jetzt() + timedelta(seconds=retry_after)
        self._log_einmal(text, "Abruf für %s fehlgeschlagen: %s", self.land_code, text)

    def _soll_abrufen(self) -> bool:
        if self._erzwingen:
            return True
        if self._nicht_vor is not None and self._jetzt() < self._nicht_vor:
            return False
        if self._termine is None or self._abgerufen_am is None:
            return True
        return self._jetzt() - self._abgerufen_am >= timedelta(
            hours=CACHE_MAX_AGE_HOURS
        )

    def _lage(self) -> Lage:
        if self._termine is None:
            msg = "Lage ohne Termine"
            raise RuntimeError(msg)
        heute = heute_in_berlin(self._jetzt())
        if not (self._termine.von <= heute <= self._termine.bis):
            self._log_einmal(
                "ausserhalb",
                "Keine Termine für %s am %s (Daten %s bis %s)",
                self.land_code,
                heute.isoformat(),
                self._termine.von.isoformat(),
                self._termine.bis.isoformat(),
            )
        regional, feiertage = self.optionen()
        return Lage(
            termine=self._termine,
            eigene_tage=self._eigene,
            heute=heute,
            regionale_feiertage=regional,
            feiertage_im_kalender=feiertage,
            abgerufen_am=self._abgerufen_am,
        )

    def optionen(self) -> tuple[bool, bool]:
        """Regionale Feiertage und Feiertage im Kalender."""
        options = self.entry.options
        return (
            bool(options.get(CONF_REGIONALE_FEIERTAGE, DEFAULT_REGIONALE_FEIERTAGE)),
            bool(
                options.get(CONF_FEIERTAGE_IM_KALENDER, DEFAULT_FEIERTAGE_IM_KALENDER)
            ),
        )

    def _reparaturen(self) -> None:
        if self._termine is None:
            return
        async_sync_issues(
            self.hass,
            entry_id=self.entry.entry_id,
            letzter_erfolg=self._letzter_erfolg,
            daten_bis=self._termine.bis,
            land_name=self._termine.land_name,
            heute=heute_in_berlin(self._jetzt()),
        )

    async def _cache_schreiben(self) -> None:
        payload = self._payload if isinstance(self._payload, dict) else None
        await self.store.async_speichere_cache(
            CacheZustand(
                etag=self._etag,
                abgerufen_am=self._abgerufen_am,
                letzter_erfolg=self._letzter_erfolg,
                abruf_stunde=self._abruf_stunde,
                abruf_minute=self._abruf_minute,
                letzter_fehler=self._letzter_fehler,
                payload=payload,
                termine=self._termine,
            )
        )

    def _zeit_festlegen(self, stunde: int | None, minute: int | None) -> None:
        if (
            stunde is not None
            and minute is not None
            and ABRUF_STUNDE_MIN <= stunde <= ABRUF_STUNDE_MAX
            and 0 <= minute <= 59
        ):
            self._abruf_stunde = stunde
            self._abruf_minute = minute
            return
        self._abruf_stunde, self._abruf_minute = waehle_abrufzeit(random.Random())

    @callback
    def _zeit_abbrechen(self) -> None:
        for unsub in (self._unsub_mitternacht, self._unsub_abruf):
            if unsub is not None:
                unsub()
        self._unsub_mitternacht = None
        self._unsub_abruf = None

    async def _um_mitternacht(self, _jetzt: datetime) -> None:
        if self._termine is not None:
            self.async_set_updated_data(self._lage())
            self._reparaturen()
        self._unsub_mitternacht = async_track_point_in_utc_time(
            self.hass,
            self._um_mitternacht,
            naechste_mitternacht(self._jetzt()),
        )

    async def _geplanter_abruf(self, _jetzt: datetime) -> None:
        if self._nicht_vor is not None and self._jetzt() < self._nicht_vor:
            return
        await self.async_request_refresh()

    def _wartezeit(self) -> float | None:
        if self._nicht_vor is None:
            return None
        rest = (self._nicht_vor - self._jetzt()).total_seconds()
        if rest <= 0:
            return None
        return rest

    def _jetzt(self) -> datetime:
        zone = dt_util.get_time_zone("Europe/Berlin") or BERLIN
        return dt_util.now(zone)

    def _log_einmal(self, schluessel: str, nachricht: str, *args: object) -> None:
        if schluessel in self._geloggt:
            return
        self._geloggt.add(schluessel)
        _LOGGER.warning(nachricht, *args)


@dataclass(slots=True)
class FerienRuntime:
    """Laufzeitdaten eines Eintrags."""

    coordinator: FerienCoordinator


type FerienConfigEntry = ConfigEntry[FerienRuntime]
