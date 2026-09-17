import ast
import random

import streamlit as st
from yahoo_anbindung import get_data
from streamlit_searchbox import st_searchbox
import html as _html
from otto_scraper import OttoProduct, get_product_details, search_otto
import yfinance as yf
import re

import re

with open('randomprodukte.txt', 'r', encoding='utf-8') as datei:
    text = datei.read()
    randomprodukte = re.findall(r'"([^"]+)"', text)

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


def stars(rating: float | None) -> str:
    if rating is None:
        return "–"
    full = int(rating)
    half = "½" if rating - full >= 0.5 else ""
    return "★" * full + half + f" ({rating})"


def eur(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def img_html(image_url: str) -> str:
    if image_url:
        return f'<div class="otto-img"><img src="{image_url}" alt="" loading="lazy"/></div>'
    return '<div class="otto-img otto-noimg">🛒<span>Kein Bild verfügbar</span></div>'

import re

def kurzname(produktname: str, hersteller: str) -> str:
    text = produktname

    if hersteller:
        # Hersteller entfernen, egal ob GmbH / GMBH / gmbh + flexible Leerzeichen
        pattern = r'\s+'.join(re.escape(w) for w in hersteller.split())
        text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)

    # Sonderzeichen / Trennzeichen neutralisieren
    text = re.sub(r'[\(\)\[\]\"\'„“”/\\,;:\.\-–—_…!?\*+|=]', ' ', text)

    woerter = []
    woerter.append(hersteller)
    for w in text.split():
        if re.search(r'\d', w):  # keine Wörter mit Zahlen
            continue
        if len(w) < 2:  # kein -, S, M, etc.
            continue
        if not woerter.__contains__(w):
            woerter.append(w)
        if len(woerter) == 3:
            break
    return ' '.join(woerter)

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
    placeholder="Aktie suchen (z.B. Apple / AAPL)",
    key="stock_search"
)

st.set_page_config(page_title="OTTO Aktien-Matcher", page_icon="🔴", layout="centered")


if firmenname:
    übergabe = get_data(firmenname)
    aktien_wert = übergabe.preis
    name = []
    preis = []
    anzahl = []
    produkte = []
    for i in range(0, 3):
        try:
            query = randomprodukte[random.randint(0, len(randomprodukte)-1)]
            with st.spinner("Lade OTTO-Daten …"):
                produkte.append(search_otto(query, limit=1))
            st.session_state["produkte"] = produkte
        except Exception as e:  # noqa: BLE001
            st.error(f"OTTO konnte nicht geladen werden: {e}")
            produkte = st.session_state.get("produkte", [])
        name.append(kurzname(produkte[i][0].title, produkte[i][0].brand))
        preis.append(produkte[i][0].price)
        nachkomma = 2
        while round((aktien_wert / produkte[i][0].price), nachkomma) == 0:
            nachkomma += 1
        anzahl.append(round(aktien_wert / produkte[i][0].price, nachkomma))

    st.write(
        f"### Für den Wert dieser Aktie könntest du dir entweder "
        f"**{anzahl[0]}x {name[0]}**, "
        f"**{anzahl[1]}x {name[1]}** oder "
        f"**{anzahl[2]}x {name[2]}** kaufen!"
    )

    mitte_links, mitte_rechts = st.columns([1, 1])

    with mitte_links:
        st.success(f"Ticker gefunden: {übergabe.ticker}")
        quote = übergabe.suche.quotes[0]
        unternehmen = quote.get("longname") or quote.get("shortname") or übergabe.ticker
        st.write(f"Unternehmen: {unternehmen}")
        st.metric("last Price", f"{übergabe.preis:.2f} {übergabe.währung}")
        st.write("**Kursverlauf der letzten 12 Monate:**")
        st.line_chart(übergabe.historie)
        if übergabe.ist_aktie:
            st.metric("Marktkapitalisierung", kompakt_formatieren(übergabe.marktkapitalisierung, übergabe.währung))
        else:
            st.metric("AUM", kompakt_formatieren(übergabe.fondgröße, übergabe.währung))

    with mitte_rechts:
        OTTO_RED = "#D52B1E"
        st.markdown(
            f"""
            <style>
            /* Alle Zeilen haben feste Höhen -> alle Karten sind gleich groß */
            .otto-card {{
                background: #fff; border-radius: 12px; padding: 14px;
                box-shadow: 0 1px 6px rgba(0,0,0,.12);
                display: flex; flex-direction: column;
            }}
            .otto-img {{
                height: 200px; border-radius: 8px; background: #f7f7f7;
                display: flex; align-items: center; justify-content: center; overflow: hidden;
            }}
            .otto-img img {{ max-width: 100%; max-height: 100%; object-fit: contain; }}
            .otto-noimg {{ flex-direction: column; gap: 4px; color: #aaa; font-size: 2.2rem; }}
            .otto-noimg span {{ font-size: .8rem; }}
            .otto-brand {{
                color: #666; font-size: .8rem; text-transform: uppercase; height: 1.4em; margin-top: 8px;
                white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            }}
            .otto-title {{
                font-weight: 700; font-size: .95rem; line-height: 1.3; height: 2.6em; overflow: hidden;
                display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
            }}
            .otto-offer {{ height: 1.5em; font-size: .85rem; }}
            .otto-old {{ color: #888; text-decoration: line-through; }}
            .otto-badge {{
                display: inline-block; background: {OTTO_RED}; color: #fff;
                font-size: .75rem; font-weight: 700; border-radius: 6px; padding: 1px 8px; margin-right: 6px;
            }}
            .otto-price {{ color: {OTTO_RED}; font-weight: 800; font-size: 1.25rem; height: 1.8em; }}
            .otto-meta {{
                color: #555; font-size: .8rem; height: 1.5em;
                white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
        for produkt in produkte:
            for j, p in enumerate(produkt):
                offer = "&nbsp;"
                if p.old_price and p.discount_pct:
                    offer = f'<span class="otto-badge">-{p.discount_pct} %</span><span class="otto-old">UVP {eur(p.old_price)}</span>'
                reviews = f" · {p.review_count} Bewertungen" if p.review_count else ""
                st.markdown(
                    f"""
                        <div class="otto-card">
                          {img_html(p.image_url)}
                          <div class="otto-brand">{_html.escape(p.brand) or "&nbsp;"}</div>
                          f'<div class="otto-title" style="color:black">{_html.escape(p.title)}</div>'
                          <div class="otto-offer">{offer}</div>
                          <div class="otto-price">{p.display_price}</div>
                          <div class="otto-meta">⭐ {stars(p.rating)}{reviews}</div>
                          <div class="otto-meta">📦 {_html.escape(p.availability) or "Verfügbarkeit siehe otto.de"}</div>
                        </div>
                        """,
                    unsafe_allow_html=True,
                )
                st.link_button("Bei OTTO ansehen ↗", p.product_url, use_container_width=True)
