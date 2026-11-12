"""Datums- und Zählersensoren."""

from __future__ import annotations

from datetime import date, datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DIAGNOSE_KEYS
from .coordinator import FerienConfigEntry, FerienCoordinator, Lage
from .entity import FerienEntity
from .logic import (
    erster_schultag,
    ferientage_verbleibend,
    im_datenbereich,
    letzter_schultag,
    naechste_ferien,
    naechster_feiertag,
    naechster_schultag,
    schultage_bis_ferien,
    tage_bis_ferien,
)

PARALLEL_UPDATES = 0

_DATUM = (
    "naechste_ferien",
    "letzter_schultag",
    "erster_schultag",
    "naechster_schultag",
    "naechster_feiertag",
    "daten_bis",
)
_ZAEHLER = (
    "tage_bis_ferien",
    "schultage_bis_ferien",
    "ferientage_verbleibend",
)
_ZEIT = ("datenstand", "letzte_aktualisierung")
_KEYS = (*_DATUM, *_ZAEHLER, *_ZEIT)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FerienConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Sensoren anlegen."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(FerienSensor(coordinator, key) for key in _KEYS)


class FerienSensor(FerienEntity, SensorEntity):
    """Ein Datum, eine Anzahl Tage oder ein Diagnose-Zeitstempel."""

    def __init__(self, coordinator: FerienCoordinator, key: str) -> None:
        """Gerät, Einheit und Kategorie aus dem Schlüssel ableiten."""
        super().__init__(coordinator, key, "sensor")
        if key in _ZAEHLER:
            self._attr_native_unit_of_measurement = UnitOfTime.DAYS
        elif key in _ZEIT:
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif key in _DATUM:
            self._attr_device_class = SensorDeviceClass.DATE
        if key in DIAGNOSE_KEYS:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def available(self) -> bool:
        """Diagnose bleibt da. Übrige Sensoren nur, solange heute abgedeckt ist."""
        if not super().available:
            return False
        if self._key in DIAGNOSE_KEYS:
            return True
        lage = self.coordinator.data
        return im_datenbereich(lage.heute, lage.termine)

    @property
    def native_value(self) -> date | datetime | int | None:
        """Wert des Sensors. `None` wird in HA zu `unknown`."""
        return _wert(self.coordinator.data, self._key)

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Zeitraum der nächsten Ferien."""
        if self._key != "naechste_ferien":
            return None
        lage = self.coordinator.data
        periode = naechste_ferien(lage.heute, lage.termine)
        if periode is None:
            return None
        return {
            "name": periode.name,
            "start": periode.start.isoformat(),
            "ende": periode.ende.isoformat(),
            "frei_von": periode.frei_von.isoformat(),
            "frei_bis": periode.frei_bis.isoformat(),
        }


def _wert(lage: Lage, key: str) -> date | datetime | int | None:
    regionale = lage.regionale_feiertage
    eigene = lage.eigene_tage
    termine = lage.termine
    heute = lage.heute
    if key == "naechste_ferien":
        periode = naechste_ferien(heute, termine)
        return periode.start if periode else None
    if key == "letzter_schultag":
        return letzter_schultag(heute, termine, eigene, regionale=regionale)
    if key == "erster_schultag":
        return erster_schultag(heute, termine, eigene, regionale=regionale)
    if key == "naechster_schultag":
        return naechster_schultag(heute, termine, eigene, regionale=regionale)
    if key == "naechster_feiertag":
        feiertag = naechster_feiertag(heute, termine, regionale=regionale)
        return feiertag.datum if feiertag else None
    if key == "tage_bis_ferien":
        return tage_bis_ferien(heute, termine)
    if key == "schultage_bis_ferien":
        return schultage_bis_ferien(heute, termine, eigene, regionale=regionale)
    if key == "ferientage_verbleibend":
        return ferientage_verbleibend(heute, termine)
    if key == "datenstand":
        return termine.datenstand
    if key == "letzte_aktualisierung":
        return lage.abgerufen_am
    if key == "daten_bis":
        return termine.bis
    return None
