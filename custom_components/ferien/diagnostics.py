"""Diagnose ohne den vollständigen Datenbestand."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.core import HomeAssistant

from .const import CONF_LAND
from .coordinator import FerienConfigEntry, FerienRuntime


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: FerienConfigEntry,
) -> dict[str, Any]:
    """Zustand des Eintrags, ohne Termine im Wortlaut."""
    basis: dict[str, Any] = {
        "land": entry.data.get(CONF_LAND),
        "optionen": dict(entry.options),
    }
    runtime = getattr(entry, "runtime_data", None)
    if not isinstance(runtime, FerienRuntime):
        basis["bereit"] = False
        return basis
    coordinator = runtime.coordinator
    basis["bereit"] = coordinator.last_update_success
    basis["etag"] = coordinator.etag
    basis["letzter_fehler"] = coordinator.letzter_fehler
    basis["letzter_erfolg"] = _zeit(coordinator.letzter_erfolg)
    basis["abruf"] = {
        "stunde": coordinator.abruf_stunde,
        "minute": coordinator.abruf_minute,
    }
    if not coordinator.last_update_success:
        return basis
    lage = coordinator.data
    termine = lage.termine
    basis["abgerufen_am"] = _zeit(lage.abgerufen_am)
    basis["von"] = termine.von.isoformat()
    basis["bis"] = termine.bis.isoformat()
    basis["datenstand"] = _zeit(termine.datenstand)
    basis["anzahl"] = {
        "ferien": len(termine.ferien),
        "schulfrei": len(termine.schulfrei),
        "feiertage": len(termine.feiertage),
        "eigene_tage": len(lage.eigene_tage),
    }
    basis["eigene_tage"] = [
        {
            "start": tag.start.isoformat(),
            "ende": tag.ende.isoformat(),
            "name": tag.name,
        }
        for tag in lage.eigene_tage
    ]
    return basis


def _zeit(wert: datetime | None) -> str | None:
    if wert is None:
        return None
    return wert.isoformat()
