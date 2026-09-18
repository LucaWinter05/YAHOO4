"""Design-System: Farben, CSS und wiederverwendbare UI-Bausteine.

Alles Optische der App steckt hier – die Seiten selbst bauen nur noch mit
:func:`hero`, :func:`kpi`, :func:`produktkarte` & Co. zusammen.

Das Farbschema kommt aus CSS-Custom-Properties. Ein Wechsel zwischen hellem
und dunklem Modus tauscht lediglich den ``:root``-Block aus, alle Komponenten
bleiben unverändert.
"""

from __future__ import annotations

import base64
import html as _html
from pathlib import Path

import streamlit as st

from kern.formatierung import eur, prozent, sterne, zahl

__all__ = [
    "OTTO_ROT",
    "seite_konfigurieren",
    "stil_einbinden",
    "hero",
    "abschnitt",
    "kpi_reihe",
    "kpi",
    "produktkarte",
    "produkt_raster",
    "leer_zustand",
    "hinweis",
    "fortschrittsbalken",
    "chips",
    "logo_data_uri",
    "trennlinie",
    "bewertungs_badge",
    "aussage",
]

OTTO_ROT = "#D52B1E"
OTTO_ROT_DUNKEL = "#A81F16"
OTTO_ROT_HELL = "#FF5A47"

_WURZEL = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# Grundgerüst
# --------------------------------------------------------------------------- #
def seite_konfigurieren() -> None:
    """``st.set_page_config`` – muss der allererste Streamlit-Aufruf sein."""
    st.set_page_config(
        page_title="OTTO Aktien-Matcher",
        page_icon="🛒",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "About": (
                "**OTTO Aktien-Matcher**\n\n"
                "Übersetzt Börsenkurse in Dinge, die man anfassen kann. "
                "Kursdaten von Yahoo Finance, Produkte von otto.de."
            ),
        },
    )


@st.cache_data(show_spinner=False)
def logo_data_uri(dateiname: str = "otto.png") -> str:
    """Logo als Data-URI, damit es ohne separaten HTTP-Request rendert."""
    pfad = _WURZEL / dateiname
    if not pfad.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(pfad.read_bytes()).decode()


def _palette(dunkel: bool) -> str:
    if dunkel:
        return f"""
            --bg:            #0E1117;
            --bg-weich:      #151A23;
            --flaeche:       rgba(30, 36, 48, .92);
            --flaeche-hoch:  rgba(42, 49, 64, .95);
            --rand:          rgba(255, 255, 255, .10);
            --rand-stark:    rgba(255, 255, 255, .20);
            --text:          #F2F4F8;
            --text-weich:    #A8B0BF;
            --text-zart:     #6F7889;
            --akzent:        {OTTO_ROT_HELL};
            --akzent-tief:   {OTTO_ROT};
            --akzent-weich:  rgba(255, 90, 71, .16);
            --gut:           #3DDC97;
            --gut-weich:     rgba(61, 220, 151, .16);
            --schlecht:      #FF6B6B;
            --schlecht-weich:rgba(255, 107, 107, .16);
            --warnung:       #FFB020;
            --warnung-weich: rgba(255, 176, 32, .16);
            --schatten:      0 10px 30px rgba(0, 0, 0, .45);
            --schatten-hoch: 0 18px 48px rgba(0, 0, 0, .60);
            --karte-bild-bg: #1B212C;
        """
    return f"""
        --bg:            #F6F7FA;
        --bg-weich:      #FFFFFF;
        --flaeche:       rgba(255, 255, 255, .96);
        --flaeche-hoch:  #FFFFFF;
        --rand:          rgba(16, 24, 40, .09);
        --rand-stark:    rgba(16, 24, 40, .18);
        --text:          #101828;
        --text-weich:    #55607A;
        --text-zart:     #8A93A6;
        --akzent:        {OTTO_ROT};
        --akzent-tief:   {OTTO_ROT_DUNKEL};
        --akzent-weich:  rgba(213, 43, 30, .10);
        --gut:           #12875B;
        --gut-weich:     rgba(18, 135, 91, .12);
        --schlecht:      #C2261A;
        --schlecht-weich:rgba(194, 38, 26, .12);
        --warnung:       #B9761A;
        --warnung-weich: rgba(185, 118, 26, .14);
        --schatten:      0 4px 18px rgba(16, 24, 40, .08);
        --schatten-hoch: 0 16px 40px rgba(16, 24, 40, .16);
        --karte-bild-bg: #F3F4F7;
    """


