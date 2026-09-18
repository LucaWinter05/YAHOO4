# 🛒 OTTO Aktien-Matcher

> Was bekommst du für den Preis einer Aktie? Diese App übersetzt jeden
> Börsenkurs in echte Dinge aus dem OTTO-Sortiment – vom Kugelschreiber
> bis zum Seidenteppich.

**Live:** https://otto-aktien-matcher.streamlit.app/

---

## Was die App kann

| Bereich | Inhalt |
|---|---|
| 🎯 **Matcher** | Bestes Einzelprodukt zum Kurs, Alternativen mit Vielfachen („3× Teppich"), Restgeld-Anzeige, teilbarer Ergebnis-Link |
| 🧺 **Warenkorb** | Greedy-Packung, die das Budget mit möglichst vielen *verschiedenen* Produkten ausreizt – inklusive Ausnutzungsquote und CSV-Export |
| 📈 **Analyse** | Kursverlauf (Linie oder Candlestick), 50-Tage-Schnitt, Rendite je Zeitraum, Volatilität, Max-Drawdown, Analysten-Kursziel, 52-Wochen-Spanne, Unternehmensprofil |
| ⏳ **Zeitmaschine** | „Hätte ich den Produktpreis vor 3 Jahren investiert …" inkl. Rendite p. a. |
| 🛍️ **Produkte** | Volltextsuche über den kompletten Datenbestand, Sortierung, Karten- oder Tabellenansicht, CSV-Export |
| 📊 **Insights** | Preisverteilung, Preis-vs-Bewertung-Streuung, Marken-Ranking, teuerste Kategorien, Rabatt-Hitliste |
| ⭐ **Watchlist** | Bis zu acht Werte auf Startwert 100 normiert vergleichen + Kennzahlen-Tabelle |

Dazu: Hell-/Dunkel-Design (folgt automatisch dem Streamlit-Theme), Filter für
Preis, Bewertung, Rabatt, Marke und Kategorie, Budget-Multiplikator
(„10 Anteile statt einem"), Schnellauswahl beliebter Werte, Zufallsbutton
und ein Suchverlauf.

Unterstützt werden Aktien, ETFs, Fonds, Kryptowährungen und Derivate.
Alle Beträge werden nach Euro umgerechnet – inklusive des Klassikers
„LSE notiert in Pence, die Marktkapitalisierung aber in Pfund".

---

## Schnellstart

```bash
uv sync                  # Abhängigkeiten installieren
uv run streamlit run app.py
```

Ohne `uv`:

```bash
pip install -e .
streamlit run app.py
```

## Tests

```bash
uv run --group dev pytest
```

Die Tests für Formatierung, Matching und Datenbank laufen komplett offline;
der Smoke-Test rendert die Startseite über `streamlit.testing`.

---

## Projektstruktur

```
app.py                  Streamlit-Oberfläche (Layout, Zustand, Tabs)
kern/
├── formatierung.py     Zahlen, Preise, Kurznamen
├── markt.py            Yahoo Finance: Suche, Kurse, Kennzahlen (gecacht)
├── datenbank.py        Zugriff auf otto_produkte.db (als DataFrame)
├── matcher.py          Budget → Produkt, Alternativen, Warenkorb
├── diagramme.py        Altair-Charts (hell & dunkel)
└── theme.py            Design-System: CSS, Hero, Karten, KPIs
otto_scraper.py         OTTO-Scraper (requests + BeautifulSoup)
daily_scrape.py         Täglicher Scrape-Lauf in die SQLite-DB
tests/                  pytest-Suite
.streamlit/config.toml  Natives Theme (hell & dunkel)
```

### Datenfluss

```
randomprodukte.txt ──► daily_scrape.py ──► otto_produkte.db
                            (GitHub Action, täglich 05:00 UTC)

Yahoo Finance ──► kern.markt ──┐
                               ├──► kern.matcher ──► app.py
otto_produkte.db ──► kern.datenbank ──┘
```

## Datenbank aktualisieren

```bash
uv run daily_scrape.py                    # alle Suchbegriffe, je 5 Produkte
uv run daily_scrape.py --max-terms 3 --limit 2   # kurzer Testlauf
```

Die GitHub Action `daily-scape.yml` erledigt das automatisch und committet
die aktualisierte Datenbank zurück ins Repo.

---

## Technische Notizen

* **Caching:** Kurse (5 min), Suchergebnisse (10 min), Wechselkurse (6 h) und
  die Produktdatenbank (10 min) liegen in `st.cache_data`. Ohne das würde
  jeder Klick neue Yahoo-Requests auslösen.
* **Keine offene SQLite-Verbindung:** Streamlit führt jeden Rerun in einem
  anderen Thread aus. Die Datenbank wird deshalb einmal komplett in einen
  DataFrame geladen und gecacht.
* **Robustheit:** `kern.markt` wirft nie – fehlt ein Feld (bei ETFs und Krypto
  liefert Yahoo andere Teilmengen), bleibt es schlicht leer und die passende
  Kachel wird ausgeblendet.
* **Diagramme:** eine Achse pro Chart, feste Farbreihenfolge für Serien,
  Legende ab zwei Serien, Hover-Tooltip überall, getrennt gewählte
  Farbwerte für hell und dunkel.

## Haftungsausschluss

Spaß- und Lernprojekt. **Keine Anlageberatung.** Kurse können verzögert sein,
Produktpreise stammen vom letzten Scrape und können auf otto.de abweichen.
