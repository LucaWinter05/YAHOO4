"""Alle Diagramme der App – gebaut mit Altair (kommt mit Streamlit mit).

Gestaltungsregeln, die hier konsequent durchgezogen werden:

* **Eine Achse pro Diagramm** – nie zwei y-Skalen übereinander.
* **Feine Marken**: 2 px Linien, zurückhaltendes Raster, ruhige Achsenfarben.
* **Ab zwei Serien immer eine Legende**, Farben in fester Reihenfolge (nie
  zyklisch), damit ein Filter die verbleibenden Serien nicht umfärbt.
* **Hover überall**: Fadenkreuz + Tooltip bei Linien/Flächen, Punkt-Tooltip sonst.
* Helle und dunkle Variante sind getrennt gewählt, nicht automatisch invertiert.
"""

from __future__ import annotations

import altair as alt
import pandas as pd

__all__ = [
    "kursverlauf",
    "kerzen_chart",
    "vergleichs_chart",
    "preis_histogramm",
    "kategorie_balken",
    "bewertung_streuung",
    "performance_balken",
    "budget_donut",
]

# Kategoriale Palette in fester Reihenfolge (geprüfte Standardpalette).
SERIEN_HELL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100",
               "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SERIEN_DUNKEL = ["#3987e5", "#d95926", "#199e70", "#c98500",
                 "#d55181", "#008300", "#9085e9", "#e66767"]

# Statusfarben – reserviert, nie als „Serie 9“ zweckentfremdet.
STATUS_GUT = "#0ca30c"
STATUS_SCHLECHT = "#d03b3b"

# Einzelserien tragen die Markenfarbe.
MARKE_HELL = "#D52B1E"
MARKE_DUNKEL = "#FF5A47"

_INK = {
    False: {"text": "#0b0b0b", "weich": "#52514e", "gedaempft": "#898781",
            "raster": "#e1e0d9", "achse": "#c3c2b7", "flaeche": "transparent"},
    True: {"text": "#ffffff", "weich": "#c3c2b7", "gedaempft": "#898781",
           "raster": "#2c2c2a", "achse": "#383835", "flaeche": "transparent"},
}


def de_format(spec: str = ",.2f") -> str:
    """Vega-Ausdruck für deutsche Zahlen auf Achsen.

    Vega-Lite-Specs tragen keine Locale, ``format=",.2f"`` liefert also
    ``1,234.50``. Der Ausdruck dreht Punkt und Komma um – über ein
    Platzhalterzeichen, damit sich die beiden Ersetzungen nicht gegenseitig
    auffressen.
    """
    return (
        f"replace(replace(replace(format(datum.value, '{spec}'), /,/g, '@'), "
        "/\\./g, ','), /@/g, '.')"
    )


def _zahl_de(wert, dezimalstellen: int = 2) -> str:
    """Deutsche Zahl für vorberechnete Tooltip-Spalten."""
    if wert is None or (isinstance(wert, float) and pd.isna(wert)):
        return "–"
    return (f"{wert:,.{dezimalstellen}f}"
            .replace(",", "@").replace(".", ",").replace("@", "."))


def _label_breite(texte, zeichenbreite: float = 6.8, maximum: int = 240) -> int:
    """Grober Platzbedarf der längsten Achsenbeschriftung in Pixeln."""
    laengste = max((len(str(t)) for t in texte), default=6)
    return int(min(maximum, 16 + laengste * zeichenbreite))


def _basis(chart: alt.Chart, dunkel: bool, hoehe: int = 300,
           polster_links: int = 56) -> alt.Chart:
    """Einheitliche Chrome-Einstellungen für jedes Diagramm.

    ``polster_links`` ist nicht kosmetisch: Streamlit rendert Charts mit
    ``width: container``, und in *geschichteten* Specs reserviert Vega-Lite
    dabei keinen Platz für die y-Achse – die Beschriftung landet bei
    negativen x-Koordinaten und wird abgeschnitten. Ein explizites Polster
    schiebt die Zeichenfläche um genau diesen Betrag nach rechts.
    """
    ink = _INK[bool(dunkel)]
    return (
        chart.properties(
            height=hoehe,
            padding={"left": polster_links, "top": 8, "right": 14, "bottom": 8},
        )
        .configure_view(strokeWidth=0, fill=ink["flaeche"])
        .configure_axis(
            labelColor=ink["gedaempft"],
            titleColor=ink["weich"],
            gridColor=ink["raster"],
            domainColor=ink["achse"],
            tickColor=ink["achse"],
            labelFontSize=11,
            titleFontSize=11,
            titleFontWeight="normal",
            labelFont="Inter, system-ui, sans-serif",
            titleFont="Inter, system-ui, sans-serif",
        )
        .configure_legend(
            labelColor=ink["weich"],
            titleColor=ink["weich"],
            labelFontSize=11,
            titleFontSize=11,
            orient="top",
            direction="horizontal",
            titleAnchor="start",
        )
        .configure_title(color=ink["text"], fontSize=13, anchor="start", font="Inter")
    )


