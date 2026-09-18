"""OTTO Aktien-Matcher – was bekommst du für den Preis einer Aktie?

Start:
    streamlit run app.py

Aufbau:
    * ``kern.markt``       – Kurse & Kennzahlen von Yahoo Finance (gecacht)
    * ``kern.datenbank``   – OTTO-Produkte aus ``otto_produkte.db``
    * ``kern.matcher``     – Budget -> Produkt(e)
    * ``kern.diagramme``   – alle Charts
    * ``kern.theme``       – Design-System & UI-Bausteine

Diese Datei ist reine Komposition: Zustand, Layout, Interaktion.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from urllib.parse import urlencode

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from kern import theme  # noqa: E402  (muss vor jedem st-Aufruf importiert sein)

theme.seite_konfigurieren()  # MUSS der erste Streamlit-Aufruf sein

from kern import datenbank, diagramme, markt, matcher  # noqa: E402
from kern.formatierung import eur, kompakt, kurzname, prozent, zahl  # noqa: E402

# --------------------------------------------------------------------------- #
# Optionale Zusatzkomponenten – die App läuft auch ohne sie
# --------------------------------------------------------------------------- #
try:
    from streamlit_searchbox import st_searchbox

    HAT_SEARCHBOX = True
except ImportError:  # pragma: no cover
    HAT_SEARCHBOX = False

try:
    from st_copy import copy_button

    HAT_COPY = True
except ImportError:  # pragma: no cover
    HAT_COPY = False


APP_URL = "https://otto-aktien-matcher.streamlit.app/"

BELIEBTE_TICKER: list[tuple[str, str]] = [
    ("🍎 Apple", "AAPL"),
    ("🚗 Tesla", "TSLA"),
    ("🎮 Nvidia", "NVDA"),
    ("🅰️ Alphabet", "GOOGL"),
    ("📦 Amazon", "AMZN"),
    ("🏎️ Porsche", "P911.DE"),
    ("🛒 Zalando", "ZAL.DE"),
    ("✈️ Lufthansa", "LHA.DE"),
    ("🧱 Siemens", "SIE.DE"),
    ("🌍 MSCI World", "IWDA.AS"),
    ("₿ Bitcoin", "BTC-EUR"),
    ("🐶 Dogecoin", "DOGE-EUR"),
]

ZUFALLS_TICKER = [t for _, t in BELIEBTE_TICKER] + [
    "MSFT", "META", "NFLX", "SAP.DE", "BMW.DE", "ADS.DE", "RHM.DE", "ETH-EUR",
]


# --------------------------------------------------------------------------- #
# Zustand
# --------------------------------------------------------------------------- #
def zustand_initialisieren() -> None:
    standard = {
        "theme_modus": "Automatisch",
        "animationen": True,
        "watchlist": [],
        "verlauf": [],
        "aktiver_ticker": None,
        "menge": 1,
    }
    for schluessel, wert in standard.items():
        st.session_state.setdefault(schluessel, wert)


def ist_dunkel() -> bool:
    """Soll dunkel gerendert werden?

    Standard ist „Automatisch": dann folgt die App dem Theme, das Streamlit
    gerade benutzt (Menü → Settings → Theme). Nur so passen auch Eingabefelder,
    Tabellen und Menüs zum Rest – die rendert Streamlit nämlich selbst.
    """
    modus = st.session_state.get("theme_modus", "Automatisch")
    if modus == "Dunkel":
        return True
    if modus == "Hell":
        return False
    try:
        return (st.context.theme.type or "light").lower() == "dark"
    except Exception:  # noqa: BLE001 – ältere Streamlit-Versionen
        return False


def ticker_merken(ticker: str) -> None:
    """Zuletzt angesehene Werte vorhalten (max. 8, neueste zuerst)."""
    if not ticker:
        return
    verlauf: list[str] = st.session_state["verlauf"]
    if ticker in verlauf:
        verlauf.remove(ticker)
    verlauf.insert(0, ticker)
    st.session_state["verlauf"] = verlauf[:8]


def ticker_setzen(ticker: str) -> None:
    """Ticker merken und in die URL schreiben.

    Der Vergleich vor dem Schreiben ist wichtig: eine Zuweisung an
    ``st.query_params`` löst einen Rerun aus – ohne Guard drehte sich die App
    im Kreis, weil die Suchbox nach dem Rerun denselben Wert zurückgibt.
    """
    st.session_state["aktiver_ticker"] = ticker
    if st.query_params.get("ticker") != ticker:
        st.query_params["ticker"] = ticker


# --------------------------------------------------------------------------- #
# Seitenleiste
# --------------------------------------------------------------------------- #
def seitenleiste(produkte_alle: pd.DataFrame) -> tuple[str | None, matcher.Filter, dict]:
    """Baut die Seitenleiste und liefert (Ticker, Filter, Darstellungsoptionen)."""
    with st.sidebar:
        logo = theme.logo_data_uri()
        if logo:
            st.markdown(
                f'<div style="text-align:center;margin-bottom:6px">'
                f'<a href="{APP_URL}" target="_self"><img src="{logo}" width="150"/></a></div>',
                unsafe_allow_html=True,
            )
        st.markdown(
            '<div style="text-align:center;font-weight:800;letter-spacing:.14em;'
            'font-size:.72rem;text-transform:uppercase;color:var(--text-zart);'
            'margin-bottom:14px">Aktien-Matcher</div>',
            unsafe_allow_html=True,
        )

        # ---------------------------------------------------------- Suche
        st.markdown("#### 🔎 Wertpapier")
        gewaehlt = None
        if HAT_SEARCHBOX:
            gewaehlt = st_searchbox(
                markt.such_vorschlaege,
                placeholder="Aktie, ETF oder Krypto suchen …",
                key="aktien_suchbox",
                clear_on_submit=False,
            )
        else:
            eingabe = st.text_input(
                "Ticker oder Firmenname",
                placeholder="z. B. AAPL oder Apple",
                label_visibility="collapsed",
            )
            if eingabe:
                treffer = markt.suche(eingabe, max_treffer=8)
                if treffer:
                    gewaehlt = st.selectbox(
                        "Treffer",
                        [t["symbol"] for t in treffer],
                        format_func=lambda s: next(
                            (f"{t['symbol']} — {t['name']}" for t in treffer if t["symbol"] == s), s
                        ),
                    )

        # ------------------------------------------------- Schnellauswahl
        with st.expander("⚡ Schnellauswahl", expanded=not st.session_state["aktiver_ticker"]):
            spalten = st.columns(2)
            for i, (label, symbol) in enumerate(BELIEBTE_TICKER):
                if spalten[i % 2].button(label, key=f"schnell_{symbol}", width="stretch"):
                    gewaehlt = symbol
            if st.button("🎲 Überrasch mich", width="stretch", type="primary"):
                gewaehlt = random.choice(ZUFALLS_TICKER)

        if st.session_state["verlauf"]:
            with st.expander("🕘 Zuletzt angesehen"):
                for symbol in st.session_state["verlauf"]:
                    if st.button(symbol, key=f"verlauf_{symbol}", width="stretch"):
                        gewaehlt = symbol

        st.divider()

        # ---------------------------------------------------------- Budget
        st.markdown("#### 💰 Budget")
        menge = st.number_input(
            "Anzahl Anteile",
            min_value=1, max_value=10_000,
            value=int(st.session_state["menge"]),
            step=1,
            key="menge_eingabe",
            help="Das Budget ist Kurs × Anzahl. Mit 10 Apple-Aktien kaufst du deutlich mehr ein.",
        )
        st.session_state["menge"] = int(menge)

        st.divider()

        # ---------------------------------------------------------- Filter
        st.markdown("#### 🎛️ Produktfilter")
        daten_liste = datenbank.verfuegbare_daten()
        datum = None
        if len(daten_liste) > 1:
            datum = st.selectbox("Datenstand", daten_liste, index=0)
        elif daten_liste:
            datum = daten_liste[0]

        basis = produkte_alle[produkte_alle["scraped_date"] == datum] if datum is not None \
            else produkte_alle

        if basis.empty:
            f = matcher.Filter(datum=datum)
            st.caption("Keine Produkte für diesen Stand.")
        else:
            max_p = float(basis["preis"].max())
            spanne = st.slider(
                "Preisspanne (€)",
                min_value=0.0, max_value=float(round(max_p + 1)),
                value=(0.0, float(round(max_p + 1))),
                step=float(max(1.0, round(max_p / 200))),
                format="%.0f",
            )
            min_bewertung = st.select_slider(
                "Mindestbewertung",
                options=[0.0, 3.0, 3.5, 4.0, 4.5, 5.0],
                value=0.0,
                format_func=lambda v: "egal" if v == 0 else f"ab {v:.1f} ★".replace(".", ","),
            )
            nur_rabatt = st.toggle("Nur reduzierte Artikel", value=False)
            nur_bild = st.toggle("Nur mit Produktbild", value=True)

            with st.expander("Marken & Kategorien"):
                gewaehlte_marken = st.multiselect(
                    "Marken", datenbank.marken(basis), placeholder="alle Marken"
                )
                gewaehlte_kategorien = st.multiselect(
                    "Kategorien", datenbank.suchbegriffe(basis), placeholder="alle Kategorien"
                )

            f = matcher.Filter(
                min_preis=spanne[0],
                max_preis=spanne[1],
                min_bewertung=min_bewertung,
                nur_rabatt=nur_rabatt,
                nur_mit_bild=nur_bild,
                marken=tuple(gewaehlte_marken),
                kategorien=tuple(gewaehlte_kategorien),
                datum=datum,
            )

        st.divider()

        # ----------------------------------------------------- Darstellung
        st.markdown("#### 🎨 Darstellung")
        # key= statt value=: so steht der neue Wert schon vor dem Skriptlauf
        # im Session-State und das Stylesheet passt im selben Rerun.
        st.radio(
            "Farbschema", ["Automatisch", "Hell", "Dunkel"],
            key="theme_modus", horizontal=True,
            help="„Automatisch\u201c folgt dem Streamlit-Theme (Menü → Settings → Theme) "
                 "und hält damit auch Eingabefelder und Tabellen passend.",
        )
        st.toggle("Animationen", key="animationen")
        karten_pro_reihe = st.select_slider("Karten pro Reihe", options=[2, 3, 4], value=3)

        st.divider()
        kz = datenbank.kennzahlen()
        st.caption(
            f"📦 **{zahl(kz.anzahl, 0)}** Produkte · **{kz.suchbegriffe}** Kategorien\n\n"
            f"🗓️ Stand: **{kz.stand}**\n\n"
            f"💶 {eur(kz.guenstigstes)} – {eur(kz.teuerstes)}"
        )
        if st.button("🔄 Daten neu laden", width="stretch"):
            st.cache_data.clear()
            st.rerun()

    darstellung = {
        "dunkel": ist_dunkel(),
        "animationen": st.session_state["animationen"],
        "spalten": karten_pro_reihe if not basis.empty else 3,
    }
    return gewaehlt, f, darstellung


# --------------------------------------------------------------------------- #
# Startbildschirm
# --------------------------------------------------------------------------- #
def startbildschirm(produkte: pd.DataFrame) -> None:
    kz = datenbank.kennzahlen()

    theme.kpi_reihe(
        [
            {"label": "Produkte im Index", "wert": zahl(kz.anzahl, 0), "icon": "📦",
             "hinweis": f"aus {kz.suchbegriffe} Kategorien"},
            {"label": "Günstigstes Teil", "wert": eur(kz.guenstigstes), "icon": "🪙"},
            {"label": "Teuerstes Teil", "wert": eur(kz.teuerstes), "icon": "💎"},
            {"label": "Ø Preis", "wert": eur(kz.durchschnitt), "icon": "📊",
             "hinweis": f"Median {eur(kz.median)}"},
            {"label": "Reduziert", "wert": zahl(kz.mit_rabatt, 0), "icon": "🏷️",
             "hinweis": f"bis −{kz.groesster_rabatt} %" if kz.groesster_rabatt else ""},
        ]
    )

    theme.leer_zustand(
        "🔎",
        "Such dir ein Wertpapier aus",
        "Links in der Seitenleiste suchen oder unten direkt draufklicken – "
        "dann rechnen wir den Kurs in echte Dinge um.",
    )

    theme.abschnitt("Direkt loslegen", "Ein Klick genügt.")
    spalten = st.columns(6)
    for i, (label, symbol) in enumerate(BELIEBTE_TICKER):
        if spalten[i % 6].button(label, key=f"start_{symbol}", width="stretch"):
            ticker_setzen(symbol)
            st.rerun()

    if not produkte.empty:
        theme.abschnitt("Was gerade im Sortiment liegt", "Die teuersten Fundstücke des letzten Scrapes.")
        spitzenreiter = produkte.nlargest(4, "preis")
        theme.produkt_raster(
            [datenbank.als_produkt(z) for _, z in spitzenreiter.iterrows()],
            spalten=4,
            baender=["TEUERSTES", "", "", ""],
        )


# --------------------------------------------------------------------------- #
# Tab 1: Matcher
# --------------------------------------------------------------------------- #
def tab_matcher(daten: markt.MarktDaten, budget: float, produkte: pd.DataFrame,
                link_produkte: list[str], darstellung: dict) -> tuple[pd.Series | None, list]:
    dunkel = darstellung["dunkel"]

    if produkte.empty:
        theme.leer_zustand(
            "🫙", "Keine Produkte im Filter",
            "Die aktuellen Filter lassen nichts übrig. Setz die Preisspanne weiter "
            "oder deaktiviere ein paar Häkchen in der Seitenleiste.",
        )
        return None, []

    # --- Hauptprodukt ------------------------------------------------------
    if link_produkte:
        haupt_zeile = datenbank.produkt_nach_url(link_produkte[0])
        if haupt_zeile is None:
            haupt_zeile = matcher.finde_hauptprodukt(produkte, budget)
    else:
        haupt_zeile = matcher.finde_hauptprodukt(produkte, budget)

    if haupt_zeile is None:
        guenstigstes = produkte["preis"].min()
        theme.leer_zustand(
            "😅", "Dafür reicht es (noch) nicht",
            f"Mit {eur(budget)} kommst du an keinen Artikel im Filter heran – "
            f"das günstigste kostet {eur(guenstigstes)}. Erhöh die Anzahl Anteile "
            "in der Seitenleiste.",
        )
        return None, []

    haupt = datenbank.als_produkt(haupt_zeile)
    rest = round(budget - float(haupt_zeile["preis"]), 2)

    # --- Alternativen ------------------------------------------------------
    if link_produkte and len(link_produkte) > 1:
        alternativen = []
        for url in link_produkte[1:4]:
            zeile = datenbank.produkt_nach_url(url)
            if zeile is not None:
                alternativen.append(
                    matcher.Treffer(zeile, matcher.vielfaches(zeile["preis"], budget, 2))
                )
    else:
        alternativen = matcher.finde_alternativen(
            produkte, budget, ausschluss_urls=(str(haupt_zeile["produkt_url"]),), anzahl=3
        )

    # --- Kernaussage -------------------------------------------------------
    anteil_text = "die Aktie" if st.session_state["menge"] == 1 else \
        f"{st.session_state['menge']} Anteile"
    theme.aussage(
        f"Statt <em>{anteil_text}</em> von {daten.name} könntest du dir "
        f"<em>{kurzname(haupt.title, haupt.brand)}</em> kaufen.",
        zusatz=(
            f"Und hättest davon noch {eur(rest)} übrig."
            if rest > 0 else "Damit ist das Budget exakt aufgebraucht."
        ),
    )

    links, rechts = st.columns([1.25, 1], gap="large")

    # --- links: Wertpapier -------------------------------------------------
    with links:
        theme.abschnitt(f"{daten.typ_label} · {daten.ticker}", daten.name)

        theme.kpi_reihe(
            [
                {"label": "Aktueller Kurs", "wert": eur(daten.preis), "icon": "💶",
                 "delta": daten.aenderung_pct, "hinweis": "gegenüber Vortag"},
                {"label": "Dein Budget", "wert": eur(budget), "icon": "🧮",
                 "hinweis": f"{st.session_state['menge']} × Kurs"},
            ]
            + ([{"label": daten.groesse_label, "wert": kompakt(daten.groesse), "icon": "🏛️",
                 "hinweis": daten.groesse_erklaerung}]
               if daten.groesse else [])
        )

        chart = diagramme.kursverlauf(daten.historie, dunkel=dunkel, hoehe=290)
        if chart is not None:
            st.altair_chart(chart, width="stretch", theme=None)
        else:
            st.info("Für diesen Wert liegt keine Kurshistorie vor.")

        weitere = []
        if daten.kursziel:
            weitere.append(
                {"label": "Analysten-Kursziel", "wert": eur(daten.kursziel), "icon": "🎯",
                 "delta": daten.kurszielpotenzial, "hinweis": "12-Monats-Schätzung"}
            )
        if daten.hoch_52w and daten.tief_52w:
            weitere.append(
                {"label": "52-Wochen-Spanne", "wert": f"{eur(daten.tief_52w)} – {eur(daten.hoch_52w)}",
                 "icon": "📏",
                 "hinweis": f"aktuell bei {prozent(daten.position_in_52w_spanne, 0, False)} der Spanne"
                 if daten.position_in_52w_spanne is not None else ""}
            )
        if daten.volatilitaet:
            weitere.append(
                {"label": "Volatilität (1 J.)", "wert": prozent(daten.volatilitaet, 1, False),
                 "icon": "🌊", "hinweis": "annualisiert"}
            )
        if weitere:
            theme.kpi_reihe(weitere)

        if daten.ist_derivat:
            st.markdown("")
            theme.hinweis(
                f"🎢 <b>GIG – Gehebelt ist Geil.</b> Hebel: "
                f"<b>{zahl(daten.hebel, 2) if daten.hebel else '–'}</b>"
                + (f" gegenüber {daten.basiswert}" if daten.basiswert else ""),
                art="warnung",
            )
            audio = Path(__file__).resolve().parent / "g-i-g.mp3"
            if audio.exists():
                st.audio(str(audio), format="audio/mp3", autoplay=True)

    # --- rechts: Hauptprodukt ---------------------------------------------
    with rechts:
        theme.abschnitt("Dein Gegenwert", "Das teuerste Teil, das gerade noch reinpasst.")
        theme.produktkarte(haupt, band="BESTES MATCH")
        theme.fortschrittsbalken(
            float(haupt_zeile["preis"]) / budget * 100 if budget else 0,
            links=f"Produkt {eur(haupt_zeile['preis'])}",
            rechts=f"Rest {eur(rest)}",
        )
        if haupt_zeile.get("rabatt_pct", 0):
            theme.hinweis(
                f"🏷️ Gerade <b>−{int(haupt_zeile['rabatt_pct'])} %</b> reduziert – "
                f"du sparst {eur(float(haupt_zeile['ersparnis']))} gegenüber der UVP.",
                art="gut",
            )

    # --- Alternativen ------------------------------------------------------
    if alternativen:
        namen = [f"**{t.anzahl}× {t.titel}**" for t in alternativen]
        beschreibung = (
            ", ".join(namen[:-1]) + f" oder {namen[-1]}" if len(namen) > 1 else namen[0]
        )
        theme.abschnitt("Oder lieber gleich mehrfach?", f"Alternativ auch {beschreibung}.")
        theme.produkt_raster(
            [datenbank.als_produkt(t.zeile) for t in alternativen],
            spalten=min(len(alternativen), darstellung["spalten"]),
            baender=[f"{t.anzahl}× DRIN" for t in alternativen],
            anzahlen=[t.anzahl for t in alternativen],
        )

    # --- Spaßfakten --------------------------------------------------------
    theme.abschnitt("Zahlen zum Angeben", "Dasselbe Budget, andere Maßstäbe.")
    guenstigstes = float(produkte["preis"].min())
    median = float(produkte["preis"].median())
    theme.kpi_reihe(
        [
            {"label": "Günstigste Teile", "icon": "🛒",
             "wert": zahl(int(budget // guenstigstes), 0) + "×",
             "hinweis": f"je {eur(guenstigstes)}"},
            {"label": "Median-Produkte", "icon": "📐",
             "wert": zahl(int(budget // median), 0) + "×",
             "hinweis": f"je {eur(median)}"},
            {"label": "Volle Warenkörbe", "icon": "🧺",
             "wert": zahl(max(1, int(budget // max(median * 5, 1))), 0) + "×",
             "hinweis": "zu je 5 Artikeln"},
            {"label": "Budget pro Tag", "icon": "📅",
             "wert": eur(budget / 365),
             "hinweis": "über ein Jahr verteilt"},
        ]
    )

    return haupt_zeile, alternativen


# --------------------------------------------------------------------------- #
# Tab 2: Warenkorb
# --------------------------------------------------------------------------- #
def tab_warenkorb(budget: float, produkte: pd.DataFrame, darstellung: dict) -> None:
    theme.abschnitt(
        "Warenkorb-Optimierer",
        "Reizt das Budget mit möglichst vielen verschiedenen Produkten aus.",
    )

    if produkte.empty or budget <= 0:
        theme.leer_zustand("🧺", "Nichts zu packen", "Erst ein Wertpapier wählen, dann füllt sich der Korb.")
        return

    steuerung = st.columns([1, 1, 2])
    max_positionen = steuerung[0].slider("Maximale Positionen", 3, 25, 10)
    mehrfach = steuerung[1].toggle("Restgeld in Mehrfachkäufe stecken", value=True)

    korb = matcher.baue_warenkorb(produkte, budget, max_positionen, mehrfach)
    if not korb:
        theme.leer_zustand(
            "🤷", "Kein Produkt passt ins Budget",
            f"Selbst das günstigste Teil im Filter kostet mehr als {eur(budget)}.",
        )
        return

    art, spruch = matcher.budget_ampel(korb.ausnutzung)

    theme.kpi_reihe(
        [
            {"label": "Budget", "wert": eur(korb.budget), "icon": "💰"},
            {"label": "Im Warenkorb", "wert": eur(korb.summe), "icon": "🧺",
             "hinweis": f"{korb.stueckzahl} Artikel in {len(korb.positionen)} Positionen"},
            {"label": "Restgeld", "wert": eur(korb.rest), "icon": "🪙"},
            {"label": "Ausnutzung", "wert": prozent(korb.ausnutzung, 1, False), "icon": "🎯",
             "hinweis": spruch},
        ]
    )

    links, rechts = st.columns([2.6, 1], gap="large")
    with links:
        theme.fortschrittsbalken(
            korb.ausnutzung,
            links=f"{eur(korb.summe)} verplant",
            rechts=f"{eur(korb.rest)} übrig",
        )
        tabelle = pd.DataFrame(
            [
                {
                    "Artikel": t.titel,
                    "Marke": str(t.zeile.get("marke", "")),
                    "Kategorie": str(t.zeile.get("suchbegriff", "")),
                    "Stück": t.anzahl,
                    "Einzelpreis": t.preis,
                    "Gesamt": t.gesamt,
                    "Bewertung": t.zeile.get("bewertung"),
                    "Link": t.url,
                }
                for t in korb.positionen
            ]
        )
        st.dataframe(
            tabelle,
            width="stretch",
            hide_index=True,
            column_config={
                "Einzelpreis": st.column_config.NumberColumn(format="%.2f €"),
                "Gesamt": st.column_config.NumberColumn(format="%.2f €"),
                "Bewertung": st.column_config.NumberColumn(format="%.1f ★"),
                "Link": st.column_config.LinkColumn("OTTO", display_text="ansehen ↗"),
            },
        )
        st.download_button(
            "⬇️ Warenkorb als CSV",
            tabelle.to_csv(index=False).encode("utf-8-sig"),
            file_name="otto-warenkorb.csv",
            mime="text/csv",
        )

    with rechts:
        ring = diagramme.budget_donut(korb.summe, max(korb.rest, 0), dunkel=darstellung["dunkel"])
        if ring is not None:
            st.altair_chart(ring, width="stretch", theme=None)
        theme.hinweis(spruch, art={"gut": "gut", "ok": "info", "schwach": "warnung"}[art])

    theme.abschnitt("Der Korb im Überblick")
    theme.produkt_raster(
        [datenbank.als_produkt(t.zeile) for t in korb.positionen],
        spalten=darstellung["spalten"],
        anzahlen=[t.anzahl for t in korb.positionen],
        baender=[f"{t.anzahl}×" if t.anzahl > 1 else "" for t in korb.positionen],
    )


# --------------------------------------------------------------------------- #
# Tab 3: Aktien-Analyse
# --------------------------------------------------------------------------- #
def tab_analyse(daten: markt.MarktDaten, produkte: pd.DataFrame, darstellung: dict) -> None:
    dunkel = darstellung["dunkel"]

    theme.abschnitt(f"{daten.name}", f"{daten.typ_label} · {daten.ticker}"
                    + (f" · {daten.boerse}" if daten.boerse else ""))

    kennzahlen = [
        {"label": "Kurs", "wert": eur(daten.preis), "delta": daten.aenderung_pct, "icon": "💶"},
    ]
    if daten.groesse:
        kennzahlen.append(
            {"label": daten.groesse_label, "wert": kompakt(daten.groesse), "icon": "🏛️",
             "hinweis": daten.groesse_erklaerung}
        )
    if daten.kgv:
        kennzahlen.append({"label": "KGV", "wert": zahl(daten.kgv, 1), "icon": "⚖️"})
    if daten.dividendenrendite:
        kennzahlen.append({"label": "Dividendenrendite",
                           "wert": prozent(daten.dividendenrendite, 2, False), "icon": "💸"})
    if daten.beta:
        kennzahlen.append({"label": "Beta", "wert": zahl(daten.beta, 2), "icon": "📐",
                           "hinweis": "Schwankung ggü. Markt"})
    if daten.max_drawdown:
        kennzahlen.append({"label": "Max. Drawdown", "wert": prozent(daten.max_drawdown, 1, False),
                           "icon": "🕳️", "hinweis": "im gezeigten Zeitraum"})
    if daten.volumen:
        kennzahlen.append({"label": "Volumen", "wert": kompakt(daten.volumen, "Stk."), "icon": "🔁"})
    theme.kpi_reihe(kennzahlen)

    # --- Chart mit Zeitraum & Darstellung ---------------------------------
    steuerung = st.columns([2, 1])
    periode_label = steuerung[0].radio(
        "Zeitraum", list(markt.PERIODEN.keys()), index=3, horizontal=True,
        label_visibility="collapsed",
    )
    darstellungsart = steuerung[1].radio(
        "Darstellung", ["Linie", "Kerzen"], horizontal=True, label_visibility="collapsed"
    )

    historie = markt.lade_historie(daten.ticker, markt.PERIODEN[periode_label])
    if historie.empty:
        st.info("Keine Kurshistorie verfügbar.")
    else:
        if darstellungsart == "Kerzen":
            chart = diagramme.kerzen_chart(historie, dunkel=dunkel, hoehe=380)
        else:
            chart = diagramme.kursverlauf(historie, dunkel=dunkel, hoehe=380)
        if chart is not None:
            st.altair_chart(chart, width="stretch", theme=None)

    links, rechts = st.columns(2, gap="large")
    with links:
        theme.abschnitt("Rendite nach Zeitraum")
        chart = diagramme.performance_balken(daten.performance, dunkel=dunkel)
        if chart is not None:
            st.altair_chart(chart, width="stretch", theme=None)
        else:
            st.info("Zu wenig Historie für eine Renditeübersicht.")

    with rechts:
        theme.abschnitt("Zeitmaschine", "Was wäre aus dem Preis eines Produkts geworden?")
        if produkte.empty:
            st.info("Ohne Produktdaten keine Zeitreise.")
        else:
            standard = float(produkte["preis"].median())
            betrag = st.number_input(
                "Investierter Betrag (€)", min_value=1.0, value=round(standard, 2), step=10.0
            )
            jahre = st.select_slider("Rückblick", options=[1, 2, 3, 5, 10], value=3)
            ergebnis = markt.rueckblick(daten.ticker, betrag, jahre)
            if ergebnis is None:
                st.info(f"Die Historie von {daten.ticker} reicht keine {jahre} Jahre zurück.")
            else:
                theme.kpi_reihe(
                    [
                        {"label": "Wert heute", "wert": eur(ergebnis["wert_heute"]), "icon": "💰",
                         "delta": ergebnis["rendite_pct"]},
                        {"label": "Gewinn / Verlust", "wert": eur(ergebnis["gewinn"]), "icon": "📈"},
                        {"label": "Rendite p. a.", "wert": prozent(ergebnis["cagr_pct"], 1),
                         "icon": "🧮", "hinweis": f"seit {ergebnis['startdatum']:%d.%m.%Y}"},
                    ]
                )
                theme.hinweis(
                    f"Für {eur(betrag)} hättest du am {ergebnis['startdatum']:%d.%m.%Y} rund "
                    f"<b>{zahl(ergebnis['anteile'], 4)}</b> Anteile bekommen – heute "
                    f"<b>{eur(ergebnis['wert_heute'])}</b> wert.",
                    art="gut" if ergebnis["gewinn"] >= 0 else "schlecht",
                )

    # --- Profil -----------------------------------------------------------
    if daten.beschreibung or daten.sektor or daten.webseite:
        with st.expander("🏢 Unternehmensprofil"):
            merkmale = []
            for label, wert in (
                ("Sektor", daten.sektor), ("Branche", daten.branche),
                ("Land", daten.land),
                ("Mitarbeitende", zahl(daten.mitarbeiter, 0) if daten.mitarbeiter else ""),
            ):
                if wert:
                    merkmale.append(f"{label}: {wert}")
            theme.chips(merkmale, neutral=True)
            if daten.beschreibung:
                st.write(daten.beschreibung)
            if daten.webseite:
                st.link_button("Zur Unternehmensseite ↗", daten.webseite)


# --------------------------------------------------------------------------- #
# Tab 4: Produkt-Explorer
# --------------------------------------------------------------------------- #
def tab_explorer(produkte: pd.DataFrame, budget: float, darstellung: dict) -> None:
    theme.abschnitt("Produkt-Explorer", "Der komplette OTTO-Datenbestand – such, sortier, filter.")

    if produkte.empty:
        theme.leer_zustand("🗃️", "Keine Produkte", "Die Filter in der Seitenleiste sind zu streng.")
        return

    kopf = st.columns([2, 1, 1, 1])
    suchtext = kopf[0].text_input("Volltextsuche", placeholder="z. B. Teppich, Apple, Kissen …")
    sortierung = kopf[1].selectbox(
        "Sortierung",
        ["Preis absteigend", "Preis aufsteigend", "Beste Bewertung",
         "Größter Rabatt", "Meiste Bewertungen"],
    )
    ansicht = kopf[2].selectbox("Ansicht", ["Karten", "Tabelle"])
    limit = kopf[3].slider("Anzahl", 6, 60, 12, step=6)

    gefiltert = produkte
    if suchtext.strip():
        begriff = suchtext.strip().lower()
        maske = (
            gefiltert["titel"].str.lower().str.contains(begriff, regex=False)
            | gefiltert["marke"].str.lower().str.contains(begriff, regex=False)
            | gefiltert["suchbegriff"].str.lower().str.contains(begriff, regex=False)
        )
        gefiltert = gefiltert[maske]

    if budget > 0:
        nur_bezahlbar = st.toggle(
            f"Nur zeigen, was ins Budget von {eur(budget)} passt", value=False
        )
        if nur_bezahlbar:
            gefiltert = gefiltert[gefiltert["preis"] <= budget]

    sortier_map = {
        "Preis absteigend": ("preis", False),
        "Preis aufsteigend": ("preis", True),
        "Beste Bewertung": ("bewertung", False),
        "Größter Rabatt": ("rabatt_pct", False),
        "Meiste Bewertungen": ("anzahl_bewertungen", False),
    }
    spalte, aufsteigend = sortier_map[sortierung]
    gefiltert = gefiltert.sort_values(spalte, ascending=aufsteigend, na_position="last")

    st.caption(f"**{zahl(len(gefiltert), 0)}** Treffer · zeige die ersten {min(limit, len(gefiltert))}")

    if gefiltert.empty:
        theme.leer_zustand("🔍", "Nichts gefunden", "Probier einen anderen Suchbegriff.")
        return

    ausschnitt = gefiltert.head(limit)

    if ansicht == "Tabelle":
        st.dataframe(
            ausschnitt[["kurztitel", "marke", "suchbegriff", "preis", "old_price",
                        "rabatt_pct", "bewertung", "anzahl_bewertungen", "produkt_url"]]
            .rename(columns={
                "kurztitel": "Artikel", "marke": "Marke", "suchbegriff": "Kategorie",
                "preis": "Preis", "old_price": "UVP", "rabatt_pct": "Rabatt %",
                "bewertung": "Bewertung", "anzahl_bewertungen": "Rezensionen",
                "produkt_url": "Link",
            }),
            width="stretch", hide_index=True,
            column_config={
                "Preis": st.column_config.NumberColumn(format="%.2f €"),
                "UVP": st.column_config.NumberColumn(format="%.2f €"),
                "Bewertung": st.column_config.NumberColumn(format="%.1f ★"),
                "Link": st.column_config.LinkColumn("OTTO", display_text="ansehen ↗"),
            },
        )
    else:
        theme.produkt_raster(
            [datenbank.als_produkt(z) for _, z in ausschnitt.iterrows()],
            spalten=darstellung["spalten"],
        )

    st.download_button(
        "⬇️ Auswahl als CSV",
        gefiltert.drop(columns=["datum"], errors="ignore").to_csv(index=False).encode("utf-8-sig"),
        file_name="otto-produkte.csv",
        mime="text/csv",
    )


# --------------------------------------------------------------------------- #
# Tab 5: Insights
# --------------------------------------------------------------------------- #
def tab_insights(produkte: pd.DataFrame, alle: pd.DataFrame, darstellung: dict) -> None:
    dunkel = darstellung["dunkel"]
    kz = datenbank.kennzahlen()

    theme.abschnitt("Marktdaten OTTO", f"Stand {kz.stand} · {zahl(kz.anzahl, 0)} Datensätze")
    theme.kpi_reihe(
        [
            {"label": "Produkte", "wert": zahl(kz.anzahl, 0), "icon": "📦"},
            {"label": "Kategorien", "wert": zahl(kz.suchbegriffe, 0), "icon": "🗂️"},
            {"label": "Marken", "wert": zahl(kz.marken, 0), "icon": "🏷️"},
            {"label": "Median-Preis", "wert": eur(kz.median), "icon": "📐"},
            {"label": "Reduziert", "wert": zahl(kz.mit_rabatt, 0), "icon": "🔻",
             "hinweis": f"bis −{kz.groesster_rabatt} %" if kz.groesster_rabatt else ""},
            {"label": "Scrape-Tage", "wert": zahl(kz.tage_historie, 0), "icon": "🗓️"},
        ]
    )

    if produkte.empty:
        theme.leer_zustand("📉", "Keine Daten im Filter", "Filter lockern, dann gibt es Diagramme.")
        return

    links, rechts = st.columns(2, gap="large")
    with links:
        theme.abschnitt("Preisverteilung", "Wo liegt die Masse des Sortiments?")
        chart = diagramme.preis_histogramm(produkte, dunkel=dunkel)
        if chart is not None:
            st.altair_chart(chart, width="stretch", theme=None)
    with rechts:
        theme.abschnitt("Preis vs. Bewertung", "Punktgröße = Anzahl Rezensionen.")
        chart = diagramme.bewertung_streuung(produkte, dunkel=dunkel)
        if chart is not None:
            st.altair_chart(chart, width="stretch", theme=None)
        else:
            st.info("Keine bewerteten Produkte im Filter.")

    links, rechts = st.columns(2, gap="large")
    with links:
        theme.abschnitt("Häufigste Marken")
        chart = diagramme.kategorie_balken(produkte, "marke", "Marke", dunkel=dunkel, top=12)
        if chart is not None:
            st.altair_chart(chart, width="stretch", theme=None)
    with rechts:
        theme.abschnitt("Teuerste Kategorien", "Durchschnittspreis je Suchbegriff.")
        chart = diagramme.kategorie_balken(
            produkte, "suchbegriff", "Kategorie", dunkel=dunkel, top=12, aggregat="preis"
        )
        if chart is not None:
            st.altair_chart(chart, width="stretch", theme=None)

    theme.abschnitt("Die größten Rabatte")
    schnaeppchen = produkte[produkte["rabatt_pct"] > 0].nlargest(4, "rabatt_pct")
    if schnaeppchen.empty:
        st.info("Im aktuellen Filter ist nichts reduziert.")
    else:
        theme.produkt_raster(
            [datenbank.als_produkt(z) for _, z in schnaeppchen.iterrows()],
            spalten=4,
            baender=[f"−{int(z['rabatt_pct'])} %" for _, z in schnaeppchen.iterrows()],
        )

    if kz.tage_historie > 1:
        theme.abschnitt("Preisentwicklung im Zeitverlauf", "Median aller Produkte je Scrape-Tag.")
        verlauf = alle.groupby("scraped_date")["preis"].median().reset_index()
        st.line_chart(verlauf.set_index("scraped_date"), height=240)


# --------------------------------------------------------------------------- #
# Tab 6: Watchlist
# --------------------------------------------------------------------------- #
def tab_watchlist(aktueller_ticker: str | None, darstellung: dict) -> None:
    theme.abschnitt("Watchlist", "Mehrere Werte nebeneinander – normiert auf Startwert 100.")

    watchlist: list[str] = st.session_state["watchlist"]

    steuerung = st.columns([2, 1, 1])
    neu = steuerung[0].text_input("Ticker hinzufügen", placeholder="z. B. MSFT")
    if steuerung[1].button("➕ Hinzufügen", width="stretch") and neu.strip():
        symbol = neu.strip().upper()
        if symbol not in watchlist:
            watchlist.append(symbol)
            st.session_state["watchlist"] = watchlist[:8]
            st.rerun()
    if aktueller_ticker and steuerung[2].button(
        f"➕ {aktueller_ticker}", width="stretch"
    ):
        if aktueller_ticker not in watchlist:
            watchlist.append(aktueller_ticker)
            st.session_state["watchlist"] = watchlist[:8]
            st.rerun()

    if not watchlist:
        theme.leer_zustand(
            "⭐", "Watchlist ist leer",
            "Füge bis zu acht Werte hinzu und vergleiche ihre Entwicklung direkt miteinander.",
        )
        return

    entfernen = st.multiselect("Entfernen", watchlist, placeholder="nichts entfernen")
    if entfernen:
        st.session_state["watchlist"] = [t for t in watchlist if t not in entfernen]
        st.rerun()

    periode_label = st.radio(
        "Zeitraum", list(markt.PERIODEN.keys()), index=3, horizontal=True,
        label_visibility="collapsed", key="watchlist_periode",
    )

    lang = markt.vergleichs_historie(tuple(watchlist), markt.PERIODEN[periode_label])
    if lang.empty:
        st.warning("Für keinen der Werte gibt es Kursdaten.")
        return

    chart = diagramme.vergleichs_chart(lang, dunkel=darstellung["dunkel"], hoehe=400)
    if chart is not None:
        st.altair_chart(chart, width="stretch", theme=None)

    theme.abschnitt("Direktvergleich")
    zeilen = []
    for symbol in watchlist:
        d = markt.lade_markt(symbol)
        if d.fehler:
            continue
        zeilen.append(
            {
                "Ticker": d.ticker,
                "Name": d.name,
                "Typ": d.typ_label,
                "Kurs (€)": d.preis,
                "Tag %": d.aenderung_pct,
                "1 Jahr %": d.performance.get("1 Jahr"),
                "Volatilität %": d.volatilitaet,
                "Größe (€)": d.groesse,
            }
        )
    if zeilen:
        st.dataframe(
            pd.DataFrame(zeilen), width="stretch", hide_index=True,
            column_config={
                "Kurs (€)": st.column_config.NumberColumn(format="%.2f"),
                "Tag %": st.column_config.NumberColumn(format="%+.2f"),
                "1 Jahr %": st.column_config.NumberColumn(format="%+.1f"),
                "Volatilität %": st.column_config.NumberColumn(format="%.1f"),
                "Größe (€)": st.column_config.NumberColumn(format="%.0f"),
            },
        )


# --------------------------------------------------------------------------- #
# Teilen
# --------------------------------------------------------------------------- #
def teilen_block(ticker: str, haupt_zeile: pd.Series | None, alternativen: list) -> None:
    if haupt_zeile is None:
        return
    theme.abschnitt("Ergebnis teilen", "Der Link öffnet exakt dieses Match.")

    parameter = {
        "ticker": ticker,
        "menge": st.session_state["menge"],
        "p0": str(haupt_zeile["produkt_url"]),
    }
    for i, treffer in enumerate(alternativen[:3], start=1):
        parameter[f"p{i}"] = treffer.url

    link = APP_URL + "?" + urlencode(parameter)

    spalten = st.columns([4, 1])
    with spalten[0]:
        st.code(link, language=None)
    with spalten[1]:
        if HAT_COPY:
            try:
                copy_button(link, tooltip="Link kopieren",
                            copied_label="Kopiert! ✅", icon="st")
            except Exception:  # noqa: BLE001
                # Die Kopier-Komponente ist Kür – der Link steht ja daneben.
                pass
        st.download_button(
            "⬇️ JSON",
            json.dumps(parameter, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="match.json",
            mime="application/json",
            width="stretch",
        )


# --------------------------------------------------------------------------- #
# Hauptprogramm
# --------------------------------------------------------------------------- #
def main() -> None:
    zustand_initialisieren()

    theme.stil_einbinden(ist_dunkel(), st.session_state["animationen"])

    # Query-Parameter zuerst: die Seitenleiste zeigt sonst noch die alte Menge,
    # während der Rest der Seite schon mit der neuen rechnet.
    link_ticker = st.query_params.get("ticker")
    link_produkte = [
        st.query_params[k] for k in ("p0", "p1", "p2", "p3", "p4") if k in st.query_params
    ]
    if "menge" in st.query_params and "menge_eingabe" not in st.session_state:
        try:
            st.session_state["menge"] = max(1, min(10_000, int(st.query_params["menge"])))
        except (TypeError, ValueError):
            pass

    alle_produkte = datenbank.lade_produkte()
    gewaehlt, aktiv_filter, darstellung = seitenleiste(alle_produkte)

    if gewaehlt:
        ticker_setzen(gewaehlt)
        link_produkte = []  # neue Suche schlägt den geteilten Link
    ticker = st.session_state["aktiver_ticker"] or link_ticker

    theme.hero(
        "Was kriegst du für <em style='font-style:normal;text-decoration:underline "
        "text-decoration-thickness:4px;text-underline-offset:7px'>eine Aktie</em>?",
        "Der OTTO Aktien-Matcher übersetzt jeden Börsenkurs in echte Produkte – "
        "vom Kugelschreiber bis zum Seidenteppich. Kursdaten von Yahoo Finance, "
        "Sortiment täglich frisch von otto.de.",
    )

    if not ticker:
        startbildschirm(matcher.filtere(alle_produkte, aktiv_filter))
        return

    daten = markt.lade_markt(ticker)
    if daten.fehler:
        st.error(f"⚠️ {daten.fehler}")
        theme.hinweis(
            "Tipp: Deutsche Werte brauchen oft das Börsenkürzel (z. B. <code>SIE.DE</code>), "
            "Krypto die Währung (<code>BTC-EUR</code>).",
        )
        startbildschirm(matcher.filtere(alle_produkte, aktiv_filter))
        return

    ticker_merken(daten.ticker)
    budget = round((daten.preis or 0) * st.session_state["menge"], 2)
    produkte = matcher.filtere(alle_produkte, aktiv_filter)

    tabs = st.tabs([
        "🎯 Matcher", "🧺 Warenkorb", "📈 Analyse",
        "🛍️ Produkte", "📊 Insights", "⭐ Watchlist", "ℹ️ Über",
    ])

    with tabs[0]:
        haupt_zeile, alternativen = tab_matcher(
            daten, budget, produkte, link_produkte, darstellung
        )
        teilen_block(daten.ticker, haupt_zeile, alternativen)
    with tabs[1]:
        tab_warenkorb(budget, produkte, darstellung)
    with tabs[2]:
        tab_analyse(daten, produkte, darstellung)
    with tabs[3]:
        tab_explorer(produkte, budget, darstellung)
    with tabs[4]:
        tab_insights(produkte, alle_produkte, darstellung)
    with tabs[5]:
        tab_watchlist(daten.ticker, darstellung)
    with tabs[6]:
        ueber_tab()


def ueber_tab() -> None:
    theme.abschnitt("Wie das hier funktioniert")
    st.markdown(
        """