def stil_einbinden(dunkel: bool = False, animationen: bool = True) -> None:
    """Injiziert das komplette Stylesheet. Einmal pro Rerun aufrufen."""
    animation_regeln = "" if animationen else """
        *, *::before, *::after { animation: none !important; transition: none !important; }
    """

    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

:root {{
    {_palette(dunkel)}
    --radius:    16px;
    --radius-s:  10px;
    --radius-xs: 8px;
    --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}}

html, body, [class*="css"], .stApp {{ font-family: var(--font); }}

.stApp {{ background: var(--bg); color: var(--text); }}
[data-testid="stAppViewContainer"] > .main {{ background: transparent; }}
[data-testid="stHeader"] {{ background: transparent; backdrop-filter: blur(8px); }}
[data-testid="stToolbar"] {{ right: 1rem; }}
.block-container {{ padding-top: 2.2rem; padding-bottom: 4rem; max-width: 1420px; }}

/* ---------------------------------------------------------------- Sidebar */
[data-testid="stSidebar"] {{
    background: var(--bg-weich);
    border-right: 1px solid var(--rand);
}}
[data-testid="stSidebar"] .block-container {{ padding-top: 1.2rem; }}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{ color: var(--text); }}

/* ------------------------------------------------------------------- Hero */
.am-hero {{
    position: relative;
    border-radius: calc(var(--radius) + 6px);
    padding: 34px 38px;
    margin-bottom: 26px;
    overflow: hidden;
    background:
        radial-gradient(1100px 380px at 8% -30%, rgba(255,255,255,.22), transparent 62%),
        radial-gradient(760px 320px at 102% 120%, rgba(0,0,0,.28), transparent 60%),
        linear-gradient(118deg, var(--akzent-tief) 0%, var(--akzent) 58%, #FF8A5B 100%);
    color: #fff;
    box-shadow: var(--schatten-hoch);
}}
.am-hero::after {{
    content: "";
    position: absolute; inset: 0;
    background-image:
        repeating-linear-gradient(135deg, rgba(255,255,255,.055) 0 2px, transparent 2px 22px);
    pointer-events: none;
}}
.am-hero-inhalt {{ position: relative; z-index: 2; }}
.am-hero-marke {{
    display: inline-flex; align-items: center; gap: 8px;
    font-size: .72rem; font-weight: 700; letter-spacing: .16em; text-transform: uppercase;
    background: rgba(255,255,255,.18); border: 1px solid rgba(255,255,255,.32);
    padding: 5px 13px; border-radius: 999px; margin-bottom: 14px;
    backdrop-filter: blur(6px);
}}
.am-hero h1 {{
    font-size: clamp(1.9rem, 4.2vw, 3.1rem); font-weight: 900; line-height: 1.04;
    margin: 0 0 10px 0; color: #fff; letter-spacing: -.025em;
}}
.am-hero p {{
    font-size: 1.03rem; max-width: 62ch; margin: 0;
    color: rgba(255,255,255,.93); line-height: 1.55;
}}
.am-hero-logo {{
    position: absolute; right: 34px; top: 50%; transform: translateY(-50%);
    z-index: 2; opacity: .97;
}}
.am-hero-logo img {{
    width: 150px; filter: drop-shadow(0 6px 18px rgba(0,0,0,.28));
    transition: transform .35s cubic-bezier(.2,.8,.2,1);
}}
.am-hero-logo img:hover {{ transform: scale(1.06) rotate(-1.5deg); }}
@media (max-width: 860px) {{ .am-hero-logo {{ display: none; }} }}

/* -------------------------------------------------------------- Abschnitt */
.am-abschnitt {{ margin: 34px 0 16px 0; }}
.am-abschnitt h2 {{
    font-size: 1.32rem; font-weight: 800; margin: 0; color: var(--text);
    display: flex; align-items: center; gap: 10px; letter-spacing: -.01em;
}}
.am-abschnitt h2::before {{
    content: ""; width: 4px; height: 1.15em; border-radius: 3px;
    background: linear-gradient(180deg, var(--akzent), var(--akzent-tief));
}}
.am-abschnitt p {{
    margin: 6px 0 0 14px; color: var(--text-weich); font-size: .92rem;
}}

/* -------------------------------------------------------------- KPI-Karten */
.am-kpi-reihe {{
    display: grid; gap: 14px; margin: 6px 0 4px 0;
    grid-template-columns: repeat(auto-fit, minmax(178px, 1fr));
}}
.am-kpi {{
    background: var(--flaeche); border: 1px solid var(--rand);
    border-radius: var(--radius); padding: 16px 18px;
    box-shadow: var(--schatten); position: relative; overflow: hidden;
    transition: transform .2s cubic-bezier(.2,.8,.2,1), box-shadow .2s, border-color .2s;
}}
.am-kpi:hover {{
    transform: translateY(-3px);
    box-shadow: var(--schatten-hoch); border-color: var(--rand-stark);
}}
.am-kpi::before {{
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
    background: linear-gradient(180deg, var(--akzent), transparent);
    opacity: .85;
}}
.am-kpi-kopf {{
    display: flex; align-items: center; gap: 7px; flex-wrap: wrap;
    font-size: .71rem; font-weight: 700; letter-spacing: .06em; line-height: 1.35;
    text-transform: uppercase; color: var(--text-zart); margin-bottom: 8px;
    overflow-wrap: anywhere;
}}
.am-kpi-wert {{
    font-size: 1.52rem; font-weight: 800; color: var(--text);
    line-height: 1.15; letter-spacing: -.02em;
    word-break: break-word;
}}
.am-kpi-delta {{
    display: inline-flex; align-items: center; gap: 4px; margin-top: 8px;
    font-size: .82rem; font-weight: 700; padding: 2px 9px; border-radius: 999px;
}}
.am-kpi-delta.gut      {{ color: var(--gut);      background: var(--gut-weich); }}
.am-kpi-delta.schlecht {{ color: var(--schlecht); background: var(--schlecht-weich); }}
.am-kpi-delta.neutral  {{ color: var(--text-weich); background: var(--akzent-weich); }}
.am-kpi-hinweis {{ margin-top: 7px; font-size: .78rem; color: var(--text-zart); }}

/* ----------------------------------------------------------- Produktkarten */
.am-karte {{
    background: var(--flaeche); border: 1px solid var(--rand);
    border-radius: var(--radius); padding: 15px;
    box-shadow: var(--schatten); display: flex; flex-direction: column;
    height: 100%; position: relative; overflow: hidden;
    transition: transform .22s cubic-bezier(.2,.8,.2,1), box-shadow .22s, border-color .22s;
}}
.am-karte:hover {{
    transform: translateY(-5px);
    box-shadow: var(--schatten-hoch); border-color: var(--akzent);
}}
.am-karte-band {{
    position: absolute; top: 13px; left: 0; z-index: 3;
    background: linear-gradient(135deg, var(--akzent), var(--akzent-tief));
    color: #fff; font-size: .72rem; font-weight: 800; letter-spacing: .04em;
    padding: 4px 12px 4px 10px; border-radius: 0 999px 999px 0;
    box-shadow: 0 3px 10px rgba(0,0,0,.24);
}}
.am-karte-bild {{
    height: 190px; border-radius: var(--radius-s); background: var(--karte-bild-bg);
    display: flex; align-items: center; justify-content: center; overflow: hidden;
    position: relative;
}}
.am-karte-bild img {{
    max-width: 100%; max-height: 100%; object-fit: contain;
    transition: transform .38s cubic-bezier(.2,.8,.2,1);
}}
.am-karte:hover .am-karte-bild img {{ transform: scale(1.07); }}
.am-karte-kein-bild {{
    flex-direction: column; gap: 6px; color: var(--text-zart); font-size: 2.1rem;
}}
.am-karte-kein-bild span {{ font-size: .78rem; }}
.am-karte-marke {{
    color: var(--text-zart); font-size: .73rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: .08em;
    height: 1.35em; margin-top: 12px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.am-karte-titel {{
    font-weight: 700; font-size: .95rem; line-height: 1.34; color: var(--text);
    height: 2.68em; overflow: hidden; margin-top: 2px;
    display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}}
.am-karte-angebot {{ height: 1.6em; font-size: .82rem; margin-top: 7px; }}
.am-karte-uvp {{ color: var(--text-zart); text-decoration: line-through; }}
.am-rabatt {{
    display: inline-block; background: var(--akzent); color: #fff;
    font-size: .73rem; font-weight: 800; border-radius: 6px;
    padding: 1px 8px; margin-right: 7px;
}}
.am-karte-preis {{
    color: var(--akzent); font-weight: 900; font-size: 1.42rem;
    letter-spacing: -.02em; height: 1.55em; margin-top: 2px;
}}
.am-karte-preis small {{
    font-size: .74rem; font-weight: 600; color: var(--text-zart);
    letter-spacing: 0; margin-left: 5px;
}}
.am-karte-meta {{
    color: var(--text-weich); font-size: .79rem; height: 1.6em;
    display: flex; align-items: center; gap: 5px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}}
.am-karte-fuss {{
    margin-top: auto; padding-top: 10px;
    border-top: 1px dashed var(--rand); font-size: .76rem; color: var(--text-zart);
}}

/* ------------------------------------------------------------------- Chips */
.am-chips {{ display: flex; flex-wrap: wrap; gap: 7px; margin: 8px 0 2px 0; }}
.am-chip {{
    background: var(--akzent-weich); color: var(--akzent);
    border: 1px solid var(--akzent); border-radius: 999px;
    padding: 3px 12px; font-size: .78rem; font-weight: 700;
}}
.am-chip.neutral {{
    background: transparent; color: var(--text-weich); border-color: var(--rand-stark);
}}

/* ------------------------------------------------------------ Fortschritt */
.am-fortschritt-huelle {{
    background: var(--akzent-weich); border-radius: 999px;
    height: 11px; overflow: hidden; margin: 9px 0 5px 0;
    border: 1px solid var(--rand);
}}
.am-fortschritt-balken {{
    height: 100%; border-radius: 999px;
    background: linear-gradient(90deg, var(--akzent-tief), var(--akzent), #FF9A6B);
    transition: width .7s cubic-bezier(.2,.8,.2,1);
    box-shadow: 0 0 14px var(--akzent-weich);
}}
.am-fortschritt-label {{
    display: flex; justify-content: space-between;
    font-size: .8rem; color: var(--text-weich); font-weight: 600;
}}

/* ------------------------------------------------------------- Info-Boxen */
.am-box {{
    border-radius: var(--radius); padding: 15px 18px; margin: 12px 0;
    border: 1px solid var(--rand); background: var(--flaeche);
    box-shadow: var(--schatten); font-size: .93rem; color: var(--text);
    border-left: 4px solid var(--akzent); line-height: 1.55;
}}
.am-box.gut      {{ border-left-color: var(--gut);      background: var(--gut-weich); }}
.am-box.warnung  {{ border-left-color: var(--warnung);  background: var(--warnung-weich); }}
.am-box.schlecht {{ border-left-color: var(--schlecht); background: var(--schlecht-weich); }}
.am-box b, .am-box strong {{ color: var(--text); }}

/* ----------------------------------------------------------- Leer-Zustand */
.am-leer {{
    text-align: center; padding: 56px 24px; border-radius: var(--radius);
    border: 2px dashed var(--rand-stark); background: var(--flaeche);
    color: var(--text-weich);
}}
.am-leer-icon {{ font-size: 3.1rem; margin-bottom: 12px; opacity: .85; }}
.am-leer h3 {{ margin: 0 0 6px 0; color: var(--text); font-weight: 800; }}
.am-leer p {{ margin: 0; font-size: .93rem; max-width: 46ch; margin-inline: auto; }}

/* --------------------------------------------------------- Aussage-Banner */
.am-aussage {{
    font-size: clamp(1.15rem, 2.4vw, 1.6rem); font-weight: 800;
    line-height: 1.42; color: var(--text); letter-spacing: -.015em;
    background: var(--flaeche); border: 1px solid var(--rand);
    border-radius: var(--radius); padding: 20px 24px; margin: 4px 0 14px 0;
    box-shadow: var(--schatten);
}}
.am-aussage em {{ color: var(--akzent); font-style: normal; }}
.am-aussage .am-rest {{
    display: block; margin-top: 8px; font-size: .92rem;
    font-weight: 600; color: var(--text-weich);
}}

/* ------------------------------------------------- Streamlit-Anpassungen */
.stButton > button, .stDownloadButton > button, .stLinkButton > a {{
    border-radius: var(--radius-s); font-weight: 700;
    border: 1px solid var(--rand-stark); transition: transform .16s, box-shadow .16s, border-color .16s;
}}
.stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {{
    transform: translateY(-1px); border-color: var(--akzent);
    box-shadow: 0 6px 18px var(--akzent-weich);
}}
.stButton > button[kind="primary"] {{
    background: linear-gradient(135deg, var(--akzent), var(--akzent-tief));
    border: none; color: #fff;
}}
.stTabs [data-baseweb="tab-list"] {{
    gap: 4px; border-bottom: 1px solid var(--rand); padding-bottom: 2px;
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: var(--radius-s) var(--radius-s) 0 0;
    padding: 9px 16px; font-weight: 700; font-size: .92rem;
}}
.stTabs [aria-selected="true"] {{
    background: var(--akzent-weich); color: var(--akzent) !important;
}}
[data-testid="stMetric"] {{
    background: var(--flaeche); border: 1px solid var(--rand);
    border-radius: var(--radius); padding: 14px 16px; box-shadow: var(--schatten);
}}
[data-testid="stExpander"] details {{
    border: 1px solid var(--rand); border-radius: var(--radius);
    background: var(--flaeche); box-shadow: var(--schatten);
}}
[data-testid="stDataFrame"] {{ border-radius: var(--radius-s); overflow: hidden; }}
div[data-baseweb="select"] > div {{ border-radius: var(--radius-xs); }}
hr {{ border-color: var(--rand); }}
/* Fußzeile weg – das Hauptmenü bleibt, dort steckt der Theme-Schalter. */
footer {{ visibility: hidden; }}

/* ------------------------------------------------------------ Animationen */
@keyframes am-auftauchen {{
    from {{ opacity: 0; transform: translateY(12px); }}
    to   {{ opacity: 1; transform: none; }}
}}
.am-hero, .am-kpi, .am-karte, .am-aussage, .am-box {{
    animation: am-auftauchen .42s cubic-bezier(.2,.8,.2,1) both;
}}
@keyframes am-puls {{
    0%, 100% {{ box-shadow: 0 0 0 0 var(--akzent-weich); }}
    50%      {{ box-shadow: 0 0 0 12px transparent; }}
}}
.am-puls {{ animation: am-puls 2.1s infinite; }}
@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{ animation: none !important; transition: none !important; }}
}}
{animation_regeln}
</style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Bausteine
# --------------------------------------------------------------------------- #
def hero(titel: str, untertitel: str, marke: str = "OTTO × Börse", mit_logo: bool = True) -> None:
    """Der große Kopfbereich der Seite."""
    logo = ""
    if mit_logo:
        quelle = logo_data_uri()
        if quelle:
            logo = (
                '<div class="am-hero-logo">'
                '<a href="https://otto-aktien-matcher.streamlit.app/" target="_self">'
                f'<img src="{quelle}" alt="OTTO"/></a></div>'
            )

    st.markdown(
        f"""
        <div class="am-hero">
          <div class="am-hero-inhalt">
            <div class="am-hero-marke">✦ {_html.escape(marke)}</div>
            <h1>{titel}</h1>
            <p>{untertitel}</p>
          </div>
          {logo}
        </div>
        """,
        unsafe_allow_html=True,
    )


def abschnitt(titel: str, untertitel: str = "") -> None:
    """Überschrift mit Akzentbalken."""
    unter = f"<p>{untertitel}</p>" if untertitel else ""
    st.markdown(
        f'<div class="am-abschnitt"><h2>{titel}</h2>{unter}</div>',
        unsafe_allow_html=True,
    )


def trennlinie() -> None:
    st.markdown("<hr style='margin:26px 0;opacity:.5'/>", unsafe_allow_html=True)


def _kpi_html(label: str, wert: str, delta: float | str | None = None,
              hinweis: str = "", icon: str = "") -> str:
    delta_html = ""
    if delta is not None and delta != "":
        if isinstance(delta, (int, float)):
            klasse = "gut" if delta > 0 else ("schlecht" if delta < 0 else "neutral")
            pfeil = "▲" if delta > 0 else ("▼" if delta < 0 else "●")
            text = f"{pfeil} {prozent(abs(delta), mit_vorzeichen=False)}"
        else:
            klasse, text = "neutral", str(delta)
        delta_html = f'<div class="am-kpi-delta {klasse}">{text}</div>'

    hinweis_html = f'<div class="am-kpi-hinweis">{_html.escape(hinweis)}</div>' if hinweis else ""
    icon_html = f"<span>{icon}</span>" if icon else ""

    return (
        '<div class="am-kpi">'
        f'<div class="am-kpi-kopf">{icon_html}{_html.escape(label)}</div>'
        f'<div class="am-kpi-wert">{wert}</div>'
        f"{delta_html}{hinweis_html}</div>"
    )


def kpi(label: str, wert: str, delta: float | str | None = None,
        hinweis: str = "", icon: str = "") -> None:
    """Einzelne Kennzahlen-Karte."""
    st.markdown(_kpi_html(label, wert, delta, hinweis, icon), unsafe_allow_html=True)


def kpi_reihe(eintraege: list[dict]) -> None:
    """Responsives Raster aus Kennzahlen-Karten.

    Jeder Eintrag: ``{"label": …, "wert": …, "delta": …, "hinweis": …, "icon": …}``
    """
    karten = "".join(
        _kpi_html(
            e.get("label", ""), e.get("wert", "–"),
            e.get("delta"), e.get("hinweis", ""), e.get("icon", ""),
        )
        for e in eintraege
    )
    st.markdown(f'<div class="am-kpi-reihe">{karten}</div>', unsafe_allow_html=True)


def bewertungs_badge(bewertung: float | None, anzahl: int | None = None) -> str:
    """Sterne-Leiste; die Anzahl der Rezensionen steht separat daneben."""
    if not bewertung:
        return "Noch keine Bewertung"
    return sterne(bewertung, anzahl)


def _bild_html(url: str) -> str:
    if url:
        return (
            '<div class="am-karte-bild">'
            f'<img src="{_html.escape(url, quote=True)}" alt="" loading="lazy" '
            'referrerpolicy="no-referrer"/></div>'
        )
    return '<div class="am-karte-bild am-karte-kein-bild">🛍️<span>Kein Bild verfügbar</span></div>'


def produktkarte(
    produkt,
    anzahl: int = 1,
    band: str = "",
    fussnote: str = "",
    mit_button: bool = True,
) -> None:
    """Rendert eine Produktkarte im OTTO-Look.

    ``produkt`` ist ein :class:`otto_scraper.OttoProduct`.
    """
    angebot = "&nbsp;"
    if produkt.old_price and produkt.discount_pct:
        angebot = (
            f'<span class="am-rabatt">−{produkt.discount_pct} %</span>'
            f'<span class="am-karte-uvp">UVP {eur(produkt.old_price)}</span>'
        )

    bewertungen = f" · {zahl(produkt.review_count, 0)} Bewertungen" if produkt.review_count else ""
    band_html = f'<div class="am-karte-band">{_html.escape(band)}</div>' if band else ""
    stueck = f"<small>× {anzahl}</small>" if anzahl > 1 else ""
    gesamt = ""
    if anzahl > 1 and produkt.price:
        gesamt = f"Gesamt: <b>{eur(produkt.price * anzahl)}</b>"
    fuss = fussnote or gesamt
    fuss_html = f'<div class="am-karte-fuss">{fuss}</div>' if fuss else ""

    st.markdown(
        f"""
        <div class="am-karte">
          {band_html}
          {_bild_html(produkt.image_url)}
          <div class="am-karte-marke">{_html.escape(produkt.brand) or "&nbsp;"}</div>
          <div class="am-karte-titel">{_html.escape(produkt.title)}</div>
          <div class="am-karte-angebot">{angebot}</div>
          <div class="am-karte-preis">{produkt.display_price}{stueck}</div>
          <div class="am-karte-meta">{bewertungs_badge(produkt.rating)}{bewertungen}</div>
          <div class="am-karte-meta">📦 {_html.escape(produkt.availability) or "Verfügbarkeit siehe otto.de"}</div>
          {fuss_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if mit_button and produkt.product_url:
        st.link_button(
            "Bei OTTO ansehen ↗",
            produkt.product_url,
            width="stretch",
        )


def produkt_raster(produkte: list, spalten: int = 3, baender: list[str] | None = None,
                   anzahlen: list[int] | None = None) -> None:
    """Mehrere Produktkarten in einem gleichmäßigen Raster."""
    if not produkte:
        return
    baender = baender or [""] * len(produkte)
    anzahlen = anzahlen or [1] * len(produkte)

    for start in range(0, len(produkte), spalten):
        reihe = produkte[start:start + spalten]
        cols = st.columns(spalten, gap="medium")
        for spalte, index in zip(cols, range(start, start + len(reihe))):
            with spalte:
                produktkarte(
                    produkte[index],
                    anzahl=anzahlen[index] if index < len(anzahlen) else 1,
                    band=baender[index] if index < len(baender) else "",
                )


def hinweis(text: str, art: str = "info") -> None:
    """Farbige Infobox (``info`` | ``gut`` | ``warnung`` | ``schlecht``)."""
    klasse = "" if art == "info" else art
    st.markdown(f'<div class="am-box {klasse}">{text}</div>', unsafe_allow_html=True)


def leer_zustand(icon: str, titel: str, text: str) -> None:
    st.markdown(
        f"""
        <div class="am-leer">
          <div class="am-leer-icon">{icon}</div>
          <h3>{_html.escape(titel)}</h3>
          <p>{_html.escape(text)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def fortschrittsbalken(prozent_wert: float, links: str = "", rechts: str = "") -> None:
    """Budget-Balken mit Beschriftung links/rechts."""
    breite = max(0.0, min(100.0, prozent_wert))
    st.markdown(
        f"""
        <div>
          <div class="am-fortschritt-label"><span>{_html.escape(links)}</span><span>{_html.escape(rechts)}</span></div>
          <div class="am-fortschritt-huelle">
            <div class="am-fortschritt-balken" style="width:{breite:.1f}%"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def chips(eintraege: list[str], neutral: bool = False) -> None:
    if not eintraege:
        return
    klasse = "am-chip neutral" if neutral else "am-chip"
    inhalt = "".join(f'<span class="{klasse}">{_html.escape(e)}</span>' for e in eintraege)
    st.markdown(f'<div class="am-chips">{inhalt}</div>', unsafe_allow_html=True)


def aussage(text_html: str, zusatz: str = "") -> None:
    """Die große Kernaussage („Du kannst dir stattdessen … kaufen“)."""
    rest = f'<span class="am-rest">{zusatz}</span>' if zusatz else ""
    st.markdown(f'<div class="am-aussage">{text_html}{rest}</div>', unsafe_allow_html=True)
