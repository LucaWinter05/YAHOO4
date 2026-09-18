"""Yahoo-Finance-Anbindung – gecacht, robust und in Euro gerechnet.

Der Rest der App soll sich nie mit yfinance-Eigenheiten herumschlagen müssen.
Deshalb liefert dieses Modul genau zwei Dinge:

* :func:`suche` – Ticker-Vorschläge für die Suchbox
* :func:`lade_markt` – ein vollständiges :class:`MarktDaten`-Objekt

Alles ist mit ``st.cache_data`` gecacht (Yahoo mag keine Dauerfeuer-Requests)
und jeder Feldzugriff ist gegen fehlende Daten abgesichert: Yahoo liefert für
ETFs, Krypto und Derivate jeweils andere Teilmengen an Feldern.
"""

from __future__ import annotations

import datetime as _dt
import math
from dataclasses import dataclass, field

import pandas as pd
import streamlit as st
import yfinance as yf

__all__ = [
    "MarktDaten",
    "suche",
    "such_vorschlaege",
    "lade_markt",
    "lade_historie",
    "vergleichs_historie",
    "in_euro",
    "TYP_LABELS",
]

# Wie lange Kursdaten gecacht werden (Sekunden)
_TTL_KURS = 300
_TTL_SUCHE = 600
_TTL_FX = 60 * 60 * 6

TYP_LABELS: dict[str, str] = {
    "AKTIE": "📈 Aktie",
    "ETF": "🧺 ETF / Fonds",
    "KRYPTO": "🪙 Kryptowährung",
    "DERIVAT": "🎢 Derivat",
    "INDEX": "📊 Index",
    "WAEHRUNG": "💱 Währung",
    "SONSTIGES": "❔ Sonstiges",
}

_QUOTE_TYP_MAP = {
    "EQUITY": "AKTIE",
    "STOCK": "AKTIE",
    "ETF": "ETF",
    "MUTUALFUND": "ETF",
    "CRYPTOCURRENCY": "KRYPTO",
    "OPTION": "DERIVAT",
    "FUTURE": "DERIVAT",
    "FUTURES": "DERIVAT",
    "INDEX": "INDEX",
    "CURRENCY": "WAEHRUNG",
}

PERIODEN: dict[str, str] = {
    "1 Monat": "1mo",
    "3 Monate": "3mo",
    "6 Monate": "6mo",
    "1 Jahr": "1y",
    "2 Jahre": "2y",
    "5 Jahre": "5y",
    "10 Jahre": "10y",
    "Max": "max",
}


# --------------------------------------------------------------------------- #
# Währungsumrechnung
# --------------------------------------------------------------------------- #
@st.cache_resource(show_spinner=False)
def _konverter():
    """CurrencyConverter einmal pro Prozess laden (lädt EZB-Daten)."""
    try:
        import currency_converter as cc

        return cc.CurrencyConverter(fallback_on_missing_rate=True,
                                    fallback_on_wrong_date=True)
    except Exception:  # noqa: BLE001 – ohne Konverter läuft die App trotzdem
        return None


@st.cache_data(ttl=_TTL_FX, show_spinner=False)
def _fx_via_yahoo(von: str, nach: str) -> float | None:
    """Notfall-Kurs über Yahoo (``EURUSD=X``) – für Krypto & Exoten."""
    if not von or not nach or von == nach:
        return 1.0
    try:
        paar = yf.Ticker(f"{von}{nach}=X")
        kurs = paar.fast_info.get("last_price")
        if kurs and kurs > 0:
            return float(kurs)
    except Exception:  # noqa: BLE001
        pass
    return None


def in_euro(betrag: float | None, waehrung: str | None) -> float | None:
    """Rechnet einen Betrag nach Euro um – mit mehreren Fallback-Ebenen.

    ``GBp`` (britische Pence) wird korrekt als 1/100 GBP behandelt; das ist der
    Klassiker, an dem Kursvergleiche sonst um Faktor 100 danebenliegen.
    """
    if betrag is None:
        return None
    code = (waehrung or "EUR").strip()

    if code == "GBp":
        betrag, code = betrag / 100, "GBP"
    if code.upper() == "EUR":
        return float(betrag)

    konverter = _konverter()
    if konverter is not None:
        try:
            return float(konverter.convert(betrag, code.upper(), "EUR"))
        except Exception:  # noqa: BLE001 – unbekannte Währung
            pass

    kurs = _fx_via_yahoo(code.upper(), "EUR")
    if kurs:
        return float(betrag) * kurs
    return float(betrag)  # letzte Rettung: unverändert durchreichen