def _farbe(dunkel: bool) -> str:
    return MARKE_DUNKEL if dunkel else MARKE_HELL


def _rgba(hexfarbe: str, alpha: float) -> str:
    """``"#D52B1E", .3`` -> ``"rgba(213,43,30,0.3)"`` (Vega versteht CSS-Farben)."""
    h = hexfarbe.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha:g})"


# --------------------------------------------------------------------------- #
# Kursverlauf
# --------------------------------------------------------------------------- #
def kursverlauf(
    historie: pd.DataFrame,
    dunkel: bool = False,
    hoehe: int = 320,
    mit_durchschnitt: bool = True,
    waehrung: str = "€",
) -> alt.Chart | None:
    """Kursverlauf als Fläche + Linie mit Fadenkreuz-Tooltip.

    ``mit_durchschnitt`` blendet zusätzlich den 50-Tage-Schnitt als Serie ein –
    dann erscheint automatisch eine Legende (zwei Serien = nie Farbe allein).
    """
    if historie is None or historie.empty:
        return None

    daten = historie[["Datum", "Close"]].dropna().copy()
    if len(daten) < 2:
        return None
    daten = daten.rename(columns={"Close": "Kurs"})
    daten["KursText"] = [_zahl_de(k) for k in daten["Kurs"]]

    farbe = _farbe(dunkel)
    ink = _INK[bool(dunkel)]

    y_min = float(daten["Kurs"].min())
    y_max = float(daten["Kurs"].max())
    polster = (y_max - y_min) * 0.08 or max(y_max * 0.02, 0.01)
    skala = alt.Scale(domain=[y_min - polster, y_max + polster], nice=False)
    # Dieselbe y-Definition in JEDER Ebene: unterschiedliche Achsenobjekte in
    # einem Layer-Chart lässt Vega-Lite zusammenfallen – die Beschriftung
    # verschwindet dann komplett.
    y_achse = alt.Y("Kurs:Q", scale=skala, axis=alt.Axis(title=None, labelExpr=de_format(",.2f")))
    x_achse = alt.X("Datum:T", axis=alt.Axis(title=None, format="%b %y", tickCount=6))

    zeiger = alt.selection_point(
        nearest=True, on="pointermove", fields=["Datum"], empty=False
    )

    flaeche = (
        alt.Chart(daten)
        .mark_area(
            line=False,
            color=alt.Gradient(
                gradient="linear", x1=0, x2=0, y1=0, y2=1,
                stops=[
                    alt.GradientStop(color=_rgba(farbe, 0.30), offset=0),
                    alt.GradientStop(color=_rgba(farbe, 0.02), offset=1),
                ],
            ),
        )
        .encode(x=x_achse, y=y_achse)
    )

    linie = flaeche.mark_line(strokeWidth=2, color=farbe, interpolate="monotone")

    punkte = (
        alt.Chart(daten)
        .mark_point(size=90, opacity=0)
        .encode(x=x_achse, y=y_achse)
        .add_params(zeiger)
    )

    fadenkreuz = (
        alt.Chart(daten)
        .mark_rule(color=ink["gedaempft"], strokeWidth=1, strokeDash=[3, 3])
        .encode(
            x=x_achse,
            tooltip=[
                alt.Tooltip("Datum:T", title="Datum", format="%d.%m.%Y"),
                alt.Tooltip("KursText:N", title=f"Kurs ({waehrung})"),
            ],
        )
        .transform_filter(zeiger)
    )

    marker = (
        alt.Chart(daten)
        .mark_point(size=80, filled=True, color=farbe, stroke="white", strokeWidth=2)
        .encode(x=x_achse, y=y_achse)
        .transform_filter(zeiger)
    )

    ebenen = [flaeche, linie]

    if mit_durchschnitt and len(daten) >= 50:
        schnitt = daten.copy()
        schnitt["Kurs"] = schnitt["Kurs"].rolling(50, min_periods=50).mean()
        schnitt = schnitt.dropna()
        if not schnitt.empty:
            schnitt["Serie"] = "50-Tage-Schnitt"
            daten_serie = daten.copy()
            daten_serie["Serie"] = "Kurs"
            legende = alt.Scale(
                domain=["Kurs", "50-Tage-Schnitt"],
                range=[farbe, ink["gedaempft"]],
            )
            farbe_serie = alt.Color("Serie:N", scale=legende, legend=alt.Legend(title=None))
            linie = (
                alt.Chart(daten_serie)
                .mark_line(strokeWidth=2, interpolate="monotone")
                .encode(x=x_achse, y=y_achse, color=farbe_serie)
            )
            schnitt_linie = (
                alt.Chart(schnitt)
                .mark_line(strokeWidth=1.5, strokeDash=[5, 4], interpolate="monotone")
                .encode(x=x_achse, y=y_achse, color=farbe_serie)
            )
            ebenen = [flaeche, linie, schnitt_linie]

    chart = alt.layer(*ebenen, fadenkreuz, marker, punkte)
    return _basis(chart, dunkel, hoehe,
                  polster_links=_label_breite([f"{y_max:,.2f}"]))


