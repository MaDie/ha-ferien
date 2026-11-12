"""Config Flow, Reconfigure und Optionen."""

from __future__ import annotations

from datetime import date
from typing import Any

import probatio
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    DateSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .api import ApiError, FerienClient, RateLimited
from .const import (
    API_BASE_URL,
    CONF_FEIERTAGE_IM_KALENDER,
    CONF_LAND,
    CONF_REGIONALE_FEIERTAGE,
    DEFAULT_FEIERTAGE_IM_KALENDER,
    DEFAULT_REGIONALE_FEIERTAGE,
    DOMAIN,
    LAENDER,
    NAME_MAX_LAENGE,
    land_name,
)
from .coordinator import FerienRuntime
from .logic import EigenerTag, tag_ersetzen, tag_loeschen
from .store import FerienStore


class FerienConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ein Bundesland pro Eintrag."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Options-Flow für diesen Eintrag."""
        if config_entry.domain != DOMAIN:
            msg = "falsche Domain"
            raise ValueError(msg)
        return FerienOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Bundesland wählen und die API einmal prüfen."""
        if user_input is not None:
            code = str(user_input[CONF_LAND])
            await self.async_set_unique_id(code)
            self._abort_if_unique_id_configured()
            fehler = await self._verbindung(code)
            if fehler is None:
                return self.async_create_entry(
                    title=_titel(code),
                    data={CONF_LAND: code},
                )
            return self.async_show_form(
                step_id="user",
                data_schema=self._land_schema(code),
                errors={"base": fehler},
            )
        vorschlag = await self._region()
        return self.async_show_form(
            step_id="user",
            data_schema=self._land_schema(vorschlag),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Land wechseln. Entitäten und ihre IDs bleiben am Eintrag."""
        eintrag = self._get_reconfigure_entry()
        aktuell = str(eintrag.data[CONF_LAND])
        if user_input is None:
            return self.async_show_form(
                step_id="reconfigure",
                data_schema=self._land_schema(aktuell),
                description_placeholders={
                    "kuerzel": aktuell.lower(),
                    "land": land_name(aktuell),
                },
            )
        code = str(user_input[CONF_LAND])
        if code != aktuell:
            belegt = await self.async_set_unique_id(code)
            if belegt is not None and belegt.entry_id != eintrag.entry_id:
                return self.async_abort(reason="already_configured")
            fehler = await self._verbindung(code)
            if fehler is not None:
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=self._land_schema(code),
                    errors={"base": fehler},
                    description_placeholders={
                        "kuerzel": aktuell.lower(),
                        "land": land_name(aktuell),
                    },
                )
        return self.async_update_reload_and_abort(
            eintrag,
            unique_id=code,
            title=_titel(code),
            data={CONF_LAND: code},
            reload_even_if_entry_is_unchanged=False,
        )

    async def _region(self) -> str | None:
        client = self._client()
        return await client.async_region()

    async def _verbindung(self, code: str) -> str | None:
        try:
            await self._client().async_termine(code, None)
        except RateLimited:
            return "cannot_connect"
        except ApiError as err:
            if err.status is None:
                return "cannot_connect"
            return "unknown"
        return None

    def _client(self) -> FerienClient:
        return FerienClient(
            async_get_clientsession(self.hass),
            basis_url=API_BASE_URL,
        )

    @staticmethod
    def _land_schema(vorschlag: str | None) -> probatio.Schema:
        feld: dict[Any, Any] = {probatio.Required(CONF_LAND): _land_selector()}
        if vorschlag in {code for code, *_rest in LAENDER}:
            feld = {probatio.Required(CONF_LAND, default=vorschlag): _land_selector()}
        return probatio.Schema(feld)