Der **OTTO Aktien-Matcher** beantwortet eine sehr konkrete Frage:
*Was könnte ich mir stattdessen kaufen?*

1. **Kurs holen** – Yahoo Finance liefert den letzten Preis, wir rechnen ihn in Euro um
   (inklusive des Klassikers „britische Pence statt Pfund").
2. **Budget bilden** – Kurs × gewünschte Stückzahl.
3. **Produkt suchen** – aus der OTTO-Produktdatenbank kommt das teuerste Teil,
   das gerade noch ins Budget passt, plus Alternativen und ein voll ausgereizter Warenkorb.

Die Produktdaten entstehen durch einen täglichen Scrape von otto.de
(`daily_scrape.py`, per GitHub Action um 05:00 UTC) und landen in `otto_produkte.db`.
        """
    )

    theme.abschnitt("Funktionen im Überblick")
    spalten = st.columns(3)
    bloecke = [
        ("🎯 **Matcher**", "Bestes Einzelprodukt, Alternativen mit Vielfachen, teilbarer Link."),
        ("🧺 **Warenkorb**", "Greedy-Packung, die das Budget möglichst vollständig ausreizt."),
        ("📈 **Analyse**", "Kursverlauf, Kerzen, Rendite je Zeitraum, Volatilität, Zeitmaschine."),
        ("🛍️ **Produkte**", "Volltextsuche, Sortierung, Karten- oder Tabellenansicht, CSV-Export."),
        ("📊 **Insights**", "Preisverteilung, Marken-Ranking, Rabatt-Hitliste, Bewertungsstreuung."),
        ("⭐ **Watchlist**", "Bis zu acht Werte normiert auf Startwert 100 vergleichen."),
    ]
    for i, (titel, text) in enumerate(bloecke):
        with spalten[i % 3]:
            theme.hinweis(f"{titel}<br/>{text}")

    theme.abschnitt("Kleingedrucktes")
    theme.hinweis(
        "Dieses Projekt ist ein Spaß- und Lernprojekt. <b>Keine Anlageberatung.</b> "
        "Kurse können verzögert sein, Produktpreise stammen vom letzten Scrape und "
        "können auf otto.de abweichen.",
        art="warnung",
    )


if __name__ == "__main__":
    main()
