# AGENTS.md – ha-ferien

Verbindliche Anweisungen für Coding-Agents (Cursor Agent, Cloud Agents) und Menschen. Bei Widerspruch gilt diese Datei vor `docs/plan.md`. Hintergrund und Quellen: `docs/plan.md`. Pipeline: `docs/ci-cd.md`. Reihenfolge: `docs/roadmap.md`.

## Feste Regeln

- **Niemals xhigh effort und niemals fast mode verwenden** (weder selbst noch bei Subagents oder Cloud Agents).
- Texte (README, UI-Strings, Changelog, Commits) kurz und konkret. Keine Werbe- oder KI-Floskeln („nahtlos“, „leistungsstark“, „revolutionär“, „Entdecke …“, Emojis).
- Status: **in Planung**. Code erst schreiben, wenn eine Aufgabe das ausdrücklich verlangt. Reihenfolge laut `docs/roadmap.md`.

## Ziel

Custom Integration für Home Assistant: Schulferien, schulfreie Tage und Feiertage aller 16 Bundesländer, mit Heute/Morgen-Status, Kalender, Countdowns und eigenen beweglichen Ferientagen. Einzige Datenquelle: API von schulferienrechner.de.

| | |
|---|---|
| Domain | `ferien` (fest, nie ändern) |
| Anzeigename | `Ferien – Schulferien & Feiertage` |
| Sprache | Python (Version wie von der Ziel-HA-Version gefordert) |
| Ziel-HA-Versionen | aktuelle stabile + vorherige Minor-Version (z. B. 2026.11 und 2026.10). `homeassistant` in `hacs.json` = älteste unterstützte Version |
| Verteilung | HACS Custom Repository, später HACS-Default |
| Lizenz Code | MIT |
| Daten | OpenHolidays API, ODbL 1.0, aufbereitet von schulferienrechner.de |

## Repo-Struktur

```
custom_components/ferien/
  __init__.py          Setup/Unload eines Eintrags, Coordinator starten, Actions registrieren
  manifest.json        domain, name, version, config_flow: true, iot_class: cloud_polling, integration_type: service, codeowners, documentation, issue_tracker, requirements: []
  const.py             DOMAIN, Länderliste, Defaults, API-Basis-URL, Schlüssel
  api.py               API-Client (aiohttp), nur HTTP + Parsing in Dataclasses, keine HA-Logik
  logic.py             reine Datumslogik (schulfrei, Schultage, Zähler), ohne HA-Imports testbar
  coordinator.py       DataUpdateCoordinator: Abruf, ETag, Store-Cache, Mitternachtswechsel
  config_flow.py       ConfigFlow + OptionsFlow + Reconfigure
  binary_sensor.py
  sensor.py
  calendar.py
  services.py          Action-Handler
  services.yaml
  diagnostics.py
  repairs.py
  strings.json
  icons.json
  translations/de.json
  translations/en.json
  quality_scale.yaml
  brand/icon.png
tests/
  conftest.py
  fixtures/            JSON-Antworten der API (siehe API-Vertrag)
  test_*.py
blueprints/automation/ferien/
hacs.json              {"name": "Ferien – Schulferien & Feiertage", "country": ["DE"], "render_readme": true, "homeassistant": "<älteste Version>"}
pyproject.toml         ruff, mypy, pytest
requirements_test.txt
.github/workflows/     ci.yml, release.yml, nightly.yml (Spezifikation: docs/ci-cd.md)
.github/dependabot.yml
```

## Einträge und Config Flow

