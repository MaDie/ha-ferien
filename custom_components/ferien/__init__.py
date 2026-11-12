"""Ferien – Schulferien und Feiertage."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import FerienClient
from .const import API_BASE_URL, DOMAIN
from .coordinator import FerienConfigEntry, FerienCoordinator, FerienRuntime
from .repairs import async_clear_issues
from .services import async_setup_services
from .store import FerienStore

PLATFORMS: tuple[Platform, ...] = (
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.CALENDAR,
)

__all__ = ["DOMAIN", "async_remove_entry", "async_setup", "async_setup_entry"]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Actions einmalig registrieren."""
    await async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: FerienConfigEntry) -> bool:
    """Eintrag laden, Cache oder Netz, dann die Plattformen."""
    client = FerienClient(async_get_clientsession(hass), basis_url=API_BASE_URL)
    coordinator = FerienCoordinator(hass, entry, client)
    entry.runtime_data = FerienRuntime(coordinator)
    await coordinator.async_config_entry_first_refresh()
    coordinator.async_planen()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FerienConfigEntry) -> bool:
    """Plattformen entladen. Der Coordinator stoppt über den Eintrag."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: FerienConfigEntry) -> None:
    """Repairs und gespeicherte Daten des Eintrags entfernen."""
    async_clear_issues(hass, entry.entry_id)
    await FerienStore(hass, entry.entry_id).async_entfernen()
