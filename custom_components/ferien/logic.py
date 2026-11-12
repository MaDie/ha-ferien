"""Datumslogik für Ferien, Feiertage und Schultage.

Keine Home-Assistant-Importe. Alle Kalendertage sind Europe/Berlin;
die Uhrzeit spielt nur für die nächste Mitternacht eine Rolle.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from enum import StrEnum
from zoneinfo import ZoneInfo

from .const import ABRUF_STUNDE_MAX, ABRUF_STUNDE_MIN

BERLIN = ZoneInfo("Europe/Berlin")


class Grund(StrEnum):
    """Warum ein Tag schulfrei ist. Die Reihenfolge ist die Anzeigepriorität."""

    EIGENER_TAG = "eigener_tag"
    FERIEN = "ferien"
    FEIERTAG = "feiertag"
    SCHULFREI = "schulfrei"
    WOCHENENDE = "wochenende"


@dataclass(frozen=True, slots=True)
class Zeitraum:
    """Ferien oder schulfreier Zeitraum. `ende` ist inklusiv."""

    id: str
    name: str
    typ: str
    start: date
    ende: date
    frei_von: date
    frei_bis: date
    bestaetigt: bool
    hinweis: str | None

    def __post_init__(self) -> None:
        """Ablehnen, was sich nicht als Zeitraum rechnen lässt."""
        if self.start > self.ende:
            msg = f"{self.id}: start liegt nach ende"
            raise ValueError(msg)
        if self.frei_von > self.start or self.frei_bis < self.ende:
            msg = f"{self.id}: freier Block deckt den Zeitraum nicht"
            raise ValueError(msg)

    def enthaelt_unterricht(self, tag: date) -> bool:
        """Liegt der Tag im offiziellen Zeitraum (`start`–`ende`)?"""
        return self.start <= tag <= self.ende

    def enthaelt_block(self, tag: date) -> bool:
        """Liegt der Tag im freien Block inklusive angrenzender Tage?"""
        return self.frei_von <= tag <= self.frei_bis


@dataclass(frozen=True, slots=True)
class Feiertag:
    """Gesetzlicher Feiertag. `teilweise` und `lokal` sind optional."""

    name: str
    datum: date
    bundesweit: bool
    teilweise: bool
    lokal: bool
    hinweis: str | None

    def sichtbar(self, regionale: bool) -> bool:
        """Regionale Feiertage nur, wenn die Option aktiv ist."""
        if self.teilweise or self.lokal:
            return regionale
        return True


@dataclass(frozen=True, slots=True)
class EigenerTag:
    """Vom Nutzer angelegter schulfreier Tag oder Zeitraum."""

    start: date
    ende: date
    name: str

    def __post_init__(self) -> None:
        """Name und Reihenfolge prüfen."""
        if self.start > self.ende:
            msg = "Ende liegt vor dem Start"
            raise ValueError(msg)
        if not self.name.strip():
            msg = "Name fehlt"
            raise ValueError(msg)

    def enthaelt(self, tag: date) -> bool:
        """Liegt der Tag im eigenen Zeitraum?"""
        return self.start <= tag <= self.ende


@dataclass(frozen=True, slots=True)
class Termine:
    """Aufbereitete Antwort von `/termine`."""

    land_code: str
    land_name: str
    von: date
    bis: date
    ferien: tuple[Zeitraum, ...]
    schulfrei: tuple[Zeitraum, ...]
    feiertage: tuple[Feiertag, ...]
    quelle: str
    lizenz: str
    datenstand: datetime | None

    def __post_init__(self) -> None:
        """Abdeckung muss ein Intervall sein."""
        if self.von > self.bis:
            msg = "von liegt nach bis"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class TagBild:
    """Bewertung eines einzelnen Tages.

    `schulfrei`, `ferien` und `feiertag` sind `None`, wenn der Wert nicht
    belegt werden kann. Ein Wochenende oder ein eigener Tag ist auch ohne
    API-Daten bekannt. `False` gibt es nur innerhalb der geladenen Abdeckung,
    damit fehlende Daten nie als Schultag erscheinen.
    """

    schulfrei: bool | None
    ferien: bool | None
    feiertag: bool | None
    grund: Grund | None
    name: str | None
    ferien_name: str | None
    ferien_start: date | None
    ferien_ende: date | None
    feiertag_name: str | None


@dataclass(frozen=True, slots=True)
class Ereignis:
    """Ganztägiger Kalendereintrag. `ende` ist exklusiv, wie in Home Assistant."""

    uid: str
    name: str
    start: date
    ende: date
    beschreibung: str | None = None


def waehle_abrufzeit(rng: random.Random) -> tuple[int, int]:
    """Zufällige Stunde und Minute im Fenster 03:00–05:00."""
    return (
        rng.randint(ABRUF_STUNDE_MIN, ABRUF_STUNDE_MAX),
        rng.randint(0, 59),
    )


def heute_in_berlin(jetzt: datetime) -> date:
    """Kalendertag in Europe/Berlin."""
    return _als_berlin(jetzt).date()


def naechste_mitternacht(jetzt: datetime) -> datetime:
    """Nächste Mitternacht Europe/Berlin, streng nach `jetzt`.

    Am Tag der Zeitumstellung ist der Abstand nicht 24 Stunden. Es wird der
    nächste vorhandene lokale Mitternachtspunkt gewählt.
    """
    lokal = _als_berlin(jetzt)
    ziel = datetime.combine(lokal.date() + timedelta(days=1), time.min, tzinfo=BERLIN)
    if ziel <= lokal:
        ziel = datetime.combine(
            lokal.date() + timedelta(days=2), time.min, tzinfo=BERLIN
        )
    return ziel


def im_datenbereich(tag: date, termine: Termine) -> bool:
    """Deckt der Cache diesen Tag ab?"""
    return termine.von <= tag <= termine.bis


def tag_bild(
    tag: date,
    termine: Termine,
    eigene: Sequence[EigenerTag],
    *,
    regionale: bool,
) -> TagBild:
    """Einen Tag bewerten.

    Priorität des Grunds: eigener Tag, Ferien, Feiertag, schulfreier Tag,
    Wochenende. Liegt ein Feiertag in den Ferien, bleibt der Feiertagssensor
    an; der kombinierte Grund nennt die Ferien.
    """
    eigener = _eigener(tag, eigene)
    im_bereich = im_datenbereich(tag, termine)
    ferien = _ferien_am(tag, termine.ferien) if im_bereich else None
    feiertag = _feiertag_am(tag, termine.feiertage, regionale) if im_bereich else None
    schulfrei_tag = _ferien_am(tag, termine.schulfrei) if im_bereich else None
    wochenende = tag.weekday() >= 5

    grund: Grund | None
    name: str | None
    schulfrei: bool | None
    if eigener is not None:
        grund, name, schulfrei = Grund.EIGENER_TAG, eigener.name, True
    elif ferien is not None:
        grund, name, schulfrei = Grund.FERIEN, ferien.name, True
    elif feiertag is not None:
        grund, name, schulfrei = Grund.FEIERTAG, feiertag.name, True
    elif schulfrei_tag is not None:
        grund, name, schulfrei = Grund.SCHULFREI, schulfrei_tag.name, True
    elif wochenende:
        grund, name, schulfrei = Grund.WOCHENENDE, None, True
    elif im_bereich:
        grund, name, schulfrei = None, None, False
    else:
        grund, name, schulfrei = None, None, None

    return TagBild(
        schulfrei=schulfrei,
        ferien=(ferien is not None) if im_bereich else None,
        feiertag=(feiertag is not None) if im_bereich else None,
        grund=grund,
        name=name,
        ferien_name=ferien.name if ferien is not None else None,
        ferien_start=ferien.start if ferien is not None else None,
        ferien_ende=ferien.ende if ferien is not None else None,
        feiertag_name=feiertag.name if feiertag is not None else None,
    )


def ist_schultag(
    tag: date,
    termine: Termine,
    eigene: Sequence[EigenerTag],
    *,
    regionale: bool,
) -> bool:
    """Schultag nur, wenn der Tag belegt schulfrei ist."""
    return tag_bild(tag, termine, eigene, regionale=regionale).schulfrei is False


def naechste_ferien(heute: date, termine: Termine) -> Zeitraum | None:
    """Laufender freier Block oder der früheste, der noch endet."""
    kandidaten = [zeitraum for zeitraum in termine.ferien if zeitraum.frei_bis >= heute]
    if not kandidaten:
        return None
    return min(kandidaten, key=lambda zeitraum: (zeitraum.frei_von, zeitraum.start))


def tage_bis_ferien(heute: date, termine: Termine) -> int | None:
    """Kalendertage bis `frei_von`. 0, wenn der freie Block schon läuft."""
    periode = naechste_ferien(heute, termine)
    if periode is None:
        return None
    return max(0, (periode.frei_von - heute).days)


def schultage_bis_ferien(
    heute: date,
    termine: Termine,
    eigene: Sequence[EigenerTag],
    *,
    regionale: bool,
) -> int | None:
    """Schultage nach heute und vor `frei_von`. Heute zählt nicht mit."""
    periode = naechste_ferien(heute, termine)
    if periode is None or not im_datenbereich(heute, termine):
        return None
    if heute >= periode.frei_von:
        return 0
    letzter = periode.frei_von - timedelta(days=1)
    if letzter > termine.bis or heute < termine.von:
        return None
    return sum(
        1
        for tag in _tage(heute + timedelta(days=1), letzter)
        if ist_schultag(tag, termine, eigene, regionale=regionale)
    )


def ferientage_verbleibend(heute: date, termine: Termine) -> int | None:
    """Tage von heute bis `frei_bis`, sonst 0.

    `None`, wenn heute nicht abgedeckt ist.
    """
    if not im_datenbereich(heute, termine):
        return None
    laufend = [
        zeitraum for zeitraum in termine.ferien if zeitraum.enthaelt_block(heute)
    ]
    if not laufend:
        return 0
    periode = max(laufend, key=lambda zeitraum: zeitraum.frei_bis)
    return (periode.frei_bis - heute).days + 1


def letzter_schultag(
    heute: date,
    termine: Termine,
    eigene: Sequence[EigenerTag],
    *,
    regionale: bool,
) -> date | None:
    """Letzter Schultag vor dem freien Block der nächsten Ferien."""
    periode = naechste_ferien(heute, termine)
    if periode is None:
        return None
    tag = periode.frei_von - timedelta(days=1)
    while tag >= termine.von:
        if ist_schultag(tag, termine, eigene, regionale=regionale):
            return tag
        tag -= timedelta(days=1)
    return None


def erster_schultag(
    heute: date,
    termine: Termine,
    eigene: Sequence[EigenerTag],
    *,
    regionale: bool,
) -> date | None:
    """Erster Schultag nach dem freien Block der aktuellen oder nächsten Ferien."""
    periode = naechste_ferien(heute, termine)
    if periode is None:
        return None
    tag = periode.frei_bis + timedelta(days=1)
    while tag <= termine.bis:
        if ist_schultag(tag, termine, eigene, regionale=regionale):
            return tag
        tag += timedelta(days=1)
    return None


def naechster_schultag(
    heute: date,
    termine: Termine,
    eigene: Sequence[EigenerTag],
    *,
    regionale: bool,
) -> date | None:
    """Erster Schultag ab morgen, innerhalb der Abdeckung."""
    if heute >= termine.bis:
        return None
    start = max(heute + timedelta(days=1), termine.von)
    tag = start
    while tag <= termine.bis:
        if ist_schultag(tag, termine, eigene, regionale=regionale):
            return tag
        tag += timedelta(days=1)
    return None


def naechster_feiertag(
    heute: date,
    termine: Termine,
    *,
    regionale: bool,
) -> Feiertag | None:
    """Nächster sichtbarer Feiertag ab heute."""
    kandidaten = [
        feiertag
        for feiertag in termine.feiertage
        if feiertag.sichtbar(regionale) and heute <= feiertag.datum <= termine.bis
    ]
    if not kandidaten:
        return None
    return min(kandidaten, key=lambda feiertag: feiertag.datum)


def ereignisse(
    termine: Termine,
    eigene: Sequence[EigenerTag],
    *,
    regionale: bool,
    feiertage_im_kalender: bool,
) -> tuple[Ereignis, ...]:
    """Kalendereinträge. Ferien nutzen den freien Block, nicht nur `start`–`ende`."""
    eintraege: list[Ereignis] = []
    for zeitraum in termine.ferien:
        eintraege.append(
            Ereignis(
                uid=zeitraum.id,
                name=zeitraum.name,
                start=zeitraum.frei_von,
                ende=zeitraum.frei_bis + timedelta(days=1),
                beschreibung=zeitraum.hinweis,
            )
        )
    for zeitraum in termine.schulfrei:
        eintraege.append(
            Ereignis(
                uid=zeitraum.id,
                name=zeitraum.name,
                start=zeitraum.start,
                ende=zeitraum.ende + timedelta(days=1),
                beschreibung=zeitraum.hinweis,
            )
        )
    if feiertage_im_kalender:
        for feiertag in termine.feiertage:
            if not feiertag.sichtbar(regionale):
                continue
            eintraege.append(
                Ereignis(
                    uid=(
                        f"{termine.land_code.lower()}-feiertag-"
                        f"{feiertag.datum.isoformat()}"
                    ),
                    name=feiertag.name,
                    start=feiertag.datum,
                    ende=feiertag.datum + timedelta(days=1),
                    beschreibung=feiertag.hinweis,
                )
            )
    for tag in eigene:
        eintraege.append(
            Ereignis(
                uid=f"eigen-{tag.start.isoformat()}-{tag.ende.isoformat()}",
                name=tag.name,
                start=tag.start,
                ende=tag.ende + timedelta(days=1),
            )
        )
    return tuple(eintraege)


def passendes_ereignis(
    heute: date,
    ereignis_liste: Sequence[Ereignis],
) -> Ereignis | None:
    """Laufendes Ereignis, sonst das früheste kommende."""
    laufend = [
        ereignis
        for ereignis in ereignis_liste
        if ereignis.start <= heute < ereignis.ende
    ]
    if laufend:
        return min(laufend, key=lambda ereignis: (ereignis.start, ereignis.name))
    kommend = [ereignis for ereignis in ereignis_liste if ereignis.start > heute]
    if not kommend:
        return None
    return min(kommend, key=lambda ereignis: (ereignis.start, ereignis.name))


def tag_ersetzen(
    tage: Sequence[EigenerTag],
    neu: EigenerTag,
) -> tuple[EigenerTag, ...]:
    """Eigenen Tag mit gleichem Start ersetzen, sonst anfügen."""
    ohne = [tag for tag in tage if tag.start != neu.start]
    ohne.append(neu)
    return tuple(sorted(ohne, key=lambda tag: (tag.start, tag.name)))


def tag_loeschen(
    tage: Sequence[EigenerTag],
    start: date,
) -> tuple[EigenerTag, ...] | None:
    """Tag mit diesem Start entfernen. `None`, wenn keiner passt."""
    neu = tuple(tag for tag in tage if tag.start != start)
    if len(neu) == len(tuple(tage)):
        return None
    return neu


def _ferien_am(tag: date, zeitraeume: Sequence[Zeitraum]) -> Zeitraum | None:
    treffer = [zeitraum for zeitraum in zeitraeume if zeitraum.enthaelt_unterricht(tag)]
    if not treffer:
        return None
    return min(treffer, key=lambda zeitraum: (zeitraum.start, zeitraum.id))


def _feiertag_am(
    tag: date,
    feiertage: Sequence[Feiertag],
    regionale: bool,
) -> Feiertag | None:
    treffer = [
        feiertag
        for feiertag in feiertage
        if feiertag.datum == tag and feiertag.sichtbar(regionale)
    ]
    if not treffer:
        return None
    return min(treffer, key=lambda feiertag: feiertag.name)


def _eigener(tag: date, eigene: Sequence[EigenerTag]) -> EigenerTag | None:
    treffer = [eintrag for eintrag in eigene if eintrag.enthaelt(tag)]
    if not treffer:
        return None
    return min(treffer, key=lambda eintrag: (eintrag.start, eintrag.name))


def _tage(start: date, ende: date) -> Iterable[date]:
    tag = start
    while tag <= ende:
        yield tag
        tag += timedelta(days=1)


def _als_berlin(jetzt: datetime) -> datetime:
    if jetzt.tzinfo is None:
        msg = "Zeitpunkt ohne Zeitzone"
        raise ValueError(msg)
    return jetzt.astimezone(BERLIN)
