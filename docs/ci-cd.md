# CI/CD – Spezifikation

Die Workflows liegen in `.github/workflows/`. Diese Datei beschreibt, was sie tun.

Allgemein für alle Workflows:
- `permissions: contents: read`, außer `release.yml` (`contents: write`).
- Python-Version und HA-Versionen als zentrale Matrix-Werte.
- Push/PR-Läufe mit `concurrency` und `cancel-in-progress: true`.
- Nur `GITHUB_TOKEN`, keine weiteren Secrets.

## 1. `ci.yml` – bei jedem Push und Pull Request

Trigger: `push` auf `main`, `pull_request`, `workflow_dispatch`.

| Job | Inhalt | Muss grün sein |
|---|---|---|
| `lint` | `ruff check .` und `ruff format --check .` | ja |
| `typing` | `mypy custom_components/ferien` (strict, Konfiguration in `pyproject.toml`) | ja |
| `tests` | `pytest --cov=custom_components/ferien --cov-fail-under=95` als Matrix über **aktuelle** und **vorherige** HA-Minor-Version (jeweils passende `pytest-homeassistant-custom-component`-Version und Python-Version). Vertragstests (`-m "not contract"`) ausgeschlossen | ja |
| `hassfest` | `home-assistant/actions/hassfest` prüft Manifest, Übersetzungen, Services, Struktur | ja |
| `hacs` | `hacs/action` mit `category: integration` prüft HACS-Regeln (Pflicht für HACS-Default) | ja |

Branch-Schutz auf `main`: alle fünf Jobs als Required Checks.

`pytest-homeassistant` 2026.11 ersetzt das frühere `pytest-homeassistant-custom-component`. Die Matrix installiert für 2026.11 das neue Paket und für 2026.10 die letzte Fassung `0.13.375`. Beide Zeilen nutzen Python 3.14, weil Home Assistant 2026.10 Python 3.14.2 verlangt.

## 2. `release.yml` – bei Tag `vX.Y.Z`

Trigger: `push` von Tags `v*.*.*`.

Schritte:
1. Tag ohne `v` mit `version` in `custom_components/ferien/manifest.json` vergleichen. Abweichung → Abbruch.
2. Prüfen, dass `CHANGELOG.md` einen Abschnitt `vX.Y.Z` enthält; diesen Abschnitt als Release-Text verwenden.
3. Lint, Typen und Tests wie in `ci.yml` erneut laufen lassen (wiederverwendbarer Workflow via `workflow_call`).
4. GitHub-Release erstellen. Tags mit `-beta.N`/`-rc.N` als Pre-Release markieren.
5. ZIP `ferien.zip` an das Release hängen. Im Archiv liegen die Dateien aus `custom_components/ferien` im Wurzel (`manifest.json` direkt, nicht unter `custom_components/ferien/`), weil HACS das ZIP nach `config/custom_components/ferien/` entpackt. `hacs.json` hat `"zip_release": true` und `"filename": "ferien.zip"`. Der Marketplace lädt diese Datei vom Versions-Tag, nicht vom Branch `main`.

HACS liest neue Versionen aus den GitHub-Releases; weitere Schritte sind nicht nötig.

## 3. `nightly.yml` – täglich

Trigger: `schedule` (z. B. 02:30 UTC) und `workflow_dispatch`.

| Job | Inhalt | Bei Fehler |
|---|---|---|
| `ha-beta` | Tests gegen HA-Beta (neueste `pytest-homeassistant-custom-component`-Vorabversion) | Issue mit Label `ha-kompatibilitaet` öffnen oder aktualisieren |
| `ha-dev` | Tests gegen HA-`dev`-Branch | nur Warnung (`continue-on-error: true`) |
| `vertrag` | `pytest -m contract` gegen `https://schulferienrechner.de/api/v1`: `meta`, `laender`, `laender/BY/termine`, `laender/BY/status` antworten mit 200, Antworten validieren gegen `openapi.json`, Daten reichen ≥ 12 Monate in die Zukunft, `ETag` + `304` funktionieren | Issue mit Label `api-vertrag` öffnen oder aktualisieren |

Der Vertragsjob wird erst aktiviert, wenn die API live ist (Roadmap M0 erledigt). Bis dahin ist er übersprungen (`if: false` bzw. Variable `API_LIVE`).

## 4. Dependabot (`.github/dependabot.yml`)

- `github-actions`: wöchentlich.
- `pip` für `requirements_test.txt`: wöchentlich, `pytest-homeassistant-custom-component` und `homeassistant` gruppiert.
- PRs mit Label `abhaengigkeiten`; Merge nur bei grüner CI.

## 5. Website-Seite (`MaDie/schulferienrechner.de`)

Ergänzung der bestehenden Pipeline (nicht in diesem Repo):
- Neuer Testschritt vor dem Deploy: Server lokal starten, alle `/api/v1`-Endpunkte für mindestens 2 Länder abrufen und gegen `public/api/v1/openapi.json` validieren (z. B. mit `ajv` bzw. `openapi-response-validator`).
- Schlägt die Validierung fehl, wird nicht deployed.
- Änderungen an `openapi.json` nur additiv in `v1` (siehe `docs/plan.md`, Abschnitt Stabilität).
