import streamlit as st
from code import get_data
import pandas as pd
import produkte

st.set_page_config(page_title="OTTO Aktien-Matcher", page_icon="🔴", layout="centered")

oben_links, oben_rechts = st.columns([10, 1])
with oben_links:
    st.write("")
with oben_rechts:
    st.image("otto.png", width=200)

st.title("Otto Aktien-Matcher")
firmenname = st.text_input("Firmenname eingeben:", placeholder="z.B. Apple/AAPL")

try:
    if firmenname:
        übergabe = get_data(firmenname)
        st.success(f"Ticker gefunden: {übergabe.ticker}")
        st.write(f"Unternehmen: {übergabe.suche.quotes[0]['longname']}")
        st.metric("last Price", f"{übergabe.preis:.2f} $")
        st.metric("Marktkapitalisierung", f"{übergabe.marktkapitalisierung:.2f} $")
except Exception as e:
    st.write(f" Bitte überprüfe deine Eingabe")


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




































# import streamlit as st
# import pandas as pd
# import numpy as np

# # 1. Muss IMMER der erste st-Befehl sein, sonst meckert Streamlit
# st.set_page_config(page_title="OTTO Aktien-Matcher", page_icon="🔴", layout="centered")

# # 2. OTTO-Look
# st.markdown("""
# <style>
# img { border-radius: 12px; }
# h1 { color: #D4021D !important; }
# </style>
# """, unsafe_allow_html=True)

# # 3. Schnittstellen mit Fallback (dein Mock bleibt)
# try:
#     from stock_service import get_stock_data
# except ImportError:
#     def get_stock_data(ticker):
#         price = 150.0
#         hist = pd.DataFrame(np.random.randn(20, 1) + 150, columns=["Close"])
#         return price, hist, {"name": f"{ticker} (Mock)", "currency": "EUR"}

# try:
#     from product_matcher import find_closest_product
# except ImportError:
#     def find_closest_product(price, csv_path=None):
#         return {"name": "SMEG Kaffeemaschine (Mock)", "price": 149.99,
#                 "image_url": "https://picsum.photos/300/200",
#                 "product_url": "https://www.otto.de"}

# # 4. Such-Liste (später aus CSV von Person C)
# COMPANIES = {
#     "Apple": "AAPL",
#     "Microsoft": "MSFT",
#     "Tesla": "TSLA",
#     "Amazon": "AMZN",
#     "Nvidia": "NVDA",
#     "SAP": "SAP.DE",
#     "BMW": "BMW.DE",
#     "Siemens": "SIE.DE",
#     "Allianz": "ALV.DE",
#     "Deutsche Telekom": "DTE.DE",
# }

# # 5. Header
# st.title("🔴 OTTO Aktien-Matcher")
# st.caption("Aktie eingeben → Kurs sehen → OTTO-Gegenwert finden")
# st.divider()

# # 6. Suche
# with st.container(border=True):
#     st.subheader("1. Aktie suchen")
#     options = [f"{name} ({ticker})" for name, ticker in COMPANIES.items()]
#     choice = st.selectbox("Firma suchen (einfach tippen zum Filtern):", options)
#     ticker = choice.split("(")[-1].replace(")", "")
#     button = st.button("Analysieren", type="primary", use_container_width=True)

# if not button:
#     st.info("👆 Wähle oben eine Firma und klicke auf Analysieren.")

# # 7. Ergebnis
# if button:
#     try:
#         with st.spinner("Lade Kurs und Produkt..."):
#             price, hist, info = get_stock_data(ticker)
#             produkt = find_closest_product(price)

#         st.success(f"Match gefunden für {info.get('name', ticker)}!")
#         c1, c2 = st.columns(2)

#         with c1:
#             with st.container(border=True):
#                 st.subheader("📈 Aktie")
#                 st.metric(f"Kurs in {info.get('currency', 'EUR')}", f"{price:.2f}")
#                 st.caption(f"{ticker} - {info.get('name', '')}")
#                 st.area_chart(hist["Close"])

#         with c2:
#             with st.container(border=True):
#                 st.subheader("🛒 OTTO-Gegenwert")
#                 st.image(produkt["image_url"], use_container_width=True)
#                 st.write(f"**{produkt['name']}**")
#                 st.write(f"{produkt['price']:.2f} €")
#                 st.link_button("Zu otto.de", produkt["product_url"], use_container_width=True)

#     except Exception as e:
#         st.error(f"Ticker nicht gefunden oder keine Daten. Versuch z.B. Apple (AAPL), SAP (SAP.DE). ({e})")

# st.divider()
# st.caption("Bootcamp-Demo • Kurse: Yahoo Finance • Produkte: OTTO CSV-Demo")
# import streamlit as st
# import pandas as pd
# import numpy as np

# st.markdown("""
# <style>
# .stApp { background-color: #fafafa; }
# h1 { color: #D4021D !important; }
# div[data-testid="stMetricValue"] { color: #D4021D; }
# img { border-radius: 12px; }
# </style>
# """, unsafe_allow_html=True)

# try:
#     from stock_service import get_stock_data
# except ImportError:
#     def get_stock_data(ticker):
#         price = 150.0
#         hist = pd.DataFrame(np.random.randn(20,1)+150, columns=["Close"])
#         return price, hist, {"name": f"{ticker} (Mock)", "currency": "EUR"}

# try:
#     from product_matcher import find_closest_product
# except ImportError:
#     def find_closest_product(price, csv_path=None):
#         return {"name": "SMEG Kaffeemaschine (Mock)", "price": 149.99,
#                 "image_url": "https://picsum.photos/300/200",
#                 "product_url": "https://www.otto.de"}
# #    
# # x = st.slider("Select a value")
# # st.write(x, "squared is", x * x)
# # st.set_page_config(page_title="OTTO Aktien-Matcher", layout="centered")
# # st.title("🔴 OTTO Aktien-Matcher")
# st.set_page_config(page_title="OTTO Aktien-Matcher", page_icon="🔴", layout="centered")

# st.title("🔴 OTTO Aktien-Matcher")
# st.caption("Aktie eingeben → Kurs sehen → OTTO-Gegenwert finden")
# st.divider()

# with st.container(border=True):
#     st.subheader("1. Aktie suchen")
#     # hier kommt deine selectbox hin
#     # hier kommt dein Button hin


# ticker = st.text_input("Ticker:", "AAPL").upper().strip()
# if st.button("Analysieren"):
#     try:
#         with st.spinner("Lade..."):
#             price, hist, info = get_stock_data(ticker)
#             produkt = find_closest_product(price)
#         c1, c2 = st.columns(2)
#         with c1:
#             st.subheader(f"{ticker} - {info.get('name','')}")
#             st.metric("Kurs", f"{price:.2f} €")
#             st.line_chart(hist)
#         with c2:
#             st.subheader("Dein OTTO-Gegenwert")
#             st.image(produkt["image_url"], use_container_width=True)
#             st.write(f"**{produkt['name']}**")
#             st.write(f"{produkt['price']:.2f} €")
#             st.link_button("Zu otto.de", produkt["product_url"])
#     except Exception as e:
#         st.error(f"Ticker nicht gefunden oder keine Daten. Versuch z.B. AAPL, SAP.DE, TSLA. ({e})")