def kerzen_chart(historie: pd.DataFrame, dunkel: bool = False, hoehe: int = 340) -> alt.Chart | None:
    """Klassischer Candlestick – Auf/Ab über Statusfarben plus Tooltip."""
    if historie is None or historie.empty:
        return None
    noetig = {"Datum", "Open", "High", "Low", "Close"}
    if not noetig.issubset(historie.columns):
        return None

    daten = historie.dropna(subset=list(noetig)).copy()
    if len(daten) < 2:
        return None
    daten["Richtung"] = ["Gestiegen" if c >= o else "Gefallen"
                         for o, c in zip(daten["Open"], daten["Close"])]
    for spalte in ("Open", "High", "Low", "Close"):
        daten[f"{spalte}Text"] = [_zahl_de(v) for v in daten[spalte]]

    farbskala = alt.Scale(
        domain=["Gestiegen", "Gefallen"], range=[STATUS_GUT, STATUS_SCHLECHT]
    )
    tooltip = [
        alt.Tooltip("Datum:T", title="Datum", format="%d.%m.%Y"),
        alt.Tooltip("OpenText:N", title="Eröffnung"),
        alt.Tooltip("HighText:N", title="Hoch"),
        alt.Tooltip("LowText:N", title="Tief"),
        alt.Tooltip("CloseText:N", title="Schluss"),
    ]

    basis = alt.Chart(daten).encode(
        x=alt.X("Datum:T", axis=alt.Axis(title=None, format="%b %y", tickCount=6)),
        color=alt.Color("Richtung:N", scale=farbskala, legend=alt.Legend(title=None)),
        tooltip=tooltip,
    )
    y_achse = alt.Y("Low:Q", scale=alt.Scale(zero=False),
                    axis=alt.Axis(title=None, labelExpr=de_format(",.2f")))
    dochte = basis.mark_rule(strokeWidth=1).encode(y=y_achse, y2="High:Q")
    koerper = basis.mark_bar(size=5, cornerRadius=1).encode(
        y=alt.Y("Open:Q", scale=alt.Scale(zero=False),
                axis=alt.Axis(title=None, labelExpr=de_format(",.2f"))),
        y2="Close:Q",
    )

    return _basis(dochte + koerper, dunkel, hoehe,
                  polster_links=_label_breite([f"{daten['High'].max():,.2f}"]))


