# Roadmap

Reihenfolge ist verbindlich. Details: `docs/plan.md`, Regeln: `AGENTS.md`.

## M0 – API v1 in schulferienrechner.de (2–3 Tage, Repo `MaDie/schulferienrechner.de`)
- [ ] Sync erweitern: laufendes Schuljahr + 2 weitere, Feiertage für 4 Jahre
- [ ] `frei_von`/`frei_bis` (Ferien über Wochenenden und Feiertage verlängert) berechnen
- [ ] Endpunkte `/api/v1/meta`, `laender`, `laender/{code}/ferien`, `feiertage`, `termine`, `status`, `/api/v1/status`, `export.json`
- [ ] `ETag`, `Last-Modified`, `304`, `Cache-Control` laut Plan
- [ ] CORS, Cloudflare-Rate-Limit (60/min je IP), In-App-Token-Bucket, `429` mit `Retry-After`
- [ ] `openapi.json` und Doku-Seite `/api` mit Changelog
- [ ] ODbL: Namensnennung, `export.json` unter ODbL, Hinweis „keine amtliche Quelle“
- [ ] Schema-Check gegen `openapi.json` in der Website-Pipeline

## M1 – v0.1 als HACS Custom Repository (3–4 Tage)
- [ ] `pyproject.toml`, `requirements_test.txt`, Workflows laut `docs/ci-cd.md`
- [ ] Fixtures aus der echten API (oder vor M0 laut Vertrag in `AGENTS.md`)
- [ ] `api.py`, `logic.py`, `coordinator.py` mit Store-Cache, ETag, Mitternachtswechsel
- [ ] Config Flow (ein Eintrag je Bundesland, Vorbelegung über `/api/region`)
- [ ] `binary_sensor`: `schulfrei_*`, `ferien_*`, `feiertag_*`
- [ ] `sensor`: `naechste_ferien`, `tage_bis_ferien`, Diagnose-Sensoren
- [ ] `calendar`
- [ ] Übersetzungen de/en, `hacs.json`, `brand/icon.png`
- [ ] Pflichttests grün, Quality Scale Bronze
- [ ] Release v0.1.0 (nach Freigabe durch Matthias), Repo dafür öffentlich schalten (nach Freigabe)

## M2 – Extras (3 Tage)
- [ ] Eigene Tage über OptionsFlow und Actions `tag_hinzufuegen`/`tag_entfernen`
- [ ] `schultage_bis_ferien`, `ferientage_verbleibend`, `letzter_schultag`, `erster_schultag`, `naechster_schultag`, `naechster_feiertag`
- [ ] Actions `termine_abrufen`, `schultag_pruefen`, `aktualisieren`
- [ ] Diagnostics, Repairs (14 Tage ohne Update, Daten enden in < 60 Tagen), Reconfigure
- [ ] Option regionale Feiertage
- [ ] 3 Blueprints: Schulwecker, Ranzen-Erinnerung, Rollläden
- [ ] README de + en mit Beispiel-Automationen

## M3 – HACS-Default (1 Tag + Wartezeit)
- [ ] Quality-Scale-Selbsteinstufung Gold in `quality_scale.yaml`
- [ ] HACS-Voraussetzungen prüfen (Action, Hassfest, Release, Lizenz, Topics, Icon)
- [ ] PR an `hacs/default` (nach Freigabe durch Matthias)
- [ ] Ankündigung im HA-Forum und bei simon42, Antworten in den Threads aus `docs/plan.md` (nach Freigabe durch Matthias)

## M4 – Optional
- [ ] Kombi-Helfer über mehrere Länder (beliebig/alle frei)
- [ ] Sensor nächster Brückentag
- [ ] Berufliche Schulen (Sync muss BBS-Daten behalten)
- [ ] Prüfung Aufnahme in HA Core (setzt PyPI-Bibliothek voraus)
