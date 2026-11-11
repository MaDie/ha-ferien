# Ferien – Schulferien & Feiertage

Home-Assistant-Integration für Schulferien, schulfreie Tage und Feiertage aller 16 Bundesländer.

**Status: in Planung.** Es gibt noch keinen Code und keine installierbare Version.

## Geplant

- Ist heute/morgen schulfrei? Mit Grund (Wochenende, Ferien, Feiertag, schulfreier Tag, eigener Tag)
- Ferien und Feiertage als getrennte Sensoren
- Kalender-Entität mit Ferien, schulfreien Tagen und Feiertagen
- Nächste Ferien, Tage und Schultage bis dahin, letzter, erster und nächster Schultag
- Eigene bewegliche Ferientage über die Oberfläche
- Mehrere Bundesländer gleichzeitig
- Funktioniert bei Ausfall der Datenquelle über ein Jahr weiter (lokaler Cache)

Installation später über HACS (Custom Repository, danach Standardliste).

## Daten

Quelle ist [schulferienrechner.de](https://schulferienrechner.de). Die Termine stammen von der [OpenHolidays API](https://www.openholidaysapi.org) und stehen unter der [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/). Keine amtliche Quelle; verbindlich sind die Angaben der Kultusministerien.

## Mitarbeit

Anweisungen für Entwickler und Coding-Agents: [AGENTS.md](AGENTS.md). Plan: [docs/plan.md](docs/plan.md), Roadmap: [docs/roadmap.md](docs/roadmap.md), CI/CD: [docs/ci-cd.md](docs/ci-cd.md).

## Lizenz

Code: MIT, siehe [LICENSE](LICENSE).