# --------------------------------------------------------------------------- #
# Vergleich mehrerer Werte
# --------------------------------------------------------------------------- #
def vergleichs_chart(
    lang: pd.DataFrame,
    dunkel: bool = False,
    hoehe: int = 340,
) -> alt.Chart | None:
    """Mehrere Kurse auf Startwert 100 normiert – eine Achse, feste Farbfolge.

    Erwartet Spalten ``Datum``, ``Ticker``, ``Index``.
    """
    if lang is None or lang.empty:
        return None

    ticker = sorted(lang["Ticker"].unique().tolist())
    palette = SERIEN_DUNKEL if dunkel else SERIEN_HELL
    if len(ticker) > len(palette):
        ticker = ticker[: len(palette)]
        lang = lang[lang["Ticker"].isin(ticker)]

    lang = lang.copy()
    lang["IndexText"] = [_zahl_de(v, 1) for v in lang["Index"]]
    lang["KursText"] = [_zahl_de(v) for v in lang["Kurs"]]

    skala = alt.Scale(domain=ticker, range=palette[: len(ticker)])
    ink = _INK[bool(dunkel)]

    zeiger = alt.selection_point(nearest=True, on="pointermove", fields=["Datum"], empty=False)

    # Identische Achsen-Definitionen in allen Ebenen – sonst verschluckt
    # Vega-Lite beim Layern die Beschriftung.
    x_achse = alt.X("Datum:T", axis=alt.Axis(title=None, format="%b %y", tickCount=6))
    y_achse = alt.Y("Index:Q", scale=alt.Scale(zero=False),
                    axis=alt.Axis(title="Index (Start = 100)", labelExpr=de_format(",.0f")))

    linien = (
        alt.Chart(lang)
        .mark_line(strokeWidth=2, interpolate="monotone")
        .encode(
            x=x_achse, y=y_achse,
            color=alt.Color("Ticker:N", scale=skala, legend=alt.Legend(title=None)),
        )
    )

    basislinie = (
        alt.Chart(pd.DataFrame({"y": [100]}))
        .mark_rule(color=ink["achse"], strokeDash=[4, 4], strokeWidth=1)
        .encode(y="y:Q")
    )

    auswahl = (
        alt.Chart(lang)
        .mark_point(size=70, opacity=0)
        .encode(x=x_achse, y=y_achse)
        .add_params(zeiger)
    )

    fadenkreuz = (
        alt.Chart(lang)
        .mark_rule(color=ink["gedaempft"], strokeWidth=1, strokeDash=[3, 3])
        .encode(
            x=x_achse,
            tooltip=[
                alt.Tooltip("Datum:T", title="Datum", format="%d.%m.%Y"),
                alt.Tooltip("Ticker:N", title="Wert"),
                alt.Tooltip("IndexText:N", title="Index"),
                alt.Tooltip("KursText:N", title="Kurs (€)"),
            ],
        )
        .transform_filter(zeiger)
    )

    punkte = (
        alt.Chart(lang)
        .mark_point(size=70, filled=True, stroke="white", strokeWidth=2)
        .encode(x=x_achse, y=y_achse,
                color=alt.Color("Ticker:N", scale=skala, legend=None))
        .transform_filter(zeiger)
    )

    return _basis(basislinie + linien + fadenkreuz + punkte + auswahl, dunkel, hoehe,
                  polster_links=_label_breite([f"{lang['Index'].max():,.0f}", "Index (Start = 100)"],
                                              zeichenbreite=3.4))


# --------------------------------------------------------------------------- #
# Produktdaten
# --------------------------------------------------------------------------- #
def preis_histogramm(df: pd.DataFrame, dunkel: bool = False, hoehe: int = 280) -> alt.Chart | None:
    """Verteilung der Produktpreise über feste Preisklassen.

    Gleich breite Bins wären hier unlesbar: Das Sortiment reicht von 0,50 €
    bis über 270.000 €, alles außer dem ersten Balken wäre unsichtbar. Die
    Klassen aus :mod:`kern.datenbank` wachsen deshalb logarithmisch.
    """
    if df is None or df.empty or "preisklasse" not in df.columns:
        return None

    reihenfolge = [str(k) for k in df["preisklasse"].cat.categories]
    daten = (
        df.groupby("preisklasse", observed=False).size().reset_index(name="anzahl")
    )
    daten["preisklasse"] = daten["preisklasse"].astype(str)
    daten = daten[daten["anzahl"] > 0]
    if daten.empty:
        return None
    daten["anzahlText"] = [_zahl_de(v, 0) for v in daten["anzahl"]]
    daten["anteil"] = (daten["anzahl"] / daten["anzahl"].sum() * 100).round(1)
    daten["anteilText"] = [f"{_zahl_de(v, 1)} %" for v in daten["anteil"]]

    farbe = _farbe(dunkel)
    ink = _INK[bool(dunkel)]

    balken = (
        alt.Chart(daten)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color=farbe, opacity=0.9)
        .encode(
            x=alt.X("preisklasse:N", sort=reihenfolge,
                    axis=alt.Axis(title="Preisklasse", labelAngle=-35)),
            y=alt.Y("anzahl:Q", axis=alt.Axis(title="Produkte", labelExpr=de_format(",.0f"))),
            tooltip=[
                alt.Tooltip("preisklasse:N", title="Preisklasse"),
                alt.Tooltip("anzahlText:N", title="Produkte"),
                alt.Tooltip("anteilText:N", title="Anteil"),
            ],
        )
    )
    beschriftung = balken.mark_text(
        dy=-7, fontSize=11, color=ink["weich"], font="Inter"
    ).encode(text=alt.Text("anzahlText:N"))

    return _basis(balken + beschriftung, dunkel, hoehe,
                  polster_links=_label_breite([f"{daten['anzahl'].max():,.0f}"]))


