"""Datumslogik ohne Home Assistant."""

from __future__ import annotations

import random
from datetime import date, datetime, timedelta

import pytest

from custom_components.ferien.api import parse_termine
from custom_components.ferien.const import ABRUF_STUNDE_MAX, ABRUF_STUNDE_MIN
from custom_components.ferien.logic import (
    BERLIN,
    EigenerTag,
    Grund,
    ereignisse,
    erster_schultag,
    ferientage_verbleibend,
    heute_in_berlin,
    letzter_schultag,
    naechste_ferien,
    naechste_mitternacht,
    naechster_feiertag,
    naechster_schultag,
    passendes_ereignis,
    schultage_bis_ferien,
    tag_bild,
    tag_ersetzen,
    tag_loeschen,
    tage_bis_ferien,
    waehle_abrufzeit,
)
from tests.hilfe import lade_fixture

TERMINE = parse_termine(lade_fixture())


def _bild(tag: date, *, regionale: bool = False, eigene: tuple[EigenerTag, ...] = ()):
    return tag_bild(tag, TERMINE, eigene, regionale=regionale)


def test_abrufzeit_liegt_zwischen_drei_und_fuenf() -> None:
    """03:00 inklusive bis 05:00 exklusive, über mehrere Seeds."""
    for samen in range(30):
        stunde, minute = waehle_abrufzeit(random.Random(samen))
        assert ABRUF_STUNDE_MIN <= stunde <= ABRUF_STUNDE_MAX
        assert 0 <= minute <= 59


def test_freitag_vor_den_herbstferien() -> None:
    """Letzter Schultag, ein Kalendertag bis zum freien Block, keine Schultage mehr."""
    tag = date(2026, 10, 30)
    bild = _bild(tag)
    assert bild.schulfrei is False
    assert bild.ferien is False
    assert tage_bis_ferien(tag, TERMINE) == 1
    assert schultage_bis_ferien(tag, TERMINE, (), regionale=False) == 0
    assert ferientage_verbleibend(tag, TERMINE) == 0
    assert letzter_schultag(tag, TERMINE, (), regionale=False) == tag
    assert erster_schultag(tag, TERMINE, (), regionale=False) == date(2026, 11, 9)
    assert naechster_schultag(tag, TERMINE, (), regionale=False) == date(2026, 11, 9)
    assert naechster_feiertag(tag, TERMINE, regionale=False).datum == date(2026, 11, 1)  # type: ignore[union-attr]


def test_montag_in_den_herbstferien() -> None:
    """Offizieller Ferientag. Sieben Tage bis frei_bis, inklusive heute."""
    tag = date(2026, 11, 2)
    bild = _bild(tag)
    assert bild.schulfrei is True
    assert bild.grund is Grund.FERIEN
    assert bild.name == "Herbstferien"
    assert bild.ferien is True
    assert bild.ferien_start == date(2026, 11, 2)
    assert bild.ferien_ende == date(2026, 11, 6)
    assert tage_bis_ferien(tag, TERMINE) == 0
    assert ferientage_verbleibend(tag, TERMINE) == 7
    assert erster_schultag(tag, TERMINE, (), regionale=False) == date(2026, 11, 9)


def test_sonntag_vor_dem_ersten_schultag() -> None:
    """Wochenende im freien Block, offizielle Ferien sind vorbei."""
    tag = date(2026, 11, 8)
    bild = _bild(tag)
    assert bild.schulfrei is True
    assert bild.grund is Grund.WOCHENENDE
    assert bild.ferien is False
    assert tage_bis_ferien(tag, TERMINE) == 0
    assert ferientage_verbleibend(tag, TERMINE) == 1
    assert naechster_schultag(tag, TERMINE, (), regionale=False) == date(2026, 11, 9)


