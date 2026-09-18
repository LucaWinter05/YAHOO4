"""Tests für die Matching-Logik (Hauptprodukt, Alternativen, Warenkorb)."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kern import matcher  # noqa: E402


@pytest.fixture
def produkte() -> pd.DataFrame:
    """Kleiner, handgemachter Produktbestand mit bekannten Werten."""
    zeilen = [
        # titel,        marke,   preis,  kategorie,  bewertung, rabatt, bild
        ("Sofa",        "Ikea",  800.0,  "Möbel",    4.5,  20, "bild"),
        ("Teppich",     "OTTO",  240.0,  "Teppich",  4.0,   0, "bild"),
        ("Teppich XL",  "OTTO",  230.0,  "Teppich",  4.8,  10, "bild"),
        ("Lampe",       "Philips", 95.0, "Licht",    3.5,   0, "bild"),
        ("Kissen",      "OTTO",   25.0,  "Deko",     4.9,  50, ""),
        ("Stift",       "Bic",     1.5,  "Büro",     3.0,   0, "bild"),
    ]
    df = pd.DataFrame(
        zeilen,
        columns=["titel", "marke", "preis", "suchbegriff", "bewertung", "rabatt_pct", "bild_url"],
    )
    df["produkt_url"] = ["https://otto.de/p/" + t.lower().replace(" ", "-") for t in df["titel"]]
    df["kurztitel"] = df["titel"]
    df["anzahl_bewertungen"] = 10
    df["scraped_date"] = "2026-09-18"
    return df


class TestVielfaches:
    def test_einfache_teilung(self):
        assert matcher.vielfaches(25.0, 100.0) == 4

    def test_minimum_wird_eingehalten(self):
        assert matcher.vielfaches(80.0, 100.0, minimum=2) == 2

    def test_kein_preis(self):
        assert matcher.vielfaches(None, 100.0) == 1
        assert matcher.vielfaches(0, 100.0) == 1


class TestHauptprodukt:
    def test_teuerstes_bezahlbares(self, produkte):
        zeile = matcher.finde_hauptprodukt(produkte, 300.0)
        assert zeile["titel"] == "Teppich"

    def test_budget_reicht_fuer_nichts(self, produkte):
        assert matcher.finde_hauptprodukt(produkte, 0.5) is None

    def test_leerer_bestand(self):
        assert matcher.finde_hauptprodukt(pd.DataFrame(), 100.0) is None


class TestAlternativen:
    def test_jede_kategorie_nur_einmal(self, produkte):
        treffer = matcher.finde_alternativen(produkte, 600.0, anzahl=4)
        kategorien = [t.zeile["suchbegriff"] for t in treffer]
        assert len(kategorien) == len(set(kategorien))

    def test_ausschluss_wird_beachtet(self, produkte):
        url = produkte.iloc[1]["produkt_url"]
        treffer = matcher.finde_alternativen(produkte, 600.0, ausschluss_urls=(url,), anzahl=5)
        assert url not in [t.url for t in treffer]

    def test_mindestens_zweimal_leistbar(self, produkte):
        treffer = matcher.finde_alternativen(produkte, 500.0, min_vielfaches=2)
        assert all(t.preis * 2 <= 500.0 for t in treffer)
        assert all(t.anzahl >= 2 for t in treffer)


class TestWarenkorb:
    def test_summe_bleibt_im_budget(self, produkte):
        korb = matcher.baue_warenkorb(produkte, 1000.0)
        assert korb.summe <= 1000.0

    def test_ausnutzung_ist_hoch(self, produkte):
        korb = matcher.baue_warenkorb(produkte, 1000.0)
        assert korb.ausnutzung > 90

    def test_keine_doppelten_produkte(self, produkte):
        korb = matcher.baue_warenkorb(produkte, 1500.0)
        urls = [t.url for t in korb.positionen]
        assert len(urls) == len(set(urls))

    def test_positionslimit(self, produkte):
        korb = matcher.baue_warenkorb(produkte, 5000.0, max_positionen=2)
        assert len(korb.positionen) <= 2

    def test_zu_kleines_budget(self, produkte):
        korb = matcher.baue_warenkorb(produkte, 0.5)
        assert not korb
        assert korb.positionen == []

    def test_restgeld_wird_verrechnet(self, produkte):
        korb = matcher.baue_warenkorb(produkte, 1000.0, mehrfach_erlauben=True)
        assert korb.rest >= 0


class TestFilter:
    def test_preisspanne(self, produkte):
        gefiltert = matcher.filtere(produkte, matcher.Filter(min_preis=100, max_preis=300))
        assert set(gefiltert["titel"]) == {"Teppich", "Teppich XL"}

    def test_mindestbewertung(self, produkte):
        gefiltert = matcher.filtere(produkte, matcher.Filter(min_bewertung=4.5))
        assert set(gefiltert["titel"]) == {"Sofa", "Teppich XL", "Kissen"}

    def test_nur_rabatt(self, produkte):
        gefiltert = matcher.filtere(produkte, matcher.Filter(nur_rabatt=True))
        assert all(gefiltert["rabatt_pct"] > 0)

    def test_nur_mit_bild(self, produkte):
        gefiltert = matcher.filtere(produkte, matcher.Filter(nur_mit_bild=True))
        assert "Kissen" not in set(gefiltert["titel"])

    def test_marken(self, produkte):
        gefiltert = matcher.filtere(produkte, matcher.Filter(marken=("OTTO",)))
        assert set(gefiltert["marke"]) == {"OTTO"}

    def test_ohne_filter_bleibt_alles(self, produkte):
        assert len(matcher.filtere(produkte, None)) == len(produkte)

    def test_ist_aktiv(self):
        assert not matcher.Filter().ist_aktiv()
        assert matcher.Filter(nur_rabatt=True).ist_aktiv()


class TestAmpel:
    def test_stufen(self):
        assert matcher.budget_ampel(99)[0] == "gut"
        assert matcher.budget_ampel(85)[0] == "ok"
        assert matcher.budget_ampel(40)[0] == "schwach"
