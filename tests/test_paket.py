"""Paket, Übersetzungen und Icon."""

from __future__ import annotations

import json
import struct
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
INTEGRATION = WURZEL / "custom_components" / "ferien"


def _schluessel(wert: object, prefix: str = "") -> set[str]:
    if not isinstance(wert, dict):
        return {prefix}
    schluessel: set[str] = set()
    for name, inhalt in wert.items():
        pfad = f"{prefix}.{name}" if prefix else str(name)
        schluessel |= _schluessel(inhalt, pfad)
    return schluessel


def test_uebersetzungen_haben_dieselben_schluessel() -> None:
    """Deutsch und Englisch decken strings.json ab."""
    strings = json.loads((INTEGRATION / "strings.json").read_text(encoding="utf-8"))
    englisch = json.loads(
        (INTEGRATION / "translations" / "en.json").read_text(encoding="utf-8")
    )
    deutsch = json.loads(
        (INTEGRATION / "translations" / "de.json").read_text(encoding="utf-8")
    )
    assert englisch == strings
    assert _schluessel(deutsch) == _schluessel(strings)


def test_icon_ist_ein_png() -> None:
    """HACS liest brand/ im Repo, Home Assistant das Icon in der Integration."""
    wurzel = (WURZEL / "brand" / "icon.png").read_bytes()
    integration = (INTEGRATION / "brand" / "icon.png").read_bytes()
    assert wurzel == integration
    assert wurzel.startswith(b"\x89PNG\r\n\x1a\n")
    breite, hoehe = struct.unpack(">II", wurzel[16:24])
    assert (breite, hoehe) == (256, 256)


def test_version_kommt_aus_dem_manifest() -> None:
    """User-Agent und Manifest nutzen dieselbe Version."""
    from custom_components.ferien.const import USER_AGENT, VERSION

    manifest = json.loads((INTEGRATION / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == VERSION
    assert VERSION in USER_AGENT
    assert manifest["domain"] == "ferien"
    assert manifest["requirements"] == []