def test_mittwoch_ist_schultag() -> None:
    """Weihnachten beginnen am 24. Dezember. Dazwischen liegen 29 Schultage."""
    tag = date(2026, 11, 11)
    bild = _bild(tag)
    assert bild.schulfrei is False
    assert bild.ferien is False
    assert bild.feiertag is False
    assert tage_bis_ferien(tag, TERMINE) == 43
    assert schultage_bis_ferien(tag, TERMINE, (), regionale=False) == 29
    assert ferientage_verbleibend(tag, TERMINE) == 0
    assert letzter_schultag(tag, TERMINE, (), regionale=False) == date(2026, 12, 23)
    assert erster_schultag(tag, TERMINE, (), regionale=False) == date(2027, 1, 11)
    assert naechster_schultag(tag, TERMINE, (), regionale=False) == date(2026, 11, 12)
    feiertag = naechster_feiertag(tag, TERMINE, regionale=False)
    assert feiertag is not None
    assert feiertag.datum == date(2026, 12, 25)
    assert feiertag.name == "1. Weihnachtstag"


def test_buss_und_bettag_ist_kein_feiertag() -> None:
    """Schulfreier Einzeltag in Bayern, kein gesetzlicher Feiertag."""
    tag = date(2026, 11, 18)
    bild = _bild(tag)
    assert bild.schulfrei is True
    assert bild.grund is Grund.SCHULFREI
    assert bild.name == "Buß- und Bettag"
    assert bild.ferien is False
    assert bild.feiertag is False


def test_feiertag_im_ferienzeitraum_nennt_ferien_als_grund() -> None:
    """Der Feiertagssensor bleibt an, der kombinierte Grund nennt die Ferien."""
    tag = date(2026, 12, 25)
    bild = _bild(tag)
    assert bild.schulfrei is True
    assert bild.grund is Grund.FERIEN
    assert bild.ferien is True
    assert bild.feiertag is True
    assert bild.feiertag_name == "1. Weihnachtstag"


def test_christi_himmelfahrt_ausserhalb_der_ferien() -> None:
    """Wochentag, gesetzlicher Feiertag, keine Ferien."""
    tag = date(2027, 5, 6)
    bild = _bild(tag)
    assert bild.grund is Grund.FEIERTAG
    assert bild.ferien is False
    assert bild.feiertag is True
    assert bild.name == "Christi Himmelfahrt"


def test_pfingstmontag_liegt_vor_dem_offiziellen_start() -> None:
    """Feiertag im freien Block, ferien_heute bleibt aus."""
    tag = date(2027, 5, 17)
    bild = _bild(tag)
    assert bild.feiertag is True
    assert bild.ferien is False
    assert bild.grund is Grund.FEIERTAG
    assert ferientage_verbleibend(tag, TERMINE) == 14
    assert tage_bis_ferien(tag, TERMINE) == 0


def test_unbekannter_typ_bleibt_ferien() -> None:
    """Frühjahrsferien stehen nicht in der bekannten Typ-Liste."""
    tag = date(2027, 2, 8)
    bild = _bild(tag)
    assert bild.ferien is True
    assert bild.grund is Grund.FERIEN
    periode = naechste_ferien(tag, TERMINE)
    assert periode is not None
    assert periode.typ == "fruehjahrsferien"


def test_regionaler_feiertag_schaltet_nur_den_feiertag() -> None:
    """Augsburg liegt in den Sommerferien. Schulfrei bleibt an."""
    tag = date(2026, 8, 8)
    ohne = _bild(tag, regionale=False)
    mit = _bild(tag, regionale=True)
    assert ohne.feiertag is False
    assert ohne.schulfrei is True
    assert mit.feiertag is True
    assert mit.schulfrei is True
    assert mit.grund is Grund.FERIEN
    assert (
        naechster_feiertag(tag, TERMINE, regionale=True).name
        == "Augsburger Friedensfest"
    )  # type: ignore[union-attr]


def test_wochentag_ausserhalb_ist_unbekannt_wochenende_nicht() -> None:
    """Fehlende Daten werden nie als Schultag ausgegeben."""
    mittwoch = _bild(date(2026, 7, 1))
    samstag = _bild(date(2026, 7, 4))
    assert mittwoch.schulfrei is None
    assert mittwoch.ferien is None
    assert samstag.schulfrei is True
    assert samstag.grund is Grund.WOCHENENDE
    assert ferientage_verbleibend(date(2026, 7, 1), TERMINE) is None
    assert schultage_bis_ferien(date(2026, 7, 1), TERMINE, (), regionale=False) is None


