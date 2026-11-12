"""Repair-Hinweise, wenn der Cache alt wird oder ausläuft."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import (
    DOMAIN,
    ISSUE_ABRUF_VERALTET,
    ISSUE_DATEN_ENDEN,
    REPAIR_DATEN_ENDE_TAGE,
    REPAIR_OHNE_ABRUF_TAGE,
)
from .logic import BERLIN


def async_sync_issues(
    hass: HomeAssistant,
    *,
    entry_id: str,
    letzter_erfolg: datetime | None,
    daten_bis: date,
    land_name: str,
    heute: date,
) -> None:
    """Issues anlegen oder schließen. Aufgerufen nach Abruf und um Mitternacht."""
    async_sync_abruf(
        hass,
        entry_id=entry_id,
        letzter_erfolg=letzter_erfolg,
        land_name=land_name,
        heute=heute,
    )
    async_sync_horizont(
        hass,
        entry_id=entry_id,
        daten_bis=daten_bis,
        land_name=land_name,
        heute=heute,
    )


def async_clear_issues(hass: HomeAssistant, entry_id: str) -> None:
    """Issues dieses Eintrags entfernen."""
    ir.async_delete_issue(hass, DOMAIN, _abruf_id(entry_id))
    ir.async_delete_issue(hass, DOMAIN, _horizont_id(entry_id))


def async_sync_abruf(
    hass: HomeAssistant,
    *,
    entry_id: str,
    letzter_erfolg: datetime | None,
    land_name: str,
    heute: date,
) -> None:
    """Issue, wenn 14 Tage kein erfolgreicher Abruf war."""
    issue_id = _abruf_id(entry_id)
    if letzter_erfolg is None:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    tage = (heute - letzter_erfolg.astimezone(BERLIN).date()).days
    if tage < REPAIR_OHNE_ABRUF_TAGE:
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_ABRUF_VERALTET,
        translation_placeholders={"land": land_name, "tage": str(tage)},
        config_entry_id=entry_id,
    )


def async_sync_horizont(
    hass: HomeAssistant,
    *,
    entry_id: str,
    daten_bis: date,
    land_name: str,
    heute: date,
) -> None:
    """Issue, wenn die Daten in weniger als 60 Tagen enden."""
    issue_id = _horizont_id(entry_id)
    if daten_bis >= heute + timedelta(days=REPAIR_DATEN_ENDE_TAGE):
        ir.async_delete_issue(hass, DOMAIN, issue_id)
        return
    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_DATEN_ENDEN,
        translation_placeholders={"land": land_name, "bis": daten_bis.isoformat()},
        config_entry_id=entry_id,
    )


def _abruf_id(entry_id: str) -> str:
    return f"{ISSUE_ABRUF_VERALTET}_{entry_id}"


def _horizont_id(entry_id: str) -> str:
    return f"{ISSUE_DATEN_ENDEN}_{entry_id}"
