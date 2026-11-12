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

## Fehler

- `unavailable` oder `unknown` heißt: für dieses Datum liegen keine Termine im Cache. Das ist kein Schultag. Liegt das Datum vor dem Bestand oder hinter `daten_bis`, ist das der Grund. Eine Reparatur erscheint, wenn der Bestand in weniger als 60 Tagen endet.
- Zustände ändern sich um Mitternacht Europe/Berlin, ohne neuen Abruf. Automationen, die „morgen“ selbst ausrechnen, folgen der Zeitzone von Home Assistant. Die sollte Europe/Berlin sein.
- Nach einem Ausfall der API bleiben die letzten Daten stehen. Das ist so vorgesehen. Nach 14 Tagen ohne erfolgreichen Abruf erscheint eine Reparatur. `ferien.aktualisieren` holt sofort. `letzte_aktualisierung` und `datenstand` stehen bei den Diagnose-Sensoren.
- Die Einrichtung bleibt hängen, wenn beim ersten Start weder Netz noch Cache da sind. Es wird kein Eintrag mit leeren Zuständen angelegt. Netz herstellen und erneut versuchen.
- Ein eigener Tag wird über sein Startdatum ersetzt oder gelöscht. Ein späteres Datum im selben Zeitraum trifft ihn nicht.
- Nach einem Bundeslandwechsel behält die `entity_id` das alte Kürzel, bis sie umbenannt wird. Die Entität selbst zeigt das neue Land.

## Mitarbeit

Anweisungen: [AGENTS.md](AGENTS.md). Plan: [docs/plan.md](docs/plan.md), Roadmap: [docs/roadmap.md](docs/roadmap.md), CI/CD: [docs/ci-cd.md](docs/ci-cd.md).

## English

One config entry is one German state. The integration reports whether today and tomorrow are school-free, and why, plus the next holiday block, school-day countdowns and a calendar. Dates are calculated in Europe/Berlin. A missing dataset becomes `unavailable` or `unknown`, never “off”.

Data comes only from schulferienrechner.de. It is derived from the OpenHolidays API under ODbL 1.0 and is not an official source.

Download runs once a day between 03:00 and 05:00 local time. At midnight Europe/Berlin the states are recomputed locally. If the API fails, the cached data stays. A repair issue appears after 14 days without a successful download, or when the data ends within 60 days.

Reconfigure keeps the entities. The `entity_id` keeps the previous state code until you rename it. Removing the entry deletes its entities, custom days and cache.

`unavailable` or `unknown` means the cache has no data for that date. It does not mean school is in session. The first setup waits instead of creating an entry when there is neither network nor cache. `ferien.aktualisieren` fetches immediately. Custom days are replaced and removed by their start date. Automations that compute “tomorrow” use Home Assistant’s time zone, which should be Europe/Berlin.

The integration is not published yet.

## Lizenz

Code: MIT, siehe [LICENSE](LICENSE).