- **Ein Config-Eintrag = ein Bundesland.** Mehrere Länder = mehrere Einträge. `unique_id` des Eintrags = Ländercode (`BY`), doppelte Einträge abbrechen (`already_configured`).
- Schritt `user`: Auswahl Bundesland (Selector, 16 Länder). Vorbelegung über `GET https://schulferienrechner.de/api/region`; schlägt das fehl, keine Vorbelegung, kein Fehler.
- Titel des Eintrags: `Ferien <Land>` (z. B. „Ferien Bayern“). Ein Gerät pro Eintrag, `entry_type: service`.
- **Reconfigure**: Land wechseln ohne Löschen. Entitäten und ihre IDs bleiben erhalten, damit Automationen weiterlaufen; nur die Daten und die `unique_id` des Eintrags wechseln. Die `entity_id` behält das alte Länderkürzel, bis der Nutzer sie umbenennt (im Dialog darauf hinweisen).
- **Optionen** (OptionsFlow):
  - `feiertage_im_kalender` (bool, Default `true`)
  - `regionale_feiertage` (bool, Default `false`; z. B. Augsburger Friedensfest, Fronleichnam in Teilen von SN/TH)
  - `eigene_tage`: Liste anzeigen, hinzufügen, löschen (Datum oder Zeitraum + Name)
- Keine YAML-Konfiguration.

## Entitäten

Alle Entitäten: `has_entity_name = True`, `translation_key` gesetzt, **feste `unique_id` = `<entry_id>_<key>`** (überlebt Reconfigure). Die `entity_id` wird beim Anlegen sprachunabhängig auf `<plattform>.ferien_<land_klein>_<key>` gesetzt (z. B. `binary_sensor.ferien_by_schulfrei_heute`), nicht aus dem übersetzten Namen abgeleitet. Die Anzeige-Namen kommen aus den Übersetzungen. Vor Umsetzung prüfen, welcher Weg in der Ziel-HA-Version dafür vorgesehen ist, und das Ergebnis im Test absichern.

States sind nie `Ja`/`Nein`-Strings. Datumssensoren nutzen `SensorDeviceClass.DATE`, Tageszähler `native_unit_of_measurement = UnitOfTime.DAYS`.

### binary_sensor
| key | an, wenn | Attribute |
|---|---|---|
| `schulfrei_heute` / `schulfrei_morgen` | Wochenende, Ferien, Feiertag, schulfreier Tag oder eigener Tag | `grund` (`wochenende`/`ferien`/`feiertag`/`schulfrei`/`eigener_tag`), `name` |
| `ferien_heute` / `ferien_morgen` | Datum liegt in Ferien (`start`–`ende`) | `name`, `start`, `ende` |
| `feiertag_heute` / `feiertag_morgen` | gesetzlicher Feiertag im Land | `name` |

### sensor
| key | Typ | Attribute |
|---|---|---|
| `naechste_ferien` | Datum (Start) | `name`, `start`, `ende`, `frei_von`, `frei_bis` |
| `letzter_schultag` | Datum (vor den nächsten Ferien) | |
| `erster_schultag` | Datum (nach den aktuellen/nächsten Ferien) | |
| `naechster_schultag` | Datum (ab morgen) | |
| `naechster_feiertag` | Datum | `name` |
| `tage_bis_ferien` | Tage (Kalendertage bis `frei_von`) | |
| `schultage_bis_ferien` | Tage (Schultage ohne heute) | |
| `ferientage_verbleibend` | Tage (in laufenden Ferien inkl. heute bis `frei_bis`, sonst 0) | |
| `datenstand` | Zeitstempel, `EntityCategory.DIAGNOSTIC` | |
| `letzte_aktualisierung` | Zeitstempel, Diagnose | |
| `daten_bis` | Datum, Diagnose | |

### calendar
Eine Entität `calendar.ferien_<land>`: Ferien, schulfreie Tage, eigene Tage, Feiertage (abschaltbar per Option). Ganztägige Events, `end` exklusiv nach HA-Konvention (API liefert `ende` inklusiv, umrechnen!). `uid` = API-`id`.

