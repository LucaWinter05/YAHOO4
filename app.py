import ast
import streamlit as st
from yahoo_anbindung import get_data
from yahoo_anbindung import search
import pandas as pd
import produkte
from streamlit_searchbox import st_searchbox

import yfinance as yf

def search_stocks(searchterm):
    if not searchterm or len(searchterm.strip()) < 2:
        return []
    try:
        result = yf.Search(searchterm, max_results=10).quotes
    except Exception:
        return [] # still schweigen, sonst Dropdown kaputt

    suggestions = []
    for q in result or []:
        symbol = q.get("symbol")
        if not symbol:
            continue
        name = q.get("longname") or q.get("shortname") or ""
        suggestions.append((f"{symbol} - {name}", symbol))
    return suggestions

def get_erstes_bild(bild_daten):
    if isinstance(bild_daten, str) and bild_daten.strip().startswith("["):
        try:
            bild_daten = ast.literal_eval(bild_daten)
        except (ValueError, SyntaxError):
            return None

    if isinstance(bild_daten, list):
        return bild_daten[0] if bild_daten else None

    return bild_daten or None

def kompakt_formatieren(betrag, währung):
    dezimalstellen = 2
    if betrag is None:
        return f"– {währung}"

    einheiten = [
        (1e12, "Bio."),
        (1e9, "Mrd."),
        (1e6, "Mio."),
        (1e3, "Tsd."),
    ]

    vorzeichen = "-" if betrag < 0 else ""
    rest = abs(betrag)

    for schwelle, suffix in einheiten:
        if rest >= schwelle:
            wert = rest / schwelle
            zahl = f"{wert:.{dezimalstellen}f}".replace(".", ",")
            return f"{vorzeichen}{zahl} {suffix} {währung}"

    zahl = f"{rest:,.{dezimalstellen}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{vorzeichen}{zahl} {währung}"

#Design Part
oben_links, oben_rechts = st.columns([5, 1])
with oben_links:
    st.write("")
with oben_rechts:
    st.image("otto.png", width=200)

st.title("Otto Aktien-Matcher")

# Das interaktive Suchfeld einbinden
firmenname = st_searchbox(
    search_stocks,
    placeholder="Aktie suchen (z. B. Netflix, Nvidia oder n)...",
    key="stock_search"
)

st.set_page_config(page_title="OTTO Aktien-Matcher", page_icon="🔴", layout="centered")






if firmenname:

    meinprodukt = produkte.rand_prod()
    extra1 = produkte.rand_prod()
    extra2 = produkte.rand_prod()
    while extra1.get_produkt() == meinprodukt.get_produkt():
        extra1 = produkte.rand_prod()
    while extra2.get_produkt() == meinprodukt.get_produkt() or extra2.get_produkt() == extra1.get_produkt():
        extra2 = produkte.rand_prod()
    übergabe = get_data(firmenname)
    aktien_wert = übergabe.preis
    menge_haupt = meinprodukt.calc_wert(aktien_wert)
    menge_extra1 = extra1.calc_wert(aktien_wert)
    menge_extra2 = extra2.calc_wert(aktien_wert)
    st.write(
        f"## Für den Wert dieser Aktie könntest du dir entweder "
        f"**{menge_haupt}x {meinprodukt.get_produkt()}**, "
        f"**{menge_extra1}x {extra1.get_produkt()}** oder "
        f"**{menge_extra2}x {extra2.get_produkt()}** kaufen!"
    )

    mitte_links, mitte_rechts = st.columns([1, 1])

    with mitte_links:
        st.success(f"Ticker gefunden: {übergabe.ticker}")
        quote = übergabe.suche.quotes[0]
        unternehmen = quote.get("longname") or quote.get("shortname") or übergabe.ticker
        st.write(f"Unternehmen: {unternehmen}")
        st.metric("last Price", f"{übergabe.preis:.2f} {übergabe.währung}")
        if übergabe.ist_aktie:
            st.metric("Marktkapitalisierung", kompakt_formatieren(übergabe.marktkapitalisierung, übergabe.währung))
        else:
            st.metric("AUM", kompakt_formatieren(übergabe.fondsgröße, übergabe.währung))

    with mitte_rechts:
         bild_daten = meinprodukt.get_bild_url()

         erstes_bild = get_erstes_bild(bild_daten)
         if erstes_bild:
             st.image(erstes_bild, width=400)

         st.write("##", meinprodukt.get_produkt())

    








