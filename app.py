import streamlit as st
from code import get_data
import pandas as pd
import produkte

#Design Part
oben_links, oben_rechts = st.columns([10, 1])
with oben_links:
    st.write("hjdjcdjcdjcd")
with oben_rechts:
    st.image("otto.png", width=200)

st.title("Otto Aktien-Matcher")

st.set_page_config(page_title="OTTO Aktien-Matcher", page_icon="🔴", layout="centered")



firmenname = st.text_input("Firmenname eingeben:", placeholder="z.B. Apple/AAPL")
mitte_links, mitte_rechts = st.columns([1, 1])


   


try:
       if firmenname:
        with mitte_links:
         übergabe = get_data(firmenname)
         st.success(f"Ticker gefunden: {übergabe.ticker}")
         st.write(f"Unternehmen: {übergabe.suche.quotes[0]['longname']}")
         st.metric("last Price", f"{übergabe.preis:.2f} $")
         def schön_formatiert(marktkapitalisierung):
            if marktkapitalisierung <  1000000:
                return f"{marktkapitalisierung:.2f} $"
            if marktkapitalisierung < 1000000000:
                return f"{marktkapitalisierung / 1000000 :.2f}mio $"
            return f"{marktkapitalisierung / 1000000000 :2f}bio $"
        st.metric("Marktkapitalisierung", schön_formatiert(übergabe.marktkapitalisierung))

        with mitte_rechts:
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

    








