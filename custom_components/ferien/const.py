"""Konstanten der Integration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

DOMAIN: Final = "ferien"
NAME: Final = "Ferien – Schulferien & Feiertage"

API_BASE_URL: Final = "https://schulferienrechner.de"
USER_AGENT_REPOSITORY: Final = "https://github.com/MaDie/ha-ferien"

STORAGE_VERSION: Final = 1
CACHE_KEY: Final = "ferien.cache.{entry_id}"
TAGE_KEY: Final = "ferien.{entry_id}"

CONF_LAND: Final = "land"
CONF_FEIERTAGE_IM_KALENDER: Final = "feiertage_im_kalender"
CONF_REGIONALE_FEIERTAGE: Final = "regionale_feiertage"

DEFAULT_FEIERTAGE_IM_KALENDER: Final = True
DEFAULT_REGIONALE_FEIERTAGE: Final = False

HTTP_TIMEOUT_SECONDS: Final = 30
CACHE_MAX_AGE_HOURS: Final = 24
REPAIR_OHNE_ABRUF_TAGE: Final = 14
REPAIR_DATEN_ENDE_TAGE: Final = 60
# Stunde 3 oder 4, also 03:00 inklusive bis 05:00 exklusive.
ABRUF_STUNDE_MIN: Final = 3
ABRUF_STUNDE_MAX: Final = 4
NAME_MAX_LAENGE: Final = 80

KALENDER_KEY: Final = "kalender"

BINARY_KEYS: Final = (
    "schulfrei_heute",
    "schulfrei_morgen",
    "ferien_heute",
    "ferien_morgen",
    "feiertag_heute",
    "feiertag_morgen",
)
SENSOR_KEYS: Final = (
    "naechste_ferien",
    "letzter_schultag",
    "erster_schultag",
    "naechster_schultag",
    "naechster_feiertag",
    "tage_bis_ferien",
    "schultage_bis_ferien",
    "ferientage_verbleibend",
)
DIAGNOSE_KEYS: Final = (
    "datenstand",
    "letzte_aktualisierung",
    "daten_bis",
)

ISSUE_ABRUF_VERALTET: Final = "abruf_veraltet"
ISSUE_DATEN_ENDEN: Final = "daten_enden"

SERVICE_TAG_HINZUFUEGEN: Final = "tag_hinzufuegen"
SERVICE_TAG_ENTFERNEN: Final = "tag_entfernen"
SERVICE_TERMINE_ABRUFEN: Final = "termine_abrufen"
SERVICE_SCHULTAG_PRUEFEN: Final = "schultag_pruefen"
SERVICE_AKTUALISIEREN: Final = "aktualisieren"

# code, Name, ISO, Slug. Slugs wie von /api/v1/laender.
LAENDER: Final[tuple[tuple[str, str, str, str], ...]] = (
    ("BW", "Baden-Württemberg", "DE-BW", "baden-wuerttemberg"),
    ("BY", "Bayern", "DE-BY", "bayern"),
    ("BE", "Berlin", "DE-BE", "berlin"),
    ("BB", "Brandenburg", "DE-BB", "brandenburg"),
    ("HB", "Bremen", "DE-HB", "bremen"),
    ("HH", "Hamburg", "DE-HH", "hamburg"),
    ("HE", "Hessen", "DE-HE", "hessen"),
    ("MV", "Mecklenburg-Vorpommern", "DE-MV", "mecklenburg-vorpommern"),
    ("NI", "Niedersachsen", "DE-NI", "niedersachsen"),
    ("NW", "Nordrhein-Westfalen", "DE-NW", "nrw"),
    ("RP", "Rheinland-Pfalz", "DE-RP", "rheinland-pfalz"),
    ("SL", "Saarland", "DE-SL", "saarland"),
    ("SN", "Sachsen", "DE-SN", "sachsen"),
    ("ST", "Sachsen-Anhalt", "DE-ST", "sachsen-anhalt"),
    ("SH", "Schleswig-Holstein", "DE-SH", "schleswig-holstein"),
    ("TH", "Thüringen", "DE-TH", "thueringen"),
)

LAND_NACH_CODE: Final = {code: name for code, name, _iso, _slug in LAENDER}
LAND_NACH_SLUG: Final = {slug: code for code, _name, _iso, slug in LAENDER}


def integration_version() -> str:
    """Version aus dem Manifest, eine Quelle für User-Agent und Gerät."""
    manifest = Path(__file__).parent / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    version = data["version"]
    if not isinstance(version, str) or not version:
        msg = "manifest.json enthält keine Version"
        raise RuntimeError(msg)
    return version


VERSION: Final = integration_version()
USER_AGENT: Final = f"ha-ferien/{VERSION} (+{USER_AGENT_REPOSITORY})"


def termine_url(code: str) -> str:
    """URL des Paket-Endpunkts für ein Bundesland."""
    return f"{API_BASE_URL}/api/v1/laender/{code}/termine"


def region_url() -> str:
    """URL der bestehenden Regionsvorwahl."""
    return f"{API_BASE_URL}/api/region"


def land_name(code: str) -> str:
    """Anzeigename eines Ländercodes."""
    return LAND_NACH_CODE[code]


def normalisiere_land(wert: object) -> str | None:
    """Ländercode, ISO oder Slug auf den zweistelligen Code abbilden."""
    if not isinstance(wert, str):
        return None
    text = wert.strip()
    if not text:
        return None
    upper = text.upper()
    if upper in LAND_NACH_CODE:
        return upper
    if upper.startswith("DE-") and upper[3:] in LAND_NACH_CODE:
        return upper[3:]
    slug = (
        text.lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    return LAND_NACH_SLUG.get(slug)
