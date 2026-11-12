"""Gemeinsame Basis der Entitäten."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_LAND, DOMAIN, KALENDER_KEY, VERSION, land_name
from .coordinator import FerienCoordinator


class FerienEntity(CoordinatorEntity[FerienCoordinator]):
    """Entität mit stabilem unique_id und sprachunabhängiger entity_id."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FerienCoordinator,
        key: str,
        plattform: str,
    ) -> None:
        """Identität aus Eintrag und Schlüssel setzen."""
        super().__init__(coordinator)
        self._key = key
        entry = coordinator.entry
        code = str(entry.data[CONF_LAND]).lower()
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_translation_key = key
        object_id = f"ferien_{code}" if key == KALENDER_KEY else f"ferien_{code}_{key}"
        self.entity_id = f"{plattform}.{object_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="schulferienrechner.de",
            model=land_name(str(entry.data[CONF_LAND])),
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://schulferienrechner.de",
            sw_version=VERSION,
        )
