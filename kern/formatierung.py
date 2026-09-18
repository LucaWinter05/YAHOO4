"""Formatierungs-Helfer: Zahlen, Preise, Prozente und Produktnamen.

Alles hier ist rein funktional und ohne Streamlit-Abhängigkeit, damit es sich
einzeln testen lässt (siehe ``tests/test_formatierung.py``).
"""

from __future__ import annotations

import re

__all__ = [
    "eur",
    "waehrung",
    "zahl",
    "kompakt",
    "kompakt_formatieren",
    "prozent",
    "sterne",
    "kurzname",
    "pluralisieren",
]

# Einheiten fürs kompakte Format (absteigend geprüft)
_EINHEITEN: tuple[tuple[float, str], ...] = (
    (1e12, "Bio."),
    (1e9, "Mrd."),
    (1e6, "Mio."),
    (1e3, "Tsd."),
)

# Zeichen, die in Produkttiteln nur Rauschen sind
_TRENNZEICHEN = re.compile(r'[\(\)\[\]\"\'„“”/\\,;:\.\-–—_…!?\*+|=]')

# Füllwörter, die einen Kurznamen nicht beschreiben
_STOPWOERTER = {
    "mit", "und", "oder", "für", "fuer", "aus", "der", "die", "das", "den",
    "dem", "des", "ein", "eine", "einen", "einem", "einer", "im", "in", "an",
    "am", "auf", "zu", "zum", "zur", "von", "vom", "bei", "als", "inkl",
    "ca", "cm", "mm", "stk", "set", "stück", "stueck", "ohne", "sowie",
}


def zahl(wert: float | int | None, dezimalstellen: int = 2) -> str:
    """Deutsche Zahlenschreibweise: ``1234.5`` -> ``'1.234,50'``."""
    if wert is None:
        return "–"
    return (
        f"{wert:,.{dezimalstellen}f}"
        .replace(",", "\x00")
        .replace(".", ",")
        .replace("\x00", ".")
    )


def eur(wert: float | None, dezimalstellen: int = 2) -> str:
    """Betrag als Euro-String, z. B. ``'1.234,50 €'``."""
    if wert is None:
        return "–"
    return f"{zahl(wert, dezimalstellen)} €"


def waehrung(wert: float | None, code: str = "EUR", dezimalstellen: int = 2) -> str:
    """Betrag mit beliebigem Währungscode/-symbol."""
    if wert is None:
        return "–"
    symbole = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥", "CHF": "CHF"}
    symbol = symbole.get((code or "").upper(), code or "")
    return f"{zahl(wert, dezimalstellen)} {symbol}".strip()


def kompakt(betrag: float | None, einheit: str = "€", dezimalstellen: int = 2) -> str:
    """Große Beträge lesbar kürzen: ``3.1e12`` -> ``'3,10 Bio. €'``."""
    if betrag is None:
        return f"– {einheit}".strip()

    vorzeichen = "-" if betrag < 0 else ""
    rest = abs(betrag)

    for schwelle, suffix in _EINHEITEN:
        if rest >= schwelle:
            gekuerzt = zahl(rest / schwelle, dezimalstellen)
            return f"{vorzeichen}{gekuerzt} {suffix} {einheit}".strip()

    return f"{vorzeichen}{zahl(rest, dezimalstellen)} {einheit}".strip()


def kompakt_formatieren(betrag: float | None, einheit: str = "€") -> str:
    """Alias aus der ersten App-Version – bleibt aus Kompatibilitätsgründen."""
    return kompakt(betrag, einheit)


def prozent(wert: float | None, dezimalstellen: int = 2, mit_vorzeichen: bool = True) -> str:
    """``0.0734`` ist *kein* Prozentwert – hier wird ``7.34`` zu ``'+7,34 %'``."""
    if wert is None:
        return "–"
    vorzeichen = "+" if (mit_vorzeichen and wert > 0) else ""
    return f"{vorzeichen}{zahl(wert, dezimalstellen)} %"


def sterne(bewertung: float | None, anzahl: int | None = None) -> str:
    """Sterne-Darstellung inkl. halbem Stern und optionaler Bewertungszahl."""
    if bewertung is None:
        return "–"
    voll = int(bewertung)
    halb = "½" if bewertung - voll >= 0.5 else ""
    leer = "☆" * max(0, 5 - voll - (1 if halb else 0))
    text = f"{'★' * voll}{halb}{leer} {zahl(bewertung, 1)}"
    if anzahl:
        text += f" ({zahl(anzahl, 0)})"
    return text


def pluralisieren(anzahl: int, einzahl: str, mehrzahl: str | None = None) -> str:
    """``1 Produkt`` / ``3 Produkte``."""
    if anzahl == 1:
        return f"{anzahl} {einzahl}"
    return f"{anzahl} {mehrzahl or einzahl + 'e'}"


def kurzname(produktname: str, hersteller: str = "", max_woerter: int = 3) -> str:
    """Macht aus einem Monster-Produkttitel einen kurzen, sprechbaren Namen.

    ``"OTTO home Teppich Salsa, rechteckig, Höhe 9 mm, ..."`` wird zu
    ``"OTTO home Teppich Salsa"`` – Hersteller vorn, danach die ersten
    aussagekräftigen Wörter ohne Zahlen, Maße und Füllwörter.
    """
    text = produktname or ""
    hersteller = (hersteller or "").strip()

    if hersteller:
        # Hersteller aus dem Titel entfernen – tolerant gegenüber Mehrfach-Leerzeichen
        muster = r"\s+".join(re.escape(w) for w in hersteller.split())
        text = re.sub(muster, " ", text, flags=re.IGNORECASE)

    text = _TRENNZEICHEN.sub(" ", text)

    woerter: list[str] = []
    if hersteller:
        woerter.append(hersteller)

    for wort in text.split():
        if len(woerter) >= max_woerter:
            break
        if re.search(r"\d", wort):          # Maße, Größen, Modellnummern raus
            continue
        if len(wort) < 3:                    # "S", "XL", "cm" ...
            continue
        if wort.lower() in _STOPWOERTER:
            continue
        if any(wort.lower() == vorhanden.lower() for vorhanden in woerter):
            continue
        woerter.append(wort)

    if not woerter:
        # Notnagel: lieber abgeschnittener Originaltitel als leerer String
        return (produktname or "Produkt")[:40].strip()

    return " ".join(woerter)