### Actions (`services.yaml`, Antwort per `SupportsResponse`)
| Action | Felder | Wirkung |
|---|---|---|
| `ferien.tag_hinzufuegen` | `config_entry_id`, `start`, `ende` (optional), `name` | eigener schulfreier Tag/Zeitraum, persistent |
| `ferien.tag_entfernen` | `config_entry_id`, `start` | entfernt eigenen Tag |
| `ferien.termine_abrufen` | `config_entry_id`, `von`, `bis`, `typen` (optional) | gibt Liste zurück (`SupportsResponse.ONLY`) |
| `ferien.schultag_pruefen` | `config_entry_id`, `datum` | gibt `{schulfrei, grund, name}` zurück |
| `ferien.aktualisieren` | `config_entry_id` (optional) | sofortiger Abruf |

Eigene Tage liegen im HA-`Store` (`.storage/ferien.<entry_id>`), **nie** in Dateien im Integrationsordner.

## Daten, Update, Cache

- Abruf: `GET /api/v1/laender/{code}/termine` einmal täglich, Zeitpunkt pro Installation zufällig zwischen 03:00 und 05:00 Ortszeit (`async_track_time_change` mit zufälliger Minute, beim Setup festgelegt). `If-None-Match` mit gespeichertem ETag; `304` = nur Zeitstempel aktualisieren.
- Beim Start: zuerst Cache laden. Netzabruf nur, wenn der Cache fehlt oder älter als 24 h ist.
- **Cache**: gesamte Antwort (mindestens 12 Monate in die Zukunft) im HA-`Store` speichern, versioniert (`STORAGE_VERSION`), mit `etag`, `syncedAt`, `abgerufen_am`.
- **Mitternacht**: um 00:00:00 Europe/Berlin alle Zustände lokal neu berechnen (`async_track_time_change`), ohne Netz. Kein Neustart nötig.
- **Ausfall**: API-Fehler (Timeout, 5xx, 429, ungültiges JSON) → alten Cache weiterverwenden, Fehler loggen (einmal, nicht bei jedem Versuch), `Retry-After` beachten.
  - Für ein Datum ohne Daten im Cache: Entität `unavailable` bzw. State `unknown`. **Niemals „keine Ferien“/`off` als Ersatz.**
  - Erster Start ohne Cache und ohne Netz: `ConfigEntryNotReady`.
- **Repairs**: Issue, wenn 14 Tage kein erfolgreicher Abruf, oder die Daten in weniger als 60 Tagen enden.
- `User-Agent`: `ha-ferien/<version> (+https://github.com/MaDie/ha-ferien)`.
- Zeitzone für alle Datumsberechnungen: Europe/Berlin (`dt_util`), nicht die Systemzeit.

## API-Vertrag (schulferienrechner.de, `/api/v1`)

**Die API existiert noch nicht.** Sie wird zuerst in `MaDie/schulferienrechner.de` gebaut (Roadmap M0). Bis dahin gegen Fixtures in `tests/fixtures/` entwickeln, die exakt diesem Vertrag folgen. Maßgeblich ist später `https://schulferienrechner.de/api/v1/openapi.json`; weicht sie ab, gilt die OpenAPI-Datei und diese Datei wird angepasst.

Allgemein: nur `GET`, JSON UTF-8, Datumsangaben ISO `YYYY-MM-DD`, `ende` **inklusiv**, Zeitzone Europe/Berlin. Ländercode als Kürzel (`BY`) oder Slug (`bayern`). Jede Antwort enthält `quelle`, `lizenz`, `datenstand`. Header: `ETag`, `Last-Modified`, `Cache-Control`; `304` bei `If-None-Match`; `429` mit `Retry-After`. Kein API-Key. In `v1` kommen nur Felder hinzu; unbekannte Felder ignorieren.

