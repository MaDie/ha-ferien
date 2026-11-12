# Ferien – Schulferien & Feiertage

Home-Assistant-Integration für Schulferien, schulfreie Tage und Feiertage der 16 Bundesländer.

Ein Eintrag ist ein Bundesland. Weitere Länder sind weitere Einträge.

## Installation

Die Integration ist noch nicht veröffentlicht. Veröffentlichung und HACS-Eintrag erst nach Freigabe.

Bis dahin lokal nach `config/custom_components/ferien` kopieren und Home Assistant neu starten. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** „Ferien“ wählen.

Unterstützt werden die aktuelle stabile Home-Assistant-Version und die vorherige Minor-Version. `hacs.json` nennt die älteste.

## Was sie meldet

- Schulfrei heute und morgen, mit Grund: Wochenende, Ferien, Feiertag, schulfreier Tag oder eigener Tag
- Ferien und Feiertage getrennt, jeweils heute und morgen
- Nächste Ferien, Tage und Schultage bis dahin, verbleibende Ferientage
- Letzter, erster und nächster Schultag, nächster Feiertag
- Kalender mit Ferien, schulfreien Tagen, eigenen Tagen und, abschaltbar, Feiertagen
- Diagnose: Datenstand, letzte Aktualisierung, Daten bis

Fehlt für ein Datum der Datenbestand, wird die Entität `unavailable` oder `unknown`. Sie wird nicht auf „aus“ gesetzt.

## Daten und Aktualisierung

Einzige Quelle ist [schulferienrechner.de](https://schulferienrechner.de), Endpunkt `/api/v1`. Die Termine stammen von der [OpenHolidays API](https://www.openholidaysapi.org) und stehen unter der [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Keine amtliche Quelle. Verbindlich sind die Angaben der Kultusministerien.

Der Abruf läuft einmal täglich zwischen 03:00 und 05:00 Ortszeit. Um Mitternacht Europe/Berlin werden die Zustände neu gerechnet, ohne Netz. Liegt ein Cache vor, bleibt er bei einem Ausfall der API liegen. Eine Reparatur erscheint, wenn 14 Tage kein Abruf geklappt hat oder die Daten in weniger als 60 Tagen enden.

## Optionen

- Feiertage im Kalender, Standard an
- Regionale Feiertage, Standard aus (zum Beispiel Augsburger Friedensfest)
- Eigene Tage: Datum oder Zeitraum mit Namen, auch über die Actions `ferien.tag_hinzufuegen` und `ferien.tag_entfernen`

Ein Bundeslandwechsel über „Neu konfigurieren“ behält die Entitäten. Die `entity_id` enthält das alte Länderkürzel, bis sie umbenannt wird.

## Actions

- `ferien.tag_hinzufuegen`, `ferien.tag_entfernen`
- `ferien.termine_abrufen`, `ferien.schultag_pruefen` (Antwort)
- `ferien.aktualisieren`

## Blueprints

Unter `blueprints/automation/ferien`:

- Schulwecker: Uhrzeit, nur wenn heute Schule ist
- Ranzen-Erinnerung: Vorabend, wenn morgen der erste Schultag ist
- Rollläden: morgens öffnen, nur an Schultagen

Die Zeitzone von Home Assistant sollte Europe/Berlin sein.

## Entfernen

Eintrag löschen. Damit verschwinden Entitäten, eigene Tage und der Cache dieses Eintrags.

## Grenzen

- Ein Eintrag je Bundesland, keine Kombination mehrerer Länder
- Berufliche Schulen sind nicht enthalten
- Die API unter `/api/v1` wird noch aufgebaut. Bis sie da ist, entwickelt die Integration gegen die Fixtures in `tests/fixtures/`

## Mitarbeit

Anweisungen: [AGENTS.md](AGENTS.md). Plan: [docs/plan.md](docs/plan.md), Roadmap: [docs/roadmap.md](docs/roadmap.md), CI/CD: [docs/ci-cd.md](docs/ci-cd.md).

## English

One config entry is one German state. The integration reports whether today and tomorrow are school-free, and why, plus the next holiday block, school-day countdowns and a calendar. Dates are calculated in Europe/Berlin. A missing dataset becomes `unavailable` or `unknown`, never “off”.

Data comes only from schulferienrechner.de. It is derived from the OpenHolidays API under ODbL 1.0 and is not an official source.

Download runs once a day between 03:00 and 05:00 local time. At midnight Europe/Berlin the states are recomputed locally. If the API fails, the cached data stays. A repair issue appears after 14 days without a successful download, or when the data ends within 60 days.

Reconfigure keeps the entities. The `entity_id` keeps the previous state code until you rename it. Removing the entry deletes its entities, custom days and cache.

The integration is not published yet.

## Lizenz

Code: MIT, siehe [LICENSE](LICENSE).
