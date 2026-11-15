# Changelog

## Unreleased

## v0.2.0 – 2026-11-15

- Sensor Grund heute zeigt den Namen der Ferien, des Feiertags, des schulfreien oder eigenen Tags. Ohne Namen steht dort Wochenende, in der Systemsprache. An einem Schultag ist der Zustand `unknown`.
- Quality Scale im Manifest ist Platinum.
- Das Release-ZIP enthält die Integrationsdateien im Archiv-Wurzel, damit HACS `manifest.json` findet.

## v0.1.0 – 2026-11-12

- Ein fehlgeschlagener Abruf setzt die Entitäten auf `unavailable`. Der Cache bleibt und gilt nach einem Neustart innerhalb von 24 Stunden wieder.
- Der tägliche Abruf läuft auch, wenn der letzte Erfolg weniger als 24 Stunden zurückliegt. Nach HTTP 429 folgt ein Versuch zum Ablauf von Retry-After.
- Schulferien, schulfreie Tage und Feiertage für alle 16 Bundesländer.
- Heute/Morgen, Kalender, Countdowns, eigene Tage, Diagnose und Reparaturhinweise.
