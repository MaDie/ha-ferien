"""Kalender mit Ferien, schulfreien Tagen, eigenen Tagen und Feiertagen."""

from __future__ import annotations

from datetime import datetime, time

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import KALENDER_KEY
from .coordinator import FerienConfigEntry, FerienCoordinator
from .entity import FerienEntity
from .logic import BERLIN, Ereignis, ereignisse, passendes_ereignis

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FerienConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Kalender anlegen."""
    async_add_entities([FerienKalender(entry.runtime_data.coordinator)])


class FerienKalender(FerienEntity, CalendarEntity):
    """Ganztägige Termine. `end` ist exklusiv."""

    def __init__(self, coordinator: FerienCoordinator) -> None:
        """Kalender an den Eintrag hängen."""
        super().__init__(coordinator, KALENDER_KEY, "calendar")

    @property
    def event(self) -> CalendarEvent | None:
        """Laufendes oder nächstes Ereignis für den Zustand des Kalenders."""
        if not self.coordinator.last_update_success:
            return None
        lage = self.coordinator.data
        passend = passendes_ereignis(lage.heute, self._liste())
        if passend is None:
            return None
        return _event(passend)

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        """Ereignisse, die das abgefragte Fenster schneiden."""
        fenster_start = dt_util.as_utc(start_date)
        fenster_ende = dt_util.as_utc(end_date)
        return [
            _event(eintrag)
            for eintrag in self._liste()
            if _schneidet(eintrag, fenster_start, fenster_ende)
        ]

    def _liste(self) -> tuple[Ereignis, ...]:
        lage = self.coordinator.data
        return ereignisse(
            lage.termine,
            lage.eigene_tage,
            regionale=lage.regionale_feiertage,
            feiertage_im_kalender=lage.feiertage_im_kalender,
        )


def _event(eintrag: Ereignis) -> CalendarEvent:
    return CalendarEvent(
        start=eintrag.start,
        end=eintrag.ende,
        summary=eintrag.name,
        description=eintrag.beschreibung,
        uid=eintrag.uid,
    )


def _schneidet(eintrag: Ereignis, start: datetime, ende: datetime) -> bool:
    anfang = datetime.combine(eintrag.start, time.min, tzinfo=BERLIN)
    abschluss = datetime.combine(eintrag.ende, time.min, tzinfo=BERLIN)
    return anfang < ende and abschluss > start
