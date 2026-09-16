import streamlit as st
from code import get_data
import pandas as pd
import produkte

#Design Part
oben_links, oben_rechts = st.columns([10, 1])
with oben_links:
    st.write("")
with oben_rechts:
    st.image("otto.png", width=200)

st.title("Otto Aktien-Matcher")
st.set_page_config(page_title="OTTO Aktien-Matcher", page_icon="🔴", layout="centered")



firmenname = st.text_input("Firmenname eingeben:", placeholder="z.B. Apple/AAPL")

try:
    if firmenname:
        übergabe = get_data(firmenname)
        st.success(f"Ticker gefunden: {übergabe.ticker}")
        st.write(f"Unternehmen: {übergabe.suche.quotes[0]['longname']}")
        st.metric("last Price", f"{übergabe.preis:.2f} $")
        st.metric("Marktkapitalisierung", f"{übergabe.marktkapitalisierung:.2f} $")

        meinprodukt = produkte.rand_prod()
        meinprodukt.get_produkt()
        st.write(meinprodukt.get_produkt())
        st.write(meinprodukt.get_preis())
        st.write(meinprodukt.get_marke())
        st.write(meinprodukt.get_bild_url())
        st.write(meinprodukt.get_produkt_url())
        st.write(meinprodukt.get_bewertung())
        st.write(meinprodukt.get_anzahl_bewertungen())
        st.write(meinprodukt.calc_wert(übergabe.preis))
        
except Exception as e:
    st.write(f" Bitte überprüfe deine Eingabe")
    








