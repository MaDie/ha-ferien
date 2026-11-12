"""Actions der Integration. Registriert einmal beim Laden, nicht je Eintrag."""

from __future__ import annotations

import logging
from datetime import date
from typing import cast

import probatio
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    ConfigEntrySelector,
    ConfigEntrySelectorConfig,
)

from .const import (
    DOMAIN,
    NAME_MAX_LAENGE,
    SERVICE_AKTUALISIEREN,
    SERVICE_SCHULTAG_PRUEFEN,
    SERVICE_TAG_ENTFERNEN,
    SERVICE_TAG_HINZUFUEGEN,
    SERVICE_TERMINE_ABRUFEN,
)
from .coordinator import FerienCoordinator, FerienRuntime
from .logic import EigenerTag, im_datenbereich, tag_bild, tag_ersetzen, tag_loeschen

_LOGGER = logging.getLogger(__name__)


def _eintrag() -> ConfigEntrySelector:
    return ConfigEntrySelector(ConfigEntrySelectorConfig(integration=DOMAIN))


def _typen(wert: object) -> list[str]:
    if isinstance(wert, str):
        return [wert]
    if isinstance(wert, list) and all(isinstance(eintrag, str) for eintrag in wert):
        return wert
    raise probatio.Invalid("Typen müssen Texte sein")