def kategorie_balken(
    df: pd.DataFrame,
    spalte: str,
    titel: str,
    dunkel: bool = False,
    top: int = 12,
    hoehe: int | None = None,
    aggregat: str = "anzahl",
) -> alt.Chart | None:
    """Ranking-Balken (waagerecht) – mit direkt angeschriebenen Werten."""
    if df is None or df.empty or spalte not in df.columns:
        return None

    if aggregat == "anzahl":
        daten = (
            df[df[spalte].astype(str).str.len() > 0]
            .groupby(spalte).size().reset_index(name="wert")
        )
        format_ = ",.0f"
        achsentitel = "Anzahl Produkte"
    else:  # Durchschnittspreis
        daten = (
            df[df[spalte].astype(str).str.len() > 0]
            .groupby(spalte)["preis"].mean().round(2).reset_index(name="wert")
        )
        format_ = ",.0f"
        achsentitel = "Ø Preis in €"

    if daten.empty:
        return None
    daten = daten.sort_values("wert", ascending=False).head(top)
    nachkomma = 0 if aggregat == "anzahl" else 2
    daten["wertText"] = [_zahl_de(v, nachkomma) for v in daten["wert"]]

    farbe = _farbe(dunkel)
    ink = _INK[bool(dunkel)]
    hoehe = hoehe or max(180, 26 * len(daten))

    balken = (
        alt.Chart(daten)
        .mark_bar(cornerRadiusTopRight=4, cornerRadiusBottomRight=4, color=farbe, opacity=0.9, height=16)
        .encode(
            x=alt.X("wert:Q", axis=alt.Axis(title=achsentitel, labelExpr=de_format(format_))),
            y=alt.Y(f"{spalte}:N", sort="-x", axis=alt.Axis(title=None, labelLimit=220)),
            tooltip=[
                alt.Tooltip(f"{spalte}:N", title=titel),
                alt.Tooltip("wertText:N", title=achsentitel),
            ],
        )
    )
    beschriftung = balken.mark_text(
        align="left", dx=6, fontSize=11, color=ink["weich"], font="Inter"
    ).encode(text=alt.Text("wertText:N"))

    return _basis(balken + beschriftung, dunkel, hoehe,
                  polster_links=_label_breite(daten[spalte]))


def bewertung_streuung(df: pd.DataFrame, dunkel: bool = False, hoehe: int = 320) -> alt.Chart | None:
    """Preis gegen Bewertung – Punktgröße zeigt die Menge der Rezensionen."""
    if df is None or df.empty:
        return None
    daten = df[df["bewertung"].notna() & (df["bewertung"] > 0)][
        ["preis", "bewertung", "anzahl_bewertungen", "kurztitel", "marke"]
    ].copy()
    if daten.empty:
        return None
    daten["preisText"] = [_zahl_de(v) for v in daten["preis"]]
    daten["bewertungText"] = [_zahl_de(v, 1) for v in daten["bewertung"]]

    farbe = _farbe(dunkel)
    chart = (
        alt.Chart(daten)
        .mark_circle(opacity=0.62, color=farbe, stroke="white", strokeWidth=0.6, clip=True)
        .encode(
            x=alt.X("preis:Q", scale=alt.Scale(type="sqrt"),
                    axis=alt.Axis(title="Preis in €", labelExpr=de_format(",.0f"))),
            y=alt.Y("bewertung:Q", scale=alt.Scale(domain=[2.5, 5.05]),
                    axis=alt.Axis(title="Bewertung", labelExpr=de_format(",.1f"))),
            size=alt.Size("anzahl_bewertungen:Q", scale=alt.Scale(range=[25, 620]),
                          legend=alt.Legend(title="Rezensionen", format=",.0f")),
            tooltip=[
                alt.Tooltip("kurztitel:N", title="Produkt"),
                alt.Tooltip("marke:N", title="Marke"),
                alt.Tooltip("preisText:N", title="Preis (€)"),
                alt.Tooltip("bewertungText:N", title="Bewertung"),
                alt.Tooltip("anzahl_bewertungen:Q", title="Rezensionen", format=",.0f"),
            ],
        )
    )
    return _basis(chart, dunkel, hoehe)