# --------------------------------------------------------------------------- #
# Suche
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=_TTL_SUCHE, show_spinner=False)
def suche(begriff: str, max_treffer: int = 12) -> list[dict]:
    """Rohe Yahoo-Suchtreffer als Liste von Dicts (gecacht)."""
    if not begriff or len(begriff.strip()) < 2:
        return []
    try:
        treffer = yf.Search(begriff.strip(), max_results=max_treffer).quotes or []
    except Exception:  # noqa: BLE001 – Suche darf die UI nie killen
        return []

    ergebnis = []
    for q in treffer:
        symbol = q.get("symbol")
        if not symbol:
            continue
        ergebnis.append(
            {
                "symbol": symbol,
                "name": q.get("longname") or q.get("shortname") or symbol,
                "typ": _QUOTE_TYP_MAP.get((q.get("quoteType") or "").upper(), "SONSTIGES"),
                "boerse": q.get("exchDisp") or q.get("exchange") or "",
            }
        )
    return ergebnis


def such_vorschlaege(begriff: str) -> list[tuple[str, str]]:
    """Vorschlagsliste für ``st_searchbox``: ``[(Anzeigetext, Symbol), ...]``."""
    vorschlaege = []
    for t in suche(begriff):
        icon = TYP_LABELS.get(t["typ"], "").split(" ")[0]
        boerse = f" · {t['boerse']}" if t["boerse"] else ""
        vorschlaege.append((f"{icon} {t['symbol']} — {t['name']}{boerse}", t["symbol"]))
    return vorschlaege


