# Home-Assistant-Integration „Ferien“ – Plan

Stand: 11.11.2026. Datenquelle: schulferienrechner.de (intern OpenHolidays API, ODbL 1.0).

## 1. Vorhandene Integrationen

| Integration | Domain | Quelle | Entitäten | Optionen | Wartung (11.11.2026) | Probleme |
|---|---|---|---|---|---|---|
| [Chiralistic/home-assistant-schulferien](https://github.com/Chiralistic/home-assistant-schulferien) „Schulferien“, **HACS-Default** | `schulferien` | OpenHolidays | `sensor` Schulferien heute/morgen, `sensor` Feiertag, 6 `binary_sensor` (Ferien+Feiertag, nur Ferien, nur Feiertag, je heute/morgen) | Land, Region (auch AT/CH); Brückentage per Datei `bridge_days.yaml` im Integrationsordner, Neustart nötig | 12 Sterne, v1.2.3 vom 02.09.2026, letzter Push 08.11.2026, 1 offenes Issue | [#35](https://github.com/Chiralistic/home-assistant-schulferien/issues/35): Bei Timeout falscher Fallback-Pfad (404) und Zustand „kein Ferientag“ statt „unbekannt“. [#33](https://github.com/Chiralistic/home-assistant-schulferien/issues/33): Wechsel um Mitternacht kam erst nach Neustart. [#24](https://github.com/Chiralistic/home-assistant-schulferien/issues/24): Mehrere Bundesländer erst nachträglich, mit inkompatibel geänderten Entity-IDs |
| [Jo-Highness/school_holidays](https://github.com/Jo-Highness/school_holidays) „School Holidays“, **HACS-Default** | `school_holidays` | OpenHolidays (alle Länder) | `binary_sensor` heute/morgen, `sensor` nächste Ferien (date, `days_until`), Diagnose-Zeitstempel | Land, Region, Intervall, Sprache; Reconfigure | 0 Sterne, v1.1.0 vom 16.10.2026, 0 Issues; Diagnostics, Repair-Hinweis nach 7 Tagen ohne Update, Cache bei Ausfall | Keine Feiertage, kein Kalender (README empfiehlt den Umweg über Local Calendar), keine schulfreien Einzeltage, Entity-IDs hängen von der HA-Sprache ab |
| [workFLOw42/ha-deutsche-ferien](https://github.com/workFLOw42/ha-deutsche-ferien) „Deutsche Schulferien & Feiertage“ (nur Custom Repo) | `deutsche_ferien` | OpenHolidays (bis v1.x ferien-api.de + Nager) | 6 `sensor` (heute schulfrei „Ja/Nein“, aktuelle/nächste Ferien, Tage bis Ferien, nächster Feiertag, Übersicht), `button` Aktualisieren | Bundesland, nationale/regionale Feiertage | 2 Sterne, v2.5.0 vom 15.09.2026 | Kein `binary_sensor`, kein Morgen-Status, kein Kalender; schreibt YAML-Datei ins Config-Verzeichnis |
| [M4RKU5-C0D3/HASH](https://github.com/M4RKU5-C0D3/HASH) „School Holidays“ | `school_holidays` (Konflikt mit Jo-Highness) | OpenHolidays | `calendar`, `binary_sensor` aktiv, `sensor` nächste Ferien (`days_until_start`, `days_remaining`) | Bundesland | 1 Stern, nur v0.1.0 (23.08.2026) | Kein Morgen-Status, keine Feiertage |
| [PowderK/openholidays-ha](https://github.com/PowderK/openholidays-ha) | `openholidays` | OpenHolidays | `binary_sensor` heute, `sensor` Name, `sensor` Zeitraum | Land, Region | 0 Sterne, v1.0.0 (11.04.2026), seitdem inaktiv | Minimal |
| [HazardDede/home-assistant-ferienapidotde](https://github.com/HazardDede/home-assistant-ferienapidotde) | `ferienapidotde` | ferien-api.de | 1 `binary_sensor`, YAML-Konfiguration, `days_offset` | Bundesland, Offset | Letztes Release 10/2022, 7 offene Issues | **Tot**: [#15](https://github.com/HazardDede/home-assistant-ferienapidotde/issues/15) (02/2026: Winterferien BB/BE nicht erkannt, Nutzer wechseln zu „Schulferien“), [#10](https://github.com/HazardDede/home-assistant-ferienapidotde/issues/10) (Quelle nicht erreichbar) |
| [Melle79/HA-schulferien_feiertage](https://github.com/Melle79/HA-schulferien_feiertage) (Add-on, kein HACS) | – (MQTT) | OpenHolidays, Fallback ferien-api.de/feiertage-api.de/Nager | `binary_sensor` heute/morgen schulfrei (inkl. Wochenende), Feiertag heute/morgen, `sensor` nächste Ferien/Feiertag | Mehrere Regionen, Unterregionen (Augsburg), Fallback-API | v1.5.2 (04.09.2026) | Nur mit Supervisor + MQTT-Broker; „kein Support“ laut README |
| [nickl3ss/werktage](https://github.com/nickl3ss/werktage) „Werktage“ | `werktage` | OpenHolidays oder eigener Kalender | Pro Person/Raum/Haus: Morgen-/Abend-Sensor, `binary_sensor`, `calendar` | Rolle Schüler/Erwachsener, Ausnahmen pro Tag, Wochenmuster | v0.3.0 (20.10.2026), 0 Sterne | Anderer Fokus (Haushaltsplanung), komplex |
| HA-Core [Workday](https://www.home-assistant.io/integrations/workday/) + Bibliothek `holidays` | `workday` | Offline (`holidays` 0.108) | `binary_sensor` mit Offset, `calendar`, Action `workday.check_date` | „Additional category“ | Core | `holidays` hat seit [PR #3533](https://github.com/vacanza/holidays/pull/3533) (gemergt 03.05.2026, ab v0.96) die Kategorie `SCHOOL` für alle 16 Länder, generiert aus KMK-PDFs. Workday sollte damit Schulferien als freie Tage zählen können; **ungetestet**. Neue Termine kommen nur mit HA-Updates, Ferien sind nicht von Feiertagen unterscheidbar, kein Ferienname, kein Countdown. Ernstzunehmende Basis-Konkurrenz |
| Fremdthemen | – | – | – | – | – | [DomCim/HA-Schoolday](https://github.com/DomCim/HA-Schoolday) (Stundenplan/Routinen, HACS-Default), [VpMobile24](https://github.com/Maximilian-Andrew-Kluge/VpMobile24/) (Stundenplan24 mit Ferien-Sensor). Ohne eigene Ferien-API |

Do-it-yourself-Wege: REST-Sensor gegen OpenHolidays ([HA-Forum](https://community.home-assistant.io/t/rest-sensor-for-school-vacations-openholidaysapi/708850), [simon42](https://community.simon42.com/t/schulferien-per-rest-api-abrufen/36516)), ICS-Datei über `ics_calendar` oder manuell gepflegter Kalender ([simon42](https://community.simon42.com/t/automation-nur-ausserhalb-der-schulferien-ausfuehren-gibt-es-eine-passende-integration/33514)).

**Lücken bei allen:** Keine Integration bietet zusammen: Kalender-Entität, Morgen-Status, Feiertage, schulfreie Einzeltage und eigene bewegliche Ferientage über die Oberfläche. Es gibt keinen Schultage-Zähler, keinen „letzter/erster Schultag“, keinen „nächster Schultag“. Keine Integration verlängert Ferien über angrenzende Wochenenden: OpenHolidays führt z. B. die Herbstferien Bayern 2026 als 02.–06.11., frei ist aber 31.10.–08.11.

## 2. Was Nutzer vermissen (mit Quelle)

| Wunsch | Quelle |
|---|---|
| Status für **morgen** (Rollläden, Kinder dürfen länger aufbleiben) | [Chiralistic #20](https://github.com/Chiralistic/home-assistant-schulferien/issues/20), [HazardDede #3](https://github.com/HazardDede/home-assistant-ferienapidotde/issues/3) (Wunsch `days_offset`, Licht-aus-Erinnerung) |
| „Ist **morgen Schultag**?“: Bastelei mit Kalender, Workday und `calendar.get_events` | [simon42 #26024](https://community.simon42.com/t/abfragen-ob-am-naechsten-tag-kalender-event-ist-und-ob-kein-werktag-ist/26024) |
| Ferien und Feiertage als **getrennte** Binärsensoren | [Chiralistic #23](https://github.com/Chiralistic/home-assistant-schulferien/issues/23) |
| **Mehrere Bundesländer** (Wohnort an Landesgrenze) | [Chiralistic #24](https://github.com/Chiralistic/home-assistant-schulferien/issues/24) |
| **Bewegliche Ferientage** der Schule ergänzen | [HazardDede #13](https://github.com/HazardDede/home-assistant-ferienapidotde/issues/13) |
| Schulfreie **Einzeltage** (Buß- und Bettag Bayern) | [Chiralistic #22](https://github.com/Chiralistic/home-assistant-schulferien/issues/22) |
| Sich selbst aktualisierender **Ferienkalender** in HA | [HazardDede #10, Kommentar ecdlguy](https://github.com/HazardDede/home-assistant-ferienapidotde/issues/10); [werktage #14](https://github.com/nickl3ss/werktage/issues/14) |
| **Zuverlässigkeit**: Quelle tot, Ausfall ergibt falschen Zustand, Mitternachtswechsel | [HazardDede #15](https://github.com/HazardDede/home-assistant-ferienapidotde/issues/15), [#10](https://github.com/HazardDede/home-assistant-ferienapidotde/issues/10), [Chiralistic #35](https://github.com/Chiralistic/home-assistant-schulferien/issues/35), [#33](https://github.com/Chiralistic/home-assistant-schulferien/issues/33) |
| Lesbare Namen/Datumsformate | [HazardDede #4](https://github.com/HazardDede/home-assistant-ferienapidotde/issues/4) |
| Workday kennt keine Schulferien (bis 2026, siehe oben); Zeiträume statt Einzeldaten | [simon42 #33514](https://community.simon42.com/t/automation-nur-ausserhalb-der-schulferien-ausfuehren-gibt-es-eine-passende-integration/33514), [Reddit](https://www.reddit.com/r/homeassistant/comments/ysdrrl/how_to_define_school_holiday_periods_how_to/) |
| Kinder auf verschiedenen Schulen, Ferien-Wochentage getrennt vom Wochenende, nach Neustart korrekt | [hausbau-forum](https://www.hausbau-forum.de/threads/wie-lassen-sich-schulferien-in-home-assistant-automatisch-beruecksichtigen.n5y5q4/) (Thread wirkt generiert, nur schwacher Beleg) |

## 3. Eigene Analyse

**Typische Automationen und was sie brauchen**
- Wecker/Licht/Rollläden morgens: `schulfrei_heute`, kombiniert aus Wochenende, Ferien, Feiertag, schulfreiem Tag und eigenen Tagen, plus Grund als Attribut.
- Abendroutine, Handy-Ladezeit, Heizung für morgen: `schulfrei_morgen` und `naechster_schultag` (Datum). Am Freitagabend heißt das z. B. Montag oder erster Schultag nach den Ferien.
- Erinnerungen: letzter Schultag vor den Ferien (Zeugnis, Sportbeutel), Sonntag vor dem ersten Schultag (Ranzen, Wecker). Braucht `letzter_schultag` und `erster_schultag`.
- Countdown für Kinder-Dashboards: Kalendertage und **Schultage** bis zu den Ferien.
- Getrennt lebende Eltern oder Kinder in zwei Ländern: mehrere Einträge mit stabilen, eindeutigen IDs und optional einem Kombi-Sensor („irgendein Kind frei“ / „alle frei“).
- Eigene Tage: bewegliche Ferientage, pädagogische Tage, Streik, Hitzefrei. Per Action und Optionsdialog, gespeichert im HA-Store und nicht in Dateien im Integrationsordner (die gehen beim Update verloren).
- Kalender-Trigger (`event: start/end`, Offset) und Anzeige im HA-Kalender: `calendar`-Entität mit Ferien, schulfreien Tagen, eigenen Tagen und optional Feiertagen.

**Technik**
- Offline: Gesamten Datensatz (mindestens 12 Monate voraus) im `Store` cachen. Zustände um 00:00 Ortszeit lokal neu berechnen, ohne Netz. Bei API-Fehlern alten Datensatz weiterverwenden. `unavailable` nur, wenn für den Tag gar keine Daten vorliegen, **nie** stillschweigend „keine Ferien“ (Fehler aus Chiralistic #35).
- Repair-Issue, wenn 14 Tage kein Update kam oder die gecachten Daten in weniger als 60 Tagen enden.
- Config Flow: Bundesland-Auswahl, vorbelegt über `/api/region` (Cloudflare-Region der HA-IP, wird nicht gespeichert). Optionen: Feiertage im Kalender, regionale Feiertage (Augsburger Friedensfest, Fronleichnam teilweise), eigene Tage. Reconfigure für Länderwechsel ohne neue IDs.
- Diagnostics (Datenstand, ETag, Cache-Abdeckung, letzte Fehler), Entity-Kategorien, `device_class: date`/`duration`, keine Ja/Nein-Strings als State.
- Quality Scale: Bronze zum Start, Gold als Ziel (Diagnostics, Repairs, Reconfigure, Übersetzungen de/en, Icons). Platinum nur mit strikter Typisierung und injizierter aiohttp-Session.
- Entity-IDs sprachunabhängig halten (z. B. `binary_sensor.ferien_by_schulfrei_heute`), anders als bei Jo-Highness. Umsetzbarkeit mit `has_entity_name` prüfen.

## 4. API-Entwurf für schulferienrechner.de

**Ausgangslage im Repo** (`server.js`, `src/data.js`, `scripts/sync-holidays.js`):
- `/cal/<land>[-ferien|-feiertage|-alarm14d].ics` sowie `/api/health` und `/api/region` sind vorhanden. JSON-Endpunkte für Ferien gibt es keine.
- Daten liegen in `data/ferien/2026-27.json`, `2027-28.json` und `data/feiertage/2026–2028.json`, mit den Typen `herbstferien` … `schulfrei`, den Flags `confirmed`, `teilweise` und `local`, und Lizenzfeld `ODC-ODbL`.
- Berufliche Schulen und Ausnahmen werden beim Sync verworfen.
- **Vorher erweitern:** Der Sync deckt nur 2026-27/2027-28 ab. OpenHolidays liefert für BY bereits bis 2030. Künftig sollte er immer das laufende Schuljahr plus 2 weitere und Feiertage für 4 Jahre holen.

**Endpunkte** (alle `GET`, JSON UTF-8, Datumsangaben ISO, `ende` inklusiv, Zeitzone Europe/Berlin)

| Endpunkt | Inhalt |
|---|---|
| `/api/v1/meta` | API-Version, Datenstand (`syncedAt`), abgedeckte Schuljahre/Jahre je Land, Quelle, Lizenz |
| `/api/v1/laender` | 16 Länder: `code` (BY), `iso` (DE-BY), `slug`, `name` |
| `/api/v1/laender/{code}/ferien?schuljahr=2026-27` oder `?von=&bis=` | Ferien und schulfreie Tage: `id` (stabil, z. B. `by-herbstferien-2026-11-02`), `name`, `typ`, `start`, `ende`, `frei_von`/`frei_bis` (über Wochenende und Feiertage verlängert), `bestaetigt`, `hinweis` |
| `/api/v1/laender/{code}/feiertage?jahr=2027` | `name`, `datum`, `bundesweit`, `teilweise`, `lokal`, `hinweis` |
| `/api/v1/laender/{code}/termine` | **Paket für Home Assistant**: alle Ferien, schulfreien Tage und Feiertage im verfügbaren Zeitraum in einer Antwort (ein Abruf pro Tag und Eintrag) |
| `/api/v1/laender/{code}/status?datum=2026-11-11` | `heute`/`morgen` (`schulfrei`, `grund`: wochenende/ferien/feiertag/schulfrei), aktuelle Ferien, nächste Ferien, `tage_bis`, `schultage_bis`, `letzter_schultag`, `erster_schultag`, `naechster_schultag`, nächster Feiertag |
| `/api/v1/status?datum=` | Status aller 16 Länder („gerade Ferien in 7 Ländern“), auch nutzbar für Discord-Bot, TikTok-Posts und Startseite |
| `/api/v1/export.json` | Vollständiger abgeleiteter Datensatz (ODbL-Pflicht, siehe unten) |
| `/api/v1/openapi.json` + Seite `/api` | Doku |

Für Ländercodes werden Kürzel und Slugs akzeptiert, wie bei `findState()`. Fehler kommen als `{"fehler":{"code":"unbekanntes_land","meldung":"…"}}` mit 400/404. Jede Antwort enthält `quelle`, `lizenz` und `datenstand`.

**Caching**
- Daten-Endpunkte: `Cache-Control: public, max-age=3600, s-maxage=86400, stale-while-revalidate=86400, stale-if-error=604800`.
- `status`: `max-age` bis Mitternacht Berlin.
- `ETag` als Hash über Datenstand und Parameter, `Last-Modified` = `syncedAt`, `304` bei `If-None-Match`. Cloudflare cacht am Rand, der Node-Server sieht kaum Last.

**Limits und Schutz**
- Cloudflare-Rate-Limit-Regel auf `/api/` (z. B. 60 Anfragen/min je IP), dazu ein In-App-Token-Bucket als Rückfall. `429` mit `Retry-After`.
- Kein API-Key. Bitte um eigenen `User-Agent` (die Integration sendet `ha-ferien/<version> (+Repo-URL)`).
- `robots.txt` sperrt `/api/` bereits.

**CORS:** `Access-Control-Allow-Origin: *`, nur `GET`/`HEAD`/`OPTIONS`, keine Cookies.

**Lizenz:** OpenHolidays-Daten stehen unter [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) ([Daten-Repo](https://github.com/openpotato/openholidaysapi.data)). Die aufbereiteten Daten sind eine abgeleitete Datenbank. Bei öffentlicher Nutzung gilt laut ODbL (Ziffer 4.4/4.6, vor Start prüfen):
- Namensnennung („Daten: OpenHolidays API, ODbL 1.0“).
- Die abgeleitete Datenbank unter ODbL anbieten. Deshalb gibt es `export.json`, denn das Repo ist privat.
- Berechnete Werte (Schultage, Status) gelten als „Produced Work“ und brauchen nur die Quellenangabe.
- Hinweis „keine amtliche Quelle“.
- Der Code der Integration kann MIT oder Apache-2.0 sein.

**Stabilität**
- In `v1` kommen nur Felder hinzu, nichts wird umbenannt oder entfernt.
- Brüche nur über `/api/v2`. `v1` läuft danach mindestens 12 Monate weiter, mit `Deprecation`- und `Sunset`-Headern.
- Changelog auf `/api`.
- Tests gegen die OpenAPI-Datei in CI.

## 5. Integrations-Plan

**Name und Domain**
- Domain **`ferien`**. Sie ist frei: kein Core-Domain, kein Eintrag in der HACS-Default-Liste (5.165 Integrationen geprüft), nicht im Brands-Repo, kein GitHub-Code-Treffer.
- `schulferien` ist durch Chiralistic belegt (HACS-Default und Brands-Repo). Zwei Custom-Integrationen mit gleicher Domain lassen sich nicht parallel installieren, `school_holidays` ist sogar doppelt vergeben.
- Anzeigename: **„Ferien – Schulferien & Feiertage“**.
- So wird gesucht:
  - HA-Dialog „Integration hinzufügen“: unscharfe Suche über `name` und `domain`, beide mit Gewicht 5 ([Quellcode](https://github.com/home-assistant/frontend/blob/dev/src/panels/config/integrations/dialog-add-integration.ts)). „ferien“ trifft die Domain exakt und den Namen am Anfang. „schulferien“ und „feiertage“ treffen den Namen.
  - HACS: Volltext über Name, Beschreibung, Autoren, Domain, Repo-Name und **Topics** ([Quellcode](https://github.com/hacs/frontend/blob/main/src/dashboards/hacs-dashboard.ts)).
- Repo `MaDie/ha-ferien`, Beschreibung „Schulferien, Feiertage und schulfreie Tage aller 16 Bundesländer für Home Assistant“, Topics `ferien schulferien feiertage brueckentage school-holidays germany hacs-integration home-assistant`. `hacs.json` mit `"country": ["DE"]`.

**Entitäten pro Eintrag** (ein Eintrag = ein Bundesland, ein Gerät „Ferien Bayern“)
- `binary_sensor`: `schulfrei_heute`, `schulfrei_morgen` (Attribut `grund`, `name`), `ferien_heute`, `ferien_morgen`, `feiertag_heute`, `feiertag_morgen`
- `sensor` (Datum): `naechste_ferien` (Attribute `name`, `start`, `ende`, `frei_von`, `frei_bis`), `letzter_schultag`, `erster_schultag`, `naechster_schultag`, `naechster_feiertag`
- `sensor` (Zahl, Tage): `tage_bis_ferien`, `schultage_bis_ferien`, `ferientage_verbleibend`
- `calendar`: Ferien, schulfreie Tage, eigene Tage, optional Feiertage
- Diagnose: `datenstand`, `letzte_aktualisierung`, `daten_bis`
- Actions: `ferien.tag_hinzufuegen` / `ferien.tag_entfernen` (bewegliche Ferientage, persistent), `ferien.termine_abrufen` (Rückgabe der Liste), `ferien.schultag_pruefen` (Datum → Ergebnis), `ferien.aktualisieren`
- Später: Helfer-Eintrag „Kombination“ über mehrere Länder (beliebig/alle frei), `sensor` nächster Brückentag

**Update:** Täglich ein Abruf von `/termine` mit ETag, zufällig zwischen 03:00 und 05:00. Beim Start nur, wenn der Cache älter als 24 h ist. Um 00:00 Neuberechnung ohne Netz. Bei 10.000 Installationen sind das rund 10.000 meist mit `304` beantwortete Anfragen am Tag, über Cloudflare kein Thema.

**Veröffentlichung:**
1. Custom Repo in HACS mit My-Button.
2. HACS-Default-PR, Voraussetzungen ([Doku](https://www.hacs.xyz/docs/publish/include/)): HACS Action, Hassfest, Release, Lizenz, Topics, `brand/icon.png` im Integrationsordner (seit HA 2026.3 möglich, [Blog](https://contributors.home-assistant.io/blog/2026/02/24/brands-proxy-api/)). Die Prüfung dauert laut HACS Monate.
3. Core erst nach stabiler API und PyPI-Bibliothek (z. B. `ferien-api`) prüfen. Gegenargument: Workday kann mit `holidays` ≥ 0.96 bereits Schulferien.

**Repo-Struktur**
```
custom_components/ferien/
  __init__.py  manifest.json  const.py  api.py  coordinator.py  logic.py
  binary_sensor.py  sensor.py  calendar.py  services.py  services.yaml
  config_flow.py  diagnostics.py  repairs.py  strings.json  icons.json
  translations/{de,en}.json  brand/icon.png  quality_scale.yaml
tests/  blueprints/automation/ferien/  hacs.json  README.md (de+en)  LICENSE
.github/workflows/{hassfest,hacs,tests,release}.yml
```
`logic.py` enthält nur die reine Datumslogik (frei/Schultag/Zähler). Sie ist ohne HA testbar und kann später die PyPI-Bibliothek werden.

**Meilensteine**

| # | Inhalt | Aufwand |
|---|---|---|
| M0 | API v1 in schulferienrechner.de: Sync erweitern, Endpunkte, ETag/Cache, CORS, Rate-Limit, OpenAPI, `/api`-Seite, Tests | 2–3 Tage |
| M1 | Integration MVP: Config Flow, Cache/Coordinator, `schulfrei_*`/`ferien_*`, `naechste_ferien`, `calendar`, Custom Repo + Release 0.1 | 3–4 Tage |
| M2 | Eigene Tage (Optionen + Actions), Schultage-Zähler, letzter/erster/nächster Schultag, Feiertags-Sensoren, Diagnostics, Repairs, Reconfigure, en-Übersetzung, 3 Blueprints (Schulwecker, Ranzen-Erinnerung, Rollläden) | 3 Tage |
| M3 | Quality-Scale-Selbsteinstufung Gold, HACS-Default-PR, Ankündigung im HA-Forum und bei simon42 sowie Antworten in den Threads oben (vorher Matthias fragen) | 1 Tag + Wartezeit |
| M4 | Optional: Kombi-Helfer mehrerer Länder, Brückentage, berufliche Schulen (Sync müsste BBS-Daten behalten), Core-Prüfung | offen |

**Abgrenzung: was unsere besser macht**
1. Alles in einem: Kalender, heute/morgen, Ferien/Feiertag getrennt **und** kombiniert, schulfreie Einzeltage. Bisher braucht man dafür zwei Integrationen oder Templates.
2. „Nächster Schultag“, letzter/erster Schultag, Schultage bis zu den Ferien: keine andere Integration hat das.
3. Bewegliche Ferientage über Oberfläche und Action, update-sicher gespeichert. Bei Chiralistic läuft das über eine Datei mit Neustart, sonst gibt es das nirgends.
4. Echte freie Blöcke (`frei_von`/`frei_bis` über Wochenenden).
5. Robust: lokaler Cache für über 12 Monate, Mitternachtswechsel ohne Netz, nie „keine Ferien“ bei Ausfall, Repair-Hinweis.
6. Stabile, sprachunabhängige Entity-IDs. Mehrere Länder von Anfang an.
7. Gepflegte Datenquelle mit Versionsversprechen statt direkter Abhängigkeit von Dritt-APIs. Hinweis für Nutzer: Die Rohdaten stammen weiter aus OpenHolidays, der Mehrwert liegt in Aufbereitung, Typisierung, Plausibilitätsprüfung und Stabilität.

**Risiken**
- Workday plus `holidays` deckt die Grundfunktion offline ab. Unser Vorsprung liegt in den Punkten 1–5.
- Ausfall von schulferienrechner.de: Durch den Cache bleibt die Integration über ein Jahr korrekt.
- ODbL-Pflichten vor dem API-Start umsetzen.