class FerienOptionsFlow(OptionsFlowWithReload):
    """Feiertagsoptionen und eigene Tage."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Menü."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["einstellungen", "tag_hinzufuegen", "tag_entfernen"],
        )

    async def async_step_einstellungen(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Schalter für Feiertage."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        optionen = self.config_entry.options
        return self.async_show_form(
            step_id="einstellungen",
            data_schema=probatio.Schema(
                {
                    probatio.Required(
                        CONF_FEIERTAGE_IM_KALENDER,
                        default=optionen.get(
                            CONF_FEIERTAGE_IM_KALENDER,
                            DEFAULT_FEIERTAGE_IM_KALENDER,
                        ),
                    ): BooleanSelector(),
                    probatio.Required(
                        CONF_REGIONALE_FEIERTAGE,
                        default=optionen.get(
                            CONF_REGIONALE_FEIERTAGE,
                            DEFAULT_REGIONALE_FEIERTAGE,
                        ),
                    ): BooleanSelector(),
                }
            ),
        )

    async def async_step_tag_hinzufuegen(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Eigenen Tag oder Zeitraum speichern."""
        errors: dict[str, str] = {}
        if user_input is not None:
            start = _datum(user_input.get("start"))
            name = str(user_input.get("name", "")).strip()
            if start is None:
                errors["start"] = "datum_ungueltig"
            else:
                ende = _datum(user_input.get("ende")) or start
                if ende < start:
                    errors["ende"] = "zeitraum_ungueltig"
                elif not name or len(name) > NAME_MAX_LAENGE:
                    errors["name"] = "name_ungueltig"
                else:
                    try:
                        tag = EigenerTag(start=start, ende=ende, name=name)
                    except ValueError:
                        errors["ende"] = "zeitraum_ungueltig"
                    else:
                        tage = tag_ersetzen(await self._tage(), tag)
                        await self._tage_schreiben(tage)
                        return self.async_abort(reason="tag_gespeichert")
        return self.async_show_form(
            step_id="tag_hinzufuegen",
            data_schema=probatio.Schema(
                {
                    probatio.Required("start"): DateSelector(),
                    probatio.Optional("ende"): DateSelector(),
                    probatio.Required("name"): TextSelector(),
                }
            ),
            errors=errors or None,
        )

    async def async_step_tag_entfernen(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Eigenen Tag anhand des Startdatums löschen."""
        tage = await self._tage()
        if not tage:
            return self.async_abort(reason="keine_eigenen_tage")
        if user_input is not None:
            start = _datum(user_input.get("start"))
            if start is None:
                return self.async_show_form(
                    step_id="tag_entfernen",
                    data_schema=_entfern_schema(tage),
                    errors={"start": "datum_ungueltig"},
                )
            neu = tag_loeschen(tage, start)
            if neu is None:
                return self.async_show_form(
                    step_id="tag_entfernen",
                    data_schema=_entfern_schema(tage),
                    errors={"start": "tag_unbekannt"},
                )
            await self._tage_schreiben(neu)
            return self.async_abort(reason="tag_gespeichert")
        return self.async_show_form(
            step_id="tag_entfernen",
            data_schema=_entfern_schema(tage),
        )

    async def _tage(self) -> tuple[EigenerTag, ...]:
        runtime = _runtime(self.config_entry)
        if runtime is not None:
            return runtime.coordinator.eigene_tage
        return await FerienStore(
            self.hass, self.config_entry.entry_id
        ).async_lade_tage()

    async def _tage_schreiben(self, tage: tuple[EigenerTag, ...]) -> None:
        runtime = _runtime(self.config_entry)
        if runtime is not None:
            await runtime.coordinator.async_tage_setzen(tage)
            return
        store = FerienStore(self.hass, self.config_entry.entry_id)
        await store.async_speichere_tage(tage)
        self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)


def _runtime(entry: ConfigEntry) -> FerienRuntime | None:
    runtime = getattr(entry, "runtime_data", None)
    if isinstance(runtime, FerienRuntime):
        return runtime
    return None


def _titel(code: str) -> str:
    return f"Ferien {land_name(code)}"


def _land_selector() -> SelectSelector:
    optionen: list[SelectOptionDict] = [
        {"value": code, "label": name} for code, name, _iso, _slug in LAENDER
    ]
    return SelectSelector(
        SelectSelectorConfig(options=optionen, mode=SelectSelectorMode.DROPDOWN)
    )


def _datum(wert: object) -> date | None:
    if type(wert) is date:
        return wert
    if isinstance(wert, str):
        try:
            return date.fromisoformat(wert)
        except ValueError:
            return None
    return None


def _entfern_schema(tage: tuple[EigenerTag, ...]) -> probatio.Schema:
    optionen: list[SelectOptionDict] = [
        {
            "value": tag.start.isoformat(),
            "label": f"{tag.name} ({tag.start.isoformat()})",
        }
        for tag in tage
    ]
    return probatio.Schema(
        {
            probatio.Required("start"): SelectSelector(
                SelectSelectorConfig(options=optionen, mode=SelectSelectorMode.DROPDOWN)
            )
        }
    )
