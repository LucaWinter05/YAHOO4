"""Zugriff auf die OTTO-Produktdatenbank (``otto_produkte.db``).

Die App arbeitet durchgängig mit einem gecachten pandas-DataFrame statt mit
einer offenen SQLite-Verbindung. Gründe:

* Streamlit führt Skripte pro Interaktion in wechselnden Threads aus – eine
  globale ``sqlite3.Connection`` ist dort ein latenter Absturz.
* Die Datenbank ist wenige hundert Kilobyte groß; einmal komplett laden und
  im Cache halten ist schneller als Dutzende Einzel-Queries pro Rerun.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

from otto_scraper import OttoProduct

__all__ = [
    "DB_PFAD",
    "lade_produkte",
    "lade_tag",
    "verfuegbare_daten",
    "neuestes_datum",
    "produkt_nach_url",
    "preisverlauf",
    "kennzahlen",
    "als_produkt",
    "suchbegriffe",
    "marken",
    "DatenbankLeer",
]

DB_PFAD = Path(__file__).resolve().parent.parent / "otto_produkte.db"

_SPALTEN = [
    "id", "scraped_date", "suchbegriff", "titel", "marke", "preis", "old_price",
    "currency", "bild_url", "produkt_url", "bewertung", "anzahl_bewertungen",
    "verfuegbarkeit", "sku", "gtin",
]


class DatenbankLeer(RuntimeError):
    """Wird geworfen, wenn gar keine nutzbaren Produktdaten vorliegen."""


@dataclass(frozen=True)
class Kennzahlen:
    """Aggregierte Eckdaten für das Dashboard."""

    anzahl: int
    anzahl_heute: int
    suchbegriffe: int
    marken: int
    guenstigstes: float | None
    teuerstes: float | None
    median: float | None
    durchschnitt: float | None
    mit_rabatt: int
    groesster_rabatt: int | None
    stand: str
    tage_historie: int


# --------------------------------------------------------------------------- #
# Laden
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=600, show_spinner=False)
def lade_produkte(db_pfad: str | None = None) -> pd.DataFrame:
    """Komplette Produkttabelle als DataFrame – aufbereitet und bereinigt.

    Zusätzlich berechnete Spalten:

    ``rabatt_pct``   Rabatt gegenüber UVP in Prozent
    ``ersparnis``    absolute Ersparnis in Euro
    ``kurztitel``    gekürzter, lesbarer Produktname
    ``bewertung``    NaN statt 0 (0 heißt bei OTTO „keine Bewertung“)
    """
    pfad = Path(db_pfad) if db_pfad else DB_PFAD
    if not pfad.exists():
        return pd.DataFrame(columns=_SPALTEN)

    with sqlite3.connect(f"file:{pfad}?mode=ro", uri=True) as con:
        df = pd.read_sql_query(f"SELECT {', '.join(_SPALTEN)} FROM produkte", con)

    if df.empty:
        return df

    # Typen geradeziehen
    for spalte in ("preis", "old_price", "bewertung"):
        df[spalte] = pd.to_numeric(df[spalte], errors="coerce")
    df["anzahl_bewertungen"] = pd.to_numeric(df["anzahl_bewertungen"], errors="coerce").fillna(0).astype(int)
    for spalte in ("marke", "titel", "bild_url", "verfuegbarkeit", "sku", "gtin", "currency", "suchbegriff"):
        df[spalte] = df[spalte].fillna("").astype(str).str.strip()

    df["currency"] = df["currency"].replace("", "EUR")
    df = df[df["preis"].notna() & (df["preis"] > 0)].copy()
    if df.empty:
        return df

    df["scraped_date"] = df["scraped_date"].astype(str)
    df["datum"] = pd.to_datetime(df["scraped_date"], errors="coerce")

    # Abgeleitete Spalten
    hat_uvp = df["old_price"].notna() & (df["old_price"] > df["preis"])
    df["rabatt_pct"] = 0
    df.loc[hat_uvp, "rabatt_pct"] = (
        (1 - df.loc[hat_uvp, "preis"] / df.loc[hat_uvp, "old_price"]) * 100
    ).round().astype(int)
    df["ersparnis"] = 0.0
    df.loc[hat_uvp, "ersparnis"] = (df.loc[hat_uvp, "old_price"] - df.loc[hat_uvp, "preis"]).round(2)

    from kern.formatierung import kurzname  # lokal, um Zirkelimporte zu vermeiden

    df["kurztitel"] = [kurzname(t, m) for t, m in zip(df["titel"], df["marke"])]
    df["preisklasse"] = pd.cut(
        df["preis"],
        bins=[0, 10, 25, 50, 100, 250, 500, 1000, 5000, float("inf")],
        labels=["< 10 €", "10–25 €", "25–50 €", "50–100 €", "100–250 €",
                "250–500 €", "500–1.000 €", "1.000–5.000 €", "> 5.000 €"],
    )

    return df.sort_values("preis", ascending=False).reset_index(drop=True)


@st.cache_data(ttl=600, show_spinner=False)
def verfuegbare_daten(db_pfad: str | None = None) -> list[str]:
    """Alle Scrape-Tage, neuester zuerst."""
    df = lade_produkte(db_pfad)
    if df.empty:
        return []
    return sorted(df["scraped_date"].unique().tolist(), reverse=True)


def neuestes_datum(db_pfad: str | None = None) -> str | None:
    daten = verfuegbare_daten(db_pfad)
    return daten[0] if daten else None


def lade_tag(datum: str | None = None, db_pfad: str | None = None) -> pd.DataFrame:
    """Produkte eines bestimmten Scrape-Tages (Standard: der neueste)."""
    df = lade_produkte(db_pfad)
    if df.empty:
        return df
    datum = datum or neuestes_datum(db_pfad)
    return df[df["scraped_date"] == datum].reset_index(drop=True)


def suchbegriffe(df: pd.DataFrame) -> list[str]:
    return sorted(df["suchbegriff"].dropna().unique().tolist()) if not df.empty else []


def marken(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []
    return sorted(m for m in df["marke"].dropna().unique().tolist() if m)


def produkt_nach_url(url: str, db_pfad: str | None = None) -> pd.Series | None:
    """Neuester Datensatz zu einer Produkt-URL (für geteilte Links)."""
    df = lade_produkte(db_pfad)
    if df.empty or not url:
        return None
    treffer = df[df["produkt_url"] == url]
    if treffer.empty:
        return None
    return treffer.sort_values("scraped_date", ascending=False).iloc[0]


def preisverlauf(url: str, db_pfad: str | None = None) -> pd.DataFrame:
    """Preisentwicklung eines Produkts über alle Scrape-Tage hinweg."""
    df = lade_produkte(db_pfad)
    if df.empty or not url:
        return pd.DataFrame(columns=["datum", "preis"])
    verlauf = df[df["produkt_url"] == url][["datum", "preis", "old_price"]]
    return verlauf.sort_values("datum").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Umwandlung in das Produkt-Objekt des Scrapers
# --------------------------------------------------------------------------- #
def als_produkt(zeile: pd.Series | dict) -> OttoProduct:
    """DataFrame-Zeile -> :class:`OttoProduct` (das Format der Produktkarten)."""
    def wert(name, standard=None):
        v = zeile.get(name, standard)
        if isinstance(v, float) and pd.isna(v):
            return standard
        return v

    return OttoProduct(
        title=wert("titel", "") or "",
        brand=wert("marke", "") or "",
        price=float(wert("preis")) if wert("preis") is not None else None,
        old_price=float(wert("old_price")) if wert("old_price") is not None else None,
        currency=wert("currency", "EUR") or "EUR",
        image_url=wert("bild_url", "") or "",
        product_url=wert("produkt_url", "") or "",
        rating=float(wert("bewertung")) if wert("bewertung") is not None else None,
        review_count=int(wert("anzahl_bewertungen") or 0) or None,
        availability=wert("verfuegbarkeit", "") or "",
        sku=str(wert("sku", "") or ""),
        gtin=str(wert("gtin", "") or ""),
    )


# --------------------------------------------------------------------------- #
# Kennzahlen
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=600, show_spinner=False)
def kennzahlen(db_pfad: str | None = None) -> Kennzahlen:
    """Eckdaten der Datenbank für das Insights-Dashboard."""
    df = lade_produkte(db_pfad)
    if df.empty:
        return Kennzahlen(0, 0, 0, 0, None, None, None, None, 0, None, "–", 0)

    stand = neuestes_datum(db_pfad) or "–"
    heute = df[df["scraped_date"] == stand]
    mit_rabatt = df[df["rabatt_pct"] > 0]

    return Kennzahlen(
        anzahl=len(df),
        anzahl_heute=len(heute),
        suchbegriffe=df["suchbegriff"].nunique(),
        marken=df["marke"].replace("", pd.NA).nunique(),
        guenstigstes=float(df["preis"].min()),
        teuerstes=float(df["preis"].max()),
        median=float(df["preis"].median()),
        durchschnitt=float(df["preis"].mean()),
        mit_rabatt=len(mit_rabatt),
        groesster_rabatt=int(mit_rabatt["rabatt_pct"].max()) if not mit_rabatt.empty else None,
        stand=stand,
        tage_historie=df["scraped_date"].nunique(),
    )