def performance_balken(performance: dict[str, float | None], dunkel: bool = False,
                       hoehe: int = 240) -> alt.Chart | None:
    """Rendite über verschiedene Zeiträume – Vorzeichen als Statusfarbe + Label."""
    eintraege = [(k, v) for k, v in (performance or {}).items() if v is not None]
    if not eintraege:
        return None

    daten = pd.DataFrame(eintraege, columns=["Zeitraum", "Rendite"])
    daten["Richtung"] = ["Plus" if v >= 0 else "Minus" for v in daten["Rendite"]]
    daten["Label"] = [f"{'+' if v > 0 else ''}{_zahl_de(v, 1)} %" for v in daten["Rendite"]]

    ink = _INK[bool(dunkel)]
    skala = alt.Scale(domain=["Plus", "Minus"], range=[STATUS_GUT, STATUS_SCHLECHT])

    balken = (
        alt.Chart(daten)
        .mark_bar(cornerRadius=4, height=18)
        .encode(
            x=alt.X("Rendite:Q", axis=alt.Axis(title="Veränderung in %", labelExpr=de_format(",.0f"))),
            y=alt.Y("Zeitraum:N", sort=list(daten["Zeitraum"]), axis=alt.Axis(title=None)),
            color=alt.Color("Richtung:N", scale=skala, legend=alt.Legend(title=None)),
            tooltip=[
                alt.Tooltip("Zeitraum:N"),
                alt.Tooltip("Label:N", title="Veränderung"),
            ],
        )
    )
    def _labels(teilmenge: pd.DataFrame, align: str, dx: int):
        return (
            alt.Chart(teilmenge)
            .mark_text(align=align, dx=dx, fontSize=11, color=ink["weich"], font="Inter")
            .encode(
                x=alt.X("Rendite:Q"),
                y=alt.Y("Zeitraum:N", sort=list(daten["Zeitraum"])),
                text="Label:N",
            )
        )

    positiv = daten[daten["Rendite"] >= 0]
    negativ = daten[daten["Rendite"] < 0]
    beschriftungen = [
        _labels(teil, ausrichtung, versatz)
        for teil, ausrichtung, versatz in ((positiv, "left", 6), (negativ, "right", -6))
        if not teil.empty
    ]
    nulllinie = (
        alt.Chart(pd.DataFrame({"x": [0]}))
        .mark_rule(color=ink["achse"], strokeWidth=1)
        .encode(x="x:Q")
    )
    return _basis(alt.layer(nulllinie, balken, *beschriftungen), dunkel, hoehe,
                  polster_links=_label_breite(daten["Zeitraum"]))


def budget_donut(genutzt: float, rest: float, dunkel: bool = False,
                 hoehe: int = 220) -> alt.Chart | None:
    """Wie viel vom Budget im Warenkorb landet – als Ring mit zwei Segmenten."""
    if genutzt <= 0 and rest <= 0:
        return None
    ink = _INK[bool(dunkel)]
    farbe = _farbe(dunkel)

    daten = pd.DataFrame(
        {
            "Teil": ["Im Warenkorb", "Restgeld"],
            "Betrag": [max(genutzt, 0), max(rest, 0)],
        }
    )
    daten["BetragText"] = [_zahl_de(v) for v in daten["Betrag"]]
    skala = alt.Scale(domain=["Im Warenkorb", "Restgeld"], range=[farbe, ink["raster"]])

    chart = (
        alt.Chart(daten)
        .mark_arc(innerRadius=58, outerRadius=88, cornerRadius=3, padAngle=0.02)
        .encode(
            theta=alt.Theta("Betrag:Q", stack=True),
            color=alt.Color("Teil:N", scale=skala, legend=alt.Legend(title=None)),
            tooltip=[
                alt.Tooltip("Teil:N"),
                alt.Tooltip("BetragText:N", title="Betrag (€)"),
            ],
        )
    )
    return _basis(chart, dunkel, hoehe, polster_links=10)