async def async_setup_services(hass: HomeAssistant) -> None:
    """Actions registrieren. Ein zweiter Aufruf ändert nichts."""
    if hass.services.has_service(DOMAIN, SERVICE_TAG_HINZUFUEGEN):
        return
    hass.services.async_register(
        DOMAIN,
        SERVICE_TAG_HINZUFUEGEN,
        _tag_hinzufuegen,
        schema=probatio.Schema(
            {
                probatio.Required("config_entry_id"): _eintrag(),
                probatio.Required("start"): cv.date,
                probatio.Optional("ende"): cv.date,
                probatio.Required("name"): cv.string,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_TAG_ENTFERNEN,
        _tag_entfernen,
        schema=probatio.Schema(
            {
                probatio.Required("config_entry_id"): _eintrag(),
                probatio.Required("start"): cv.date,
            }
        ),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_TERMINE_ABRUFEN,
        _termine_abrufen,
        schema=probatio.Schema(
            {
                probatio.Required("config_entry_id"): _eintrag(),
                probatio.Required("von"): cv.date,
                probatio.Required("bis"): cv.date,
                probatio.Optional("typen"): _typen,
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SCHULTAG_PRUEFEN,
        _schultag_pruefen,
        schema=probatio.Schema(
            {
                probatio.Required("config_entry_id"): _eintrag(),
                probatio.Required("datum"): cv.date,
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_AKTUALISIEREN,
        _aktualisieren,
        schema=probatio.Schema({probatio.Optional("config_entry_id"): _eintrag()}),
    )


async def _tag_hinzufuegen(call: ServiceCall) -> None:
    coordinator = _coordinator(call.hass, str(call.data["config_entry_id"]))
    start = _als_datum(call.data["start"])
    ende = _als_datum(call.data["ende"]) if "ende" in call.data else start
    name = str(call.data["name"]).strip()
    if not name or len(name) > NAME_MAX_LAENGE:
        raise _fehler("name_ungueltig")
    if ende < start:
        raise _fehler("zeitraum_ungueltig")
    try:
        tag = EigenerTag(start=start, ende=ende, name=name)
    except ValueError as err:
        raise _fehler("zeitraum_ungueltig") from err
    await coordinator.async_tage_setzen(tag_ersetzen(coordinator.eigene_tage, tag))


async def _tag_entfernen(call: ServiceCall) -> None:
    coordinator = _coordinator(call.hass, str(call.data["config_entry_id"]))
    start = _als_datum(call.data["start"])
    neu = tag_loeschen(coordinator.eigene_tage, start)
    if neu is None:
        raise _fehler("tag_unbekannt", {"start": start.isoformat()})
    await coordinator.async_tage_setzen(neu)


async def _termine_abrufen(call: ServiceCall) -> ServiceResponse:
    coordinator = _coordinator(call.hass, str(call.data["config_entry_id"]))
    von = _als_datum(call.data["von"])
    bis = _als_datum(call.data["bis"])
    if bis < von:
        raise _fehler("zeitraum_ungueltig")
    termine = coordinator.data.termine
    if not im_datenbereich(von, termine) or not im_datenbereich(bis, termine):
        raise _fehler(
            "zeitraum_ohne_daten",
            {"von": von.isoformat(), "bis": bis.isoformat()},
        )
    typen = call.data.get("typen")
    erlaubt = {str(typ) for typ in typen} if isinstance(typen, list) else None
    eintraege: list[dict[str, str]] = []
    for zeitraum in (*termine.ferien, *termine.schulfrei):
        if erlaubt is not None and zeitraum.typ not in erlaubt:
            continue
        if zeitraum.ende < von or zeitraum.start > bis:
            continue
        eintraege.append(
            {
                "id": zeitraum.id,
                "name": zeitraum.name,
                "typ": zeitraum.typ,
                "start": zeitraum.start.isoformat(),
                "ende": zeitraum.ende.isoformat(),
                "frei_von": zeitraum.frei_von.isoformat(),
                "frei_bis": zeitraum.frei_bis.isoformat(),
            }
        )
    for feiertag in termine.feiertage:
        if erlaubt is not None and "feiertag" not in erlaubt:
            continue
        if not (von <= feiertag.datum <= bis):
            continue
        if not feiertag.sichtbar(coordinator.data.regionale_feiertage):
            continue
        eintraege.append(
            {
                "id": f"feiertag-{feiertag.datum.isoformat()}",
                "name": feiertag.name,
                "typ": "feiertag",
                "start": feiertag.datum.isoformat(),
                "ende": feiertag.datum.isoformat(),
                "frei_von": feiertag.datum.isoformat(),
                "frei_bis": feiertag.datum.isoformat(),
            }
        )
    for tag in coordinator.eigene_tage:
        if erlaubt is not None and "eigener_tag" not in erlaubt:
            continue
        if tag.ende < von or tag.start > bis:
            continue
        eintraege.append(
            {
                "id": f"eigen-{tag.start.isoformat()}",
                "name": tag.name,
                "typ": "eigener_tag",
                "start": tag.start.isoformat(),
                "ende": tag.ende.isoformat(),
                "frei_von": tag.start.isoformat(),
                "frei_bis": tag.ende.isoformat(),
            }
        )
    return cast(ServiceResponse, {"termine": eintraege})


async def _schultag_pruefen(call: ServiceCall) -> ServiceResponse:
    coordinator = _coordinator(call.hass, str(call.data["config_entry_id"]))
    datum = _als_datum(call.data["datum"])
    lage = coordinator.data
    bild = tag_bild(
        datum,
        lage.termine,
        lage.eigene_tage,
        regionale=lage.regionale_feiertage,
    )
    if bild.schulfrei is None:
        raise _fehler("datum_ohne_daten", {"datum": datum.isoformat()})
    return {
        "schulfrei": bild.schulfrei,
        "grund": bild.grund.value if bild.grund is not None else None,
        "name": bild.name,
    }


async def _aktualisieren(call: ServiceCall) -> None:
    eintrag_id = call.data.get("config_entry_id")
    if isinstance(eintrag_id, str):
        coordinators = [_coordinator(call.hass, eintrag_id)]
    else:
        coordinators = [
            entry.runtime_data.coordinator
            for entry in call.hass.config_entries.async_entries(DOMAIN)
            if entry.runtime_data is not None
        ]
    if not coordinators:
        raise _fehler("eintrag_fehlt")
    fehler = 0
    for coordinator in coordinators:
        if not await coordinator.async_aktualisieren():
            fehler += 1
            _LOGGER.warning(
                "Aktualisieren für %s fehlgeschlagen: %s",
                coordinator.land_code,
                coordinator.letzter_fehler,
            )
    if fehler:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="abruf_fehlgeschlagen",
            translation_placeholders={"anzahl": str(fehler)},
        )


def _coordinator(hass: HomeAssistant, entry_id: str) -> FerienCoordinator:
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise _fehler("eintrag_fehlt")
    runtime = getattr(entry, "runtime_data", None)
    if not isinstance(runtime, FerienRuntime):
        raise _fehler("eintrag_nicht_bereit")
    return runtime.coordinator


def _als_datum(wert: object) -> date:
    if isinstance(wert, date):
        return wert
    raise _fehler("datum_ungueltig")


def _fehler(
    key: str,
    placeholders: dict[str, str] | None = None,
) -> ServiceValidationError:
    return ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key=key,
        translation_placeholders=placeholders,
    )
