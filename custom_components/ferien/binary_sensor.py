"""Binärsensoren für heute und morgen."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import FerienConfigEntry, FerienCoordinator, Lage
from .entity import FerienEntity
from .logic import TagBild, tag_bild

PARALLEL_UPDATES = 0

_Feld = Literal["schulfrei", "ferien", "feiertag"]


@dataclass(frozen=True, slots=True)
class _Spec:
    key: str
    feld: _Feld
    morgen: bool


_SPECS = (
    _Spec("schulfrei_heute", "schulfrei", False),
    _Spec("schulfrei_morgen", "schulfrei", True),
    _Spec("ferien_heute", "ferien", False),
    _Spec("ferien_morgen", "ferien", True),
    _Spec("feiertag_heute", "feiertag", False),
    _Spec("feiertag_morgen", "feiertag", True),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FerienConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Binärsensoren anlegen."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(FerienBinarySensor(coordinator, spec) for spec in _SPECS)


class FerienBinarySensor(FerienEntity, BinarySensorEntity):
    """Ein Zustand für einen Tag. `unavailable`, wenn er nicht belegt ist."""

    def __init__(self, coordinator: FerienCoordinator, spec: _Spec) -> None:
        """Spec merken."""
        super().__init__(coordinator, spec.key, "binary_sensor")
        self._spec = spec

    @property
    def available(self) -> bool:
        """Aus, nur wenn der Cache den Tag wirklich kennt."""
        return super().available and self._wert() is not None

    @property
    def is_on(self) -> bool:
        """Wahr, wenn der Tag aus dem genannten Grund frei ist."""
        return self._wert() is True

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Grund und Namen, ohne leere Felder."""
        bild = self._bild()
        if bild is None or self._wert() is not True:
            return None
        if self._spec.feld == "schulfrei":
            attribute: dict[str, str] = {}
            if bild.grund is not None:
                attribute["grund"] = bild.grund.value
            if bild.name is not None:
                attribute["name"] = bild.name
            return attribute or None
        if (
            self._spec.feld == "ferien"
            and bild.ferien_name is not None
            and bild.ferien_start is not None
            and bild.ferien_ende is not None
        ):
            return {
                "name": bild.ferien_name,
                "start": bild.ferien_start.isoformat(),
                "ende": bild.ferien_ende.isoformat(),
            }
        if self._spec.feld == "feiertag" and bild.feiertag_name is not None:
            return {"name": bild.feiertag_name}
        return None

    def _wert(self) -> bool | None:
        bild = self._bild()
        if bild is None:
            return None
        if self._spec.feld == "schulfrei":
            return bild.schulfrei
        if self._spec.feld == "ferien":
            return bild.ferien
        return bild.feiertag

    def _bild(self) -> TagBild | None:
        if not self.coordinator.last_update_success:
            return None
        lage = self.coordinator.data
        tag = lage.heute + timedelta(days=1) if self._spec.morgen else lage.heute
        return _bewerten(lage, tag)


def _bewerten(lage: Lage, tag: date) -> TagBild:
    return tag_bild(
        tag,
        lage.termine,
        lage.eigene_tage,
        regionale=lage.regionale_feiertage,
    )
