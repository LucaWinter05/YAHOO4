import ast
import streamlit as st
from yahoo_anbindung import get_data
from yahoo_anbindung import search
import pandas as pd
import produkte
from streamlit_searchbox import st_searchbox


# Funktion, die während des Tippens im Hintergrund Yahoo Finance abfragt
import yfinance as yf

def search_stocks(searchterm: str):
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
    übergabe = get_data(firmenname)
    st.write(f'## Du könntest für den Wert dieser Aktie {meinprodukt.calc_wert(übergabe.preis)} {meinprodukt.get_produkt()} kaufen!')

    mitte_links, mitte_rechts = st.columns([1, 1])

    with mitte_links:
     st.success(f"Ticker gefunden: {übergabe.ticker}")
     st.write(f"Unternehmen: {übergabe.suche.quotes[0]['longname']}")
     st.metric("last Price", f"{übergabe.preis:.2f} {übergabe.währung}")
     def schön_formatiert(marktkapitalisierung):
        if marktkapitalisierung <  1000000:
            return f"{marktkapitalisierung:.2f} {übergabe.währung}"
        if marktkapitalisierung < 1000000000:
            return f"{marktkapitalisierung / 1000000 :.2f} mio {übergabe.währung}"
        return f"{marktkapitalisierung / 1000000000 :2f} bio {übergabe.währung}"
    st.metric("Marktkapitalisierung", schön_formatiert(übergabe.marktkapitalisierung))

    with mitte_rechts:
         bild_daten = meinprodukt.get_bild_url()
         if isinstance(bild_daten, str) and bild_daten.strip().startswith("["):
             try:
                 # Nur dann in eine echte Liste umwandeln
                 bild_daten = ast.literal_eval(bild_daten)
             except Exception:
                 # Falls beim Umwandeln etwas schiefläuft, behalten wir den String
                 pass

         st.image(f"{bild_daten[0]}", width=200)

         st.write("##", meinprodukt.get_produkt())

    








