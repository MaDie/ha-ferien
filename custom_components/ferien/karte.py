"""Lovelace-Karte: heute Schule oder frei, darunter morgen."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import EVENT_COMPONENT_LOADED
from homeassistant.core import Event, HomeAssistant, callback

from .const import DOMAIN

KARTE_URL = "/ferien/ferien-karte.js"
_DATEI = Path(__file__).parent / "www" / "ferien-karte.js"
_BEREITS = f"{DOMAIN}_karte"


async def async_karte_registrieren(hass: HomeAssistant) -> None:
    """JS ausliefern und laden, sobald das Frontend da ist."""
    if hass.data.get(_BEREITS):
        return
    http = getattr(hass, "http", None)
    if http is None:
        return
    hass.data[_BEREITS] = True
    await http.async_register_static_paths(
        [StaticPathConfig(KARTE_URL, str(_DATEI), False)]
    )
    if "frontend" in hass.config.components:
        add_extra_js_url(hass, KARTE_URL)

    @callback
    def _wenn_geladen(event: Event) -> None:
        if event.data.get("component") != "frontend":
            return
        if "frontend" not in hass.config.components:
            return
        add_extra_js_url(hass, KARTE_URL)

    hass.bus.async_listen(EVENT_COMPONENT_LOADED, _wenn_geladen)