# --------------------------------------------------------------------------- #
# Kurshistorie
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=_TTL_KURS, show_spinner=False)
def lade_historie(ticker: str, periode: str = "1y") -> pd.DataFrame:
    """OHLCV-Historie als DataFrame mit Spalte ``Datum``.

    Gibt im Fehlerfall einen leeren DataFrame zurück statt zu werfen.
    """
    try:
        df = yf.Ticker(ticker).history(period=periode, auto_adjust=True)
    except Exception:  # noqa: BLE001
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.reset_index()
    zeitspalte = "Date" if "Date" in df.columns else df.columns[0]
    df = df.rename(columns={zeitspalte: "Datum"})
    df["Datum"] = pd.to_datetime(df["Datum"], utc=True).dt.tz_localize(None)
    behalten = [c for c in ["Datum", "Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    return df[behalten].dropna(subset=["Close"])


def _performance(historie: pd.DataFrame, tage: int) -> float | None:
    """Prozentuale Veränderung über die letzten ``tage`` Kalendertage."""
    if historie.empty or len(historie) < 2:
        return None
    ende = historie["Datum"].iloc[-1]
    start = ende - pd.Timedelta(days=tage)
    fenster = historie[historie["Datum"] >= start]
    if len(fenster) < 2:
        return None
    alt, neu = fenster["Close"].iloc[0], fenster["Close"].iloc[-1]
    if not alt:
        return None
    return (neu / alt - 1) * 100


def _ytd(historie: pd.DataFrame) -> float | None:
    if historie.empty:
        return None
    jahr = historie["Datum"].iloc[-1].year
    fenster = historie[historie["Datum"].dt.year == jahr]
    if len(fenster) < 2 or not fenster["Close"].iloc[0]:
        return None
    return (fenster["Close"].iloc[-1] / fenster["Close"].iloc[0] - 1) * 100


def _volatilitaet(historie: pd.DataFrame) -> float | None:
    """Annualisierte Volatilität in Prozent (Standardabweichung der Tagesrenditen)."""
    if len(historie) < 20:
        return None
    renditen = historie["Close"].pct_change().dropna()
    if renditen.empty:
        return None
    return float(renditen.std() * math.sqrt(252) * 100)


def _max_drawdown(historie: pd.DataFrame) -> float | None:
    """Größter prozentualer Rückgang vom Hoch im betrachteten Zeitraum."""
    if len(historie) < 2:
        return None
    kurse = historie["Close"]
    hoechststand = kurse.cummax()
    drawdown = (kurse / hoechststand - 1) * 100
    return float(drawdown.min())


# --------------------------------------------------------------------------- #
# Marktdaten
# --------------------------------------------------------------------------- #
@dataclass
class MarktDaten:
    """Alles, was die App über ein Wertpapier wissen will – schon in Euro."""

    ticker: str
    name: str
    typ: str = "SONSTIGES"

    preis: float | None = None                  # in EUR
    preis_original: float | None = None
    waehrung_original: str = "EUR"
    vortag: float | None = None                 # in EUR
    aenderung_pct: float | None = None

    historie: pd.DataFrame = field(default_factory=pd.DataFrame)

    marktkapitalisierung: float | None = None   # in EUR
    fondsgroesse: float | None = None           # in EUR (AUM)
    kursziel: float | None = None               # in EUR
    hoch_52w: float | None = None
    tief_52w: float | None = None
    sma50: float | None = None
    sma200: float | None = None
    volumen: float | None = None

    kgv: float | None = None
    kbv: float | None = None
    dividendenrendite: float | None = None
    beta: float | None = None
    mitarbeiter: int | None = None

    sektor: str = ""
    branche: str = ""
    land: str = ""
    webseite: str = ""
    beschreibung: str = ""
    boerse: str = ""

    # Derivate
    hebel: float | None = None
    basiswert: str = ""
    basiswert_preis: float | None = None

    performance: dict[str, float | None] = field(default_factory=dict)
    volatilitaet: float | None = None
    max_drawdown: float | None = None

    fehler: str = ""

    # -- bequeme Abfragen ---------------------------------------------------
    @property
    def ist_aktie(self) -> bool:
        return self.typ == "AKTIE"

    @property
    def ist_derivat(self) -> bool:
        return self.typ == "DERIVAT"

    @property
    def ist_fonds(self) -> bool:
        return self.typ == "ETF"

    @property
    def typ_label(self) -> str:
        return TYP_LABELS.get(self.typ, TYP_LABELS["SONSTIGES"])

    @property
    def groesse(self) -> float | None:
        """Marktkapitalisierung bzw. Fondsvolumen – je nachdem, was passt."""
        return self.marktkapitalisierung if self.marktkapitalisierung else self.fondsgroesse

    @property
    def groesse_label(self) -> str:
        """Kurzes Label – „Marktkapitalisierung" sprengt jede Kachel."""
        return "Börsenwert" if self.marktkapitalisierung else "Fondsvolumen"

    @property
    def groesse_erklaerung(self) -> str:
        return "Marktkapitalisierung" if self.marktkapitalisierung else "Assets under Management"

    @property
    def kurszielpotenzial(self) -> float | None:
        """Abstand zum Analysten-Kursziel in Prozent."""
        if not self.kursziel or not self.preis:
            return None
        return (self.kursziel / self.preis - 1) * 100

    @property
    def abstand_52w_hoch(self) -> float | None:
        if not self.hoch_52w or not self.preis:
            return None
        return (self.preis / self.hoch_52w - 1) * 100

    @property
    def position_in_52w_spanne(self) -> float | None:
        """0 % = Jahrestief, 100 % = Jahreshoch."""
        if None in (self.hoch_52w, self.tief_52w, self.preis):
            return None
        spanne = self.hoch_52w - self.tief_52w
        if spanne <= 0:
            return None
        return max(0.0, min(100.0, (self.preis - self.tief_52w) / spanne * 100))


def _sicher(quelle: dict, *schluessel, standard=None):
    """Erster Schlüssel, der einen brauchbaren Wert liefert."""
    for s in schluessel:
        wert = quelle.get(s)
        if wert not in (None, "", 0):
            return wert
    return standard


@st.cache_data(ttl=_TTL_KURS, show_spinner=False)
def _roh_info(ticker: str) -> dict:
    """``Ticker.info`` ist langsam und flaky – deshalb separat gecacht."""
    try:
        return dict(yf.Ticker(ticker).info or {})
    except Exception:  # noqa: BLE001
        return {}


@st.cache_data(ttl=_TTL_KURS, show_spinner=False)
def _roh_fast_info(ticker: str) -> dict:
    try:
        fi = yf.Ticker(ticker).fast_info
        return {k: fi.get(k) for k in fi.keys()}
    except Exception:  # noqa: BLE001
        return {}


@st.cache_data(ttl=_TTL_KURS, show_spinner="Lade Marktdaten …")
def lade_markt(symbol_oder_suche: str, historien_periode: str = "1y") -> MarktDaten:
    """Lädt alle Marktdaten zu einem Ticker **oder** Suchbegriff.

    Die Funktion wirft nicht: schlägt etwas fehl, steht der Grund in
    :attr:`MarktDaten.fehler` und die UI kann eine saubere Meldung zeigen.
    """
    begriff = (symbol_oder_suche or "").strip()
    if not begriff:
        return MarktDaten(ticker="", name="", fehler="Kein Suchbegriff angegeben.")

    treffer = suche(begriff, max_treffer=5)
    # Exakter Ticker-Treffer schlägt den ersten Suchtreffer
    kopf = next((t for t in treffer if t["symbol"].upper() == begriff.upper()), None)
    if kopf is None:
        kopf = treffer[0] if treffer else {
            "symbol": begriff.upper(), "name": begriff.upper(),
            "typ": "SONSTIGES", "boerse": "",
        }

    ticker = kopf["symbol"]
    fast = _roh_fast_info(ticker)
    info = _roh_info(ticker)

    if not fast and not info:
        return MarktDaten(
            ticker=ticker, name=kopf["name"],
            fehler=f"Yahoo Finance liefert gerade keine Daten für „{ticker}“.",
        )

    waehrung_original = fast.get("currency") or info.get("currency") or "EUR"
    letzter_kurs = _sicher(fast, "last_price") or _sicher(info, "currentPrice", "regularMarketPrice")
    vortag_kurs = _sicher(fast, "previous_close") or _sicher(info, "previousClose")

    typ = kopf.get("typ") or "SONSTIGES"
    if typ == "SONSTIGES":
        typ = _QUOTE_TYP_MAP.get((info.get("quoteType") or "").upper(), "SONSTIGES")

    historie = lade_historie(ticker, historien_periode).copy()
    if not historie.empty and waehrung_original == "GBp":
        for spalte in ("Open", "High", "Low", "Close"):
            if spalte in historie.columns:
                historie[spalte] = historie[spalte] / 100

    preis = in_euro(letzter_kurs, waehrung_original)
    if preis is None and not historie.empty:
        preis = in_euro(float(historie["Close"].iloc[-1]), waehrung_original)

    vortag = in_euro(vortag_kurs, waehrung_original)
    aenderung = None
    if preis and vortag:
        aenderung = (preis / vortag - 1) * 100

    daten = MarktDaten(
        ticker=ticker,
        name=info.get("longName") or info.get("shortName") or kopf["name"],
        typ=typ,
        preis=preis,
        preis_original=letzter_kurs,
        waehrung_original=waehrung_original,
        vortag=vortag,
        aenderung_pct=aenderung,
        historie=historie,
        boerse=kopf.get("boerse") or info.get("exchange", ""),
    )

    if not daten.preis:
        daten.fehler = f"Für „{ticker}“ ist aktuell kein Kurs verfügbar."
        return daten

    # --- Kennzahlen (alles optional, alles abgesichert) --------------------
    # Achtung LSE: Kurse stehen in Pence (GBp), Marktkapitalisierung und
    # Fondsvolumen dagegen in Pfund. Ohne diese Unterscheidung läge die
    # Marktkapitalisierung britischer Werte um den Faktor 100 daneben.
    waehrung_gross = "GBP" if waehrung_original == "GBp" else waehrung_original

    marktkap = _sicher(fast, "market_cap") or _sicher(info, "marketCap")
    daten.marktkapitalisierung = in_euro(marktkap, waehrung_gross) if marktkap else None

    aum = _sicher(info, "totalAssets", "netAssets", "fundTotalAssets")
    daten.fondsgroesse = in_euro(aum, waehrung_gross) if aum else None

    ziel = _sicher(info, "targetMeanPrice", "targetMedianPrice")
    daten.kursziel = in_euro(ziel, waehrung_original) if ziel else None

    hoch = _sicher(fast, "year_high") or _sicher(info, "fiftyTwoWeekHigh")
    tief = _sicher(fast, "year_low") or _sicher(info, "fiftyTwoWeekLow")
    daten.hoch_52w = in_euro(hoch, waehrung_original) if hoch else None
    daten.tief_52w = in_euro(tief, waehrung_original) if tief else None

    sma50 = _sicher(fast, "fifty_day_average") or _sicher(info, "fiftyDayAverage")
    sma200 = _sicher(fast, "two_hundred_day_average") or _sicher(info, "twoHundredDayAverage")
    daten.sma50 = in_euro(sma50, waehrung_original) if sma50 else None
    daten.sma200 = in_euro(sma200, waehrung_original) if sma200 else None

    daten.volumen = _sicher(fast, "last_volume", "ten_day_average_volume") or _sicher(
        info, "volume", "averageVolume"
    )

    daten.kgv = _sicher(info, "trailingPE", "forwardPE")
    daten.kbv = _sicher(info, "priceToBook")
    rendite = _sicher(info, "dividendYield")
    if rendite:
        # Yahoo liefert mal 0.0234, mal 2.34 – beides auf Prozent normieren
        daten.dividendenrendite = rendite * 100 if rendite < 1 else rendite
    daten.beta = _sicher(info, "beta", "beta3Year")
    daten.mitarbeiter = _sicher(info, "fullTimeEmployees")

    daten.sektor = info.get("sector") or ""
    daten.branche = info.get("industry") or ""
    daten.land = info.get("country") or ""
    daten.webseite = info.get("website") or ""
    daten.beschreibung = (info.get("longBusinessSummary") or "").strip()

    # --- Derivate: Hebel gegen den Basiswert ------------------------------
    if daten.ist_derivat:
        basis_symbol = info.get("underlyingSymbol") or ""
        if basis_symbol:
            basis_fast = _roh_fast_info(basis_symbol)
            basis_preis = in_euro(basis_fast.get("last_price"), basis_fast.get("currency", "EUR"))
            daten.basiswert = basis_symbol
            daten.basiswert_preis = basis_preis
            if basis_preis and daten.preis:
                daten.hebel = basis_preis / daten.preis

    # --- abgeleitete Statistik -------------------------------------------
    if not historie.empty:
        daten.performance = {
            "1 Woche": _performance(historie, 7),
            "1 Monat": _performance(historie, 30),
            "3 Monate": _performance(historie, 91),
            "6 Monate": _performance(historie, 182),
            "1 Jahr": _performance(historie, 365),
            "YTD": _ytd(historie),
        }
        daten.volatilitaet = _volatilitaet(historie)
        daten.max_drawdown = _max_drawdown(historie)

    return daten


@st.cache_data(ttl=_TTL_KURS, show_spinner=False)
def vergleichs_historie(ticker: tuple[str, ...], periode: str = "1y") -> pd.DataFrame:
    """Normalisierte Kursverläufe (Start = 100) für mehrere Ticker im Langformat."""
    teile = []
    for t in ticker:
        h = lade_historie(t, periode)
        if h.empty:
            continue
        basis = h["Close"].iloc[0]
        if not basis:
            continue
        teile.append(
            pd.DataFrame(
                {
                    "Datum": h["Datum"],
                    "Ticker": t,
                    "Index": h["Close"] / basis * 100,
                    "Kurs": h["Close"],
                }
            )
        )
    if not teile:
        return pd.DataFrame(columns=["Datum", "Ticker", "Index", "Kurs"])
    return pd.concat(teile, ignore_index=True)


def rueckblick(ticker: str, betrag: float, jahre: int) -> dict | None:
    """„Was wäre, wenn …“ – Wert eines Investments von vor ``jahre`` Jahren.

    Gibt ``None`` zurück, wenn die Historie nicht weit genug zurückreicht.
    """
    periode = "max" if jahre > 10 else f"{max(jahre, 1)}y"
    historie = lade_historie(ticker, periode)
    if historie.empty:
        return None

    ende = historie["Datum"].iloc[-1]
    ziel = ende - pd.Timedelta(days=int(jahre * 365.25))
    frueher = historie[historie["Datum"] <= ziel]
    if frueher.empty:
        return None

    startkurs = float(frueher["Close"].iloc[-1])
    endkurs = float(historie["Close"].iloc[-1])
    if startkurs <= 0:
        return None

    anteile = betrag / startkurs
    heute_wert = anteile * endkurs
    return {
        "startdatum": frueher["Datum"].iloc[-1].date(),
        "startkurs": startkurs,
        "endkurs": endkurs,
        "anteile": anteile,
        "wert_heute": heute_wert,
        "gewinn": heute_wert - betrag,
        "rendite_pct": (heute_wert / betrag - 1) * 100,
        "jahre": jahre,
        "cagr_pct": ((heute_wert / betrag) ** (1 / max(jahre, 1)) - 1) * 100,
    }


def heute() -> _dt.date:
    """Kleiner Wrapper – erleichtert das Einfrieren des Datums in Tests."""
    return _dt.date.today()