def test_eigener_tag_hat_vorrang_auch_ausserhalb() -> None:
    """Ein eigener Tag ist bekannt, auch wenn der Cache den Tag nicht deckt."""
    tag = date(2026, 7, 1)
    eigene = (EigenerTag(start=tag, ende=tag, name="Betriebsausflug"),)
    bild = _bild(tag, eigene=eigene)
    assert bild.schulfrei is True
    assert bild.grund is Grund.EIGENER_TAG
    assert bild.name == "Betriebsausflug"
    assert bild.ferien is None


def test_eigener_tag_wird_ersetzt_und_geloescht() -> None:
    """Dasselbe Startdatum ersetzt den Eintrag."""
    start = date(2026, 11, 12)
    erster = EigenerTag(start=start, ende=start, name="Alt")
    neu = EigenerTag(start=start, ende=date(2026, 11, 13), name="Neu")
    ersetzt = tag_ersetzen((erster,), neu)
    assert len(ersetzt) == 1
    assert ersetzt[0].name == "Neu"
    assert tag_loeschen(ersetzt, start) == ()
    assert tag_loeschen(ersetzt, date(2026, 1, 1)) is None


def test_kalender_endet_exklusiv_und_nimmt_den_freien_block() -> None:
    """Herbstferien beginnen am Samstag vor dem offiziellen Start."""
    liste = ereignisse(TERMINE, (), regionale=False, feiertage_im_kalender=True)
    herbst = next(
        eintrag for eintrag in liste if eintrag.uid == "by-herbstferien-2026-11-02"
    )
    assert herbst.start == date(2026, 10, 31)
    assert herbst.ende == date(2026, 11, 9)
    feiertag = next(eintrag for eintrag in liste if eintrag.name == "Neujahr")
    assert feiertag.ende == feiertag.start + timedelta(days=1)
    ohne = ereignisse(TERMINE, (), regionale=False, feiertage_im_kalender=False)
    assert all("feiertag" not in eintrag.uid for eintrag in ohne)
    heute = date(2026, 11, 11)
    passend = passendes_ereignis(heute, liste)
    assert passend is not None
    assert passend.start == date(2026, 11, 18)


def test_mitternacht_ueber_die_zeitumstellung() -> None:
    """Der lokale Abstand ist ein Tag, die Offsets unterscheiden sich."""
    herbst = datetime(2026, 10, 25, 0, 0, tzinfo=BERLIN)
    naechste = naechste_mitternacht(herbst)
    assert naechste == datetime(2026, 10, 26, 0, 0, tzinfo=BERLIN)
    assert herbst.utcoffset() == timedelta(hours=2)
    assert naechste.utcoffset() == timedelta(hours=1)
    fruehjahr = datetime(2027, 3, 28, 0, 0, tzinfo=BERLIN)
    danach = naechste_mitternacht(fruehjahr)
    assert danach == datetime(2027, 3, 29, 0, 0, tzinfo=BERLIN)
    assert fruehjahr.utcoffset() == timedelta(hours=1)
    assert danach.utcoffset() == timedelta(hours=2)


def test_naive_zeit_wird_abgelehnt() -> None:
    """Ohne Zeitzone gibt es kein Berlin-Datum."""
    with pytest.raises(ValueError, match="Zeitzone"):
        heute_in_berlin(datetime(2026, 11, 11, 12, 0))


def test_eigener_zeitraum_validiert_grenzen() -> None:
    """Ende vor Start ist kein Zeitraum."""
    with pytest.raises(ValueError):
        EigenerTag(start=date(2026, 11, 12), ende=date(2026, 11, 11), name="Falsch")
    with pytest.raises(ValueError):
        EigenerTag(start=date(2026, 11, 12), ende=date(2026, 11, 12), name="  ")
