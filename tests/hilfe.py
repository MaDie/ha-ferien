"""Gemeinsame Helfer. Kein autouse von Home Assistant."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch

from homeassistant.core import HomeAssistant

try:
    from pytest_homeassistant.common import (
        MockConfigEntry,
        async_fire_time_changed_exact,
    )
    from pytest_homeassistant.test_util.aiohttp import AiohttpClientMocker
except ImportError:  # pragma: no cover - nur die CI-Matrix 2026.10
    from pytest_homeassistant_custom_component.common import (
        MockConfigEntry,
    )
    from pytest_homeassistant_custom_component.common import (
        async_fire_time_changed as async_fire_time_changed_exact,
    )
    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMocker,
    )

from custom_components.ferien.const import CONF_LAND, DOMAIN, land_name

FIXTURE = Path(__file__).parent / "fixtures" / "by_termine.json"
BASIS = "https://schulferienrechner.de"
ENTRY_ID = "ferien-by-test"


def lade_fixture() -> dict[str, Any]:
    """Vertrags-Fixture für Bayern."""
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        msg = "Fixture ist kein Objekt"
        raise RuntimeError(msg)
    return data


def termine_url(code: str) -> str:
    return f"{BASIS}/api/v1/laender/{code}/termine"


def mock_termine(
    aioclient_mock: AiohttpClientMocker,
    code: str = "BY",
    payload: dict[str, Any] | None = None,
    *,
    status: int = 200,
    etag: str | None = "by-1",
    exc: BaseException | None = None,
    content: bytes | None = None,
) -> None:
    """Einen Termine-Abruf vormerken."""
    kwargs: dict[str, Any] = {"status": status}
    if etag is not None:
        kwargs["headers"] = {"ETag": etag}
    if exc is not None:
        kwargs["exc"] = exc
    if content is not None:
        kwargs["content"] = content
    elif payload is not None:
        kwargs["json"] = payload
    elif exc is None and status == 200:
        kwargs["json"] = lade_fixture()
    aioclient_mock.get(termine_url(code), **kwargs)


def mock_region(
    aioclient_mock: AiohttpClientMocker,
    land: str | None = "DE-BY",
    *,
    status: int = 200,
    exc: BaseException | None = None,
) -> None:
    """`/api/region` vormerken."""
    kwargs: dict[str, Any] = {"status": status}
    if exc is not None:
        kwargs["exc"] = exc
    elif status == 200:
        kwargs["json"] = {"land": land}
    aioclient_mock.get(f"{BASIS}/api/region", **kwargs)


@contextmanager
def feste_abrufzeit():
    """Täglichen Abruf auf 03:17 legen, damit Diagnosen stabil bleiben."""
    with patch(
        "custom_components.ferien.coordinator.waehle_abrufzeit",
        return_value=(3, 17),
    ):
        yield


async def richte_ein(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    *,
    code: str = "BY",
    payload: dict[str, Any] | None = None,
    status: int = 200,
    exc: BaseException | None = None,
    content: bytes | None = None,
    etag: str | None = "by-1",
    entry_id: str = ENTRY_ID,
    sprache: str = "en",
    optionen: dict[str, Any] | None = None,
) -> MockConfigEntry:
    """Eintrag anlegen und laden. Die Uhr ist bereits eingefroren."""
    hass.config.language = sprache
    await hass.config.async_set_time_zone("Europe/Berlin")
    mock_termine(
        aioclient_mock,
        code,
        payload,
        status=status,
        etag=etag,
        exc=exc,
        content=content,
    )
    eintrag = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_LAND: code},
        unique_id=code,
        entry_id=entry_id,
        title=f"Ferien {land_name(code)}",
        version=1,
        options=optionen or {},
    )
    eintrag.add_to_hass(hass)
    with feste_abrufzeit():
        await hass.config_entries.async_setup(eintrag.entry_id)
        await hass.async_block_till_done()
    return eintrag


__all__ = [
    "ENTRY_ID",
    "async_fire_time_changed_exact",
    "feste_abrufzeit",
    "lade_fixture",
    "mock_region",
    "mock_termine",
    "richte_ein",
    "termine_url",
]