| Endpunkt | Nutzung in der Integration |
|---|---|
| `/api/v1/meta` | Version, `syncedAt`, Abdeckung je Land (Diagnostics) |
| `/api/v1/laender` | Länderliste (Fallback: Liste in `const.py`) |
| `/api/v1/laender/{code}/ferien?schuljahr=2026-27` bzw. `?von=&bis=` | nicht benötigt |
| `/api/v1/laender/{code}/feiertage?jahr=2027` | nicht benötigt |
| `/api/v1/laender/{code}/termine` | **Hauptabruf** |
| `/api/v1/laender/{code}/status?datum=` | nur im Vertragstest, Logik rechnet die Integration selbst |
| `/api/v1/status?datum=` | nicht benötigt |
| `/api/v1/export.json`, `/api/v1/openapi.json` | Vertragstest |
| `/api/region` (bestehend) | Vorbelegung im Config Flow |

Fehlerformat: `{"fehler": {"code": "unbekanntes_land", "meldung": "…"}}` mit 400/404.

Erwartetes Format von `/termine` (Fixture-Vorlage):

```json
{
  "land": {"code": "BY", "iso": "DE-BY", "slug": "bayern", "name": "Bayern"},
  "von": "2026-08-01",
  "bis": "2028-12-31",
  "ferien": [
    {"id": "by-herbstferien-2026-11-02", "name": "Herbstferien", "typ": "herbstferien",
     "start": "2026-11-02", "ende": "2026-11-06", "frei_von": "2026-10-31", "frei_bis": "2026-11-08",
     "bestaetigt": true, "hinweis": null}
  ],
  "schulfrei": [
    {"id": "by-schulfrei-2026-11-18", "name": "Buß- und Bettag", "typ": "schulfrei",
     "start": "2026-11-18", "ende": "2026-11-18", "frei_von": "2026-11-18", "frei_bis": "2026-11-18",
     "bestaetigt": true, "hinweis": null}
  ],
  "feiertage": [
    {"name": "Neujahr", "datum": "2027-01-01", "bundesweit": true, "teilweise": false, "lokal": false, "hinweis": null}
  ],
  "quelle": "OpenHolidays API, aufbereitet von schulferienrechner.de",
  "lizenz": "ODbL-1.0",
  "datenstand": "2026-11-11T03:00:00+01:00"
}
```

`typ` ∈ `herbstferien`, `weihnachtsferien`, `winterferien`, `osterferien`, `pfingstferien`, `sommerferien`, `schulfrei` (Liste offen, unbekannte Werte als generische Ferien behandeln). Feiertage mit `teilweise` oder `lokal` = `true` nur bei Option `regionale_feiertage`.

## Coding-Regeln

- Alles `async`. Keine blockierenden Aufrufe im Event-Loop (kein `requests`, kein `time.sleep`, kein synchrones Datei-I/O; falls nötig `hass.async_add_executor_job`).
- HTTP nur über `aiohttp` mit `async_get_clientsession(hass)`; Session in `api.py` injizieren, nie selbst erzeugen. Timeout 30 s.
- Keine zusätzlichen PyPI-Abhängigkeiten (`requirements: []`). Datumslogik selbst in `logic.py`.
- Vollständige Typannotationen, `mypy --strict` für `custom_components/ferien`. `from __future__ import annotations`.
- `ruff check` und `ruff format` ohne Befund. Zeilenlänge 88.
- Runtime-Daten in `entry.runtime_data` (typisiert, `type FerienConfigEntry = ConfigEntry[FerienData]`), nicht in `hass.data`.
- Entitäten erben von `CoordinatorEntity`; keine eigenen Polls pro Entität.
- Logging: `_LOGGER = logging.getLogger(__name__)`, keine Daten-Dumps auf `info`.
- Alle Nutzertexte in `strings.json`/`translations/` (de + en). Keine hartcodierten Strings in Python.
- Quality Scale: **Bronze** für v0.1, **Gold** als Ziel (Diagnostics, Repairs, Reconfigure, Übersetzungen, Icons, Entity-Kategorien). Status in `quality_scale.yaml` pflegen (`done`/`todo`/`exempt` mit Begründung). Platinum nur, wenn strict typing und injizierte Session erfüllt sind.

## Tests

