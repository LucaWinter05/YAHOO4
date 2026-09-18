"""Tests für die Formatierungs-Helfer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kern.formatierung import (  # noqa: E402
    eur, kompakt, kurzname, prozent, pluralisieren, sterne, zahl,
)


class TestZahl:
    def test_deutsche_trennzeichen(self):
        assert zahl(1234.5) == "1.234,50"
        assert zahl(1234567.891, 2) == "1.234.567,89"

    def test_none_wird_gedankenstrich(self):
        assert zahl(None) == "–"

    def test_ohne_dezimalstellen(self):
        assert zahl(42.6, 0) == "43"


class TestEuro:
    def test_normal(self):
        assert eur(19.99) == "19,99 €"

    def test_tausender(self):
        assert eur(1999.5) == "1.999,50 €"

    def test_none(self):
        assert eur(None) == "–"


class TestKompakt:
    def test_stufen(self):
        assert kompakt(3_100_000_000_000) == "3,10 Bio. €"
        assert kompakt(2_500_000_000) == "2,50 Mrd. €"
        assert kompakt(1_500_000) == "1,50 Mio. €"
        assert kompakt(2_000) == "2,00 Tsd. €"

    def test_kleine_betraege_bleiben_ausgeschrieben(self):
        assert kompakt(999) == "999,00 €"

    def test_negativ(self):
        assert kompakt(-1_500_000).startswith("-1,50 Mio.")

    def test_none(self):
        assert kompakt(None) == "– €"


class TestProzent:
    def test_vorzeichen(self):
        assert prozent(7.34) == "+7,34 %"
        assert prozent(-2.5) == "-2,50 %"

    def test_ohne_vorzeichen(self):
        assert prozent(7.34, mit_vorzeichen=False) == "7,34 %"


class TestSterne:
    def test_halber_stern(self):
        assert sterne(4.5).startswith("★★★★½")

    def test_mit_anzahl(self):
        assert "(845)" in sterne(4.5, 845)

    def test_ohne_bewertung(self):
        assert sterne(None) == "–"


class TestKurzname:
    def test_hersteller_steht_vorn_und_nicht_doppelt(self):
        ergebnis = kurzname(
            "OTTO home Teppich Salsa, rechteckig, Höhe 9 mm, mit besonders weichem Flor",
            "OTTO home",
        )
        assert ergebnis.startswith("OTTO home")
        assert ergebnis.count("OTTO home") == 1

    def test_zahlen_und_masse_fliegen_raus(self):
        ergebnis = kurzname("Regal 120 cm breit Kiefer massiv", "")
        assert "120" not in ergebnis

    def test_maximale_wortzahl(self):
        ergebnis = kurzname("Ein sehr langer Produkttitel mit vielen Wörtern", "Marke")
        assert len(ergebnis.split()) <= 3

    def test_notnagel_bei_leerem_ergebnis(self):
        # Nur Zahlen -> es bleibt kein Wort übrig, trotzdem kein leerer String
        assert kurzname("12 34 56", "") != ""


class TestPluralisieren:
    def test_einzahl_und_mehrzahl(self):
        assert pluralisieren(1, "Produkt", "Produkte") == "1 Produkt"
        assert pluralisieren(3, "Produkt", "Produkte") == "3 Produkte"
