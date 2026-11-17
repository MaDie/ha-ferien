"""Registrierung der Lovelace-Karte."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

from homeassistant.const import EVENT_COMPONENT_LOADED
from homeassistant.core import HomeAssistant

from custom_components.ferien.karte import KARTE_URL, async_karte_registrieren


async def test_karte_ohne_http_ist_still(hass: HomeAssistant) -> None:
    """Ohne HTTP-Server bleibt die Registrierung aus."""
    hass.http = None  # type: ignore[assignment]
    await async_karte_registrieren(hass)


async def test_karte_sofort_wenn_frontend_da(hass: HomeAssistant) -> None:
    """Steht das Frontend schon, wird das Modul direkt eingetragen."""
    hass.config.components.add("frontend")
    http = Mock()
    http.async_register_static_paths = AsyncMock()
    hass.http = http
    with patch("custom_components.ferien.karte.add_extra_js_url") as extra:
        await async_karte_registrieren(hass)
        await async_karte_registrieren(hass)
    extra.assert_called_once_with(hass, KARTE_URL)
    http.async_register_static_paths.assert_awaited_once()
    konfig = http.async_register_static_paths.await_args.args[0][0]
    assert konfig.url_path == KARTE_URL
    assert konfig.path.endswith("ferien-karte.js")
    assert konfig.cache_headers is False


async def test_karte_wartet_auf_frontend(hass: HomeAssistant) -> None:
    """Kommt das Frontend später, wird das Modul erst dann eingetragen."""
    if "frontend" in hass.config.components:
        hass.config.components.remove("frontend")
    http = Mock()
    http.async_register_static_paths = AsyncMock()
    hass.http = http
    with patch("custom_components.ferien.karte.add_extra_js_url") as extra:
        await async_karte_registrieren(hass)
        extra.assert_not_called()
        hass.bus.async_fire(EVENT_COMPONENT_LOADED, {"component": "http"})
        await hass.async_block_till_done()
        extra.assert_not_called()
        hass.bus.async_fire(EVENT_COMPONENT_LOADED, {"component": "frontend"})
        await hass.async_block_till_done()
        extra.assert_not_called()
        hass.config.components.add("frontend")
        hass.bus.async_fire(EVENT_COMPONENT_LOADED, {"component": "frontend"})
        await hass.async_block_till_done()
    extra.assert_called_once_with(hass, KARTE_URL)