- `pytest` + `pytest-homeassistant-custom-component` (Version passend zur Ziel-HA-Version), `pytest-asyncio`, `freezegun` über `freezer`-Fixture.
- API immer gemockt (`aioclient_mock`), nie echte Netzaufrufe in Unit-Tests.
- `logic.py` mit reinen Unit-Tests ohne HA.
- Pflichtfälle:
  1. Config Flow: Erfolg, Vorbelegung über `/api/region`, `/api/region` fehlschlägt, doppeltes Land abgebrochen, API beim Setup nicht erreichbar, Reconfigure, OptionsFlow.
  2. Sensoren: alle Entitäten für einen Ferientag, einen Schultag, Freitag vor Ferien, Wochenende vor erstem Schultag, Feiertag, schulfreien Einzeltag, eigenen Tag.
  3. Mitternacht: Zeit auf 23:59:59 setzen, vorspulen, Zustände wechseln ohne neuen API-Aufruf.
  4. API-Ausfall: Timeout, 500, 429 mit `Retry-After`, ungültiges JSON → alte Daten bleiben, kein `off`; ohne Daten → `unavailable`/`unknown`.
  5. Cache: Start mit Cache ohne Netz funktioniert; Cache < 24 h → kein Abruf; ETag → `304` verarbeitet.
  6. Actions: Tag hinzufügen/entfernen bleibt nach Neustart erhalten; `termine_abrufen`, `schultag_pruefen` liefern Antwort.
  7. Entity-IDs: identisch bei HA-Sprache `de` und `en`.
  8. Diagnostics: Snapshot ohne sensible Daten.
- Abdeckung `custom_components/ferien` mindestens 95 % (Pflicht für Gold).

## Definition of Done (pro Änderung)

- `ruff check`, `ruff format --check`, `mypy`, `pytest` lokal grün; CI grün (ci.yml).
- Neue Logik hat Tests; Pflichtfälle oben weiterhin abgedeckt.
- `strings.json` und beide Übersetzungen aktualisiert.
- `quality_scale.yaml` angepasst, falls Regeln betroffen.
- README und `CHANGELOG.md` (Abschnitt `Unreleased`) aktualisiert, wenn sich Verhalten für Nutzer ändert.
- Keine Änderung an Domain, `unique_id`-Schema oder Entity-Keys ohne Migration (`async_migrate_entry`).

## Release

1. `CHANGELOG.md`: `Unreleased` → `vX.Y.Z – JJJJ-MM-TT`.
2. `version` in `manifest.json` auf `X.Y.Z` setzen, PR mergen.
3. Tag `vX.Y.Z` auf `main` pushen. `release.yml` prüft Tag = `manifest.json`-Version und erstellt das GitHub-Release mit Changelog-Abschnitt.
4. SemVer: Bruch an Entitäten/Actions = Major (vor 1.0: Minor). Vorabversionen `vX.Y.Z-beta.N` als Pre-Release.

## Verboten

- Domain `ferien`, `unique_id`-Schema oder Entity-Keys ohne Migration ändern.
- „Keine Ferien“/`off` als Ersatzwert bei fehlenden Daten.
- Direkte Abrufe von OpenHolidays, ferien-api.de oder anderen Dritt-APIs. Einzige Quelle ist schulferienrechner.de.
- Dateien im Integrationsordner zur Laufzeit schreiben; YAML-Konfiguration.
- Blockierende I/O im Event-Loop, eigene `aiohttp.ClientSession`, `requests`.
- Neue Laufzeit-Abhängigkeiten ohne Rückfrage.
- Secrets, Tokens oder persönliche Daten im Repo, in Fixtures oder Diagnostics.
- Repo öffentlich schalten, HACS-Default-PR stellen, in Foren posten oder Releases veröffentlichen ohne ausdrückliche Freigabe von Matthias.
- Force-Push auf `main`.
- KI-Floskeln in README, UI-Texten, Changelog.
