"""Tests gegen die echte Produktdatenbank (read-only)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kern import datenbank  # noqa: E402

pytestmark = pytest.mark.skipif(
    not datenbank.DB_PFAD.exists(), reason="otto_produkte.db liegt nicht im Repo"
)


@pytest.fixture(scope="module")
def df():
    return datenbank.lade_produkte()


def test_datenbank_ist_nicht_leer(df):
    assert len(df) > 0


def test_erwartete_spalten_sind_da(df):
    for spalte in ("preis", "titel", "produkt_url", "rabatt_pct", "ersparnis", "kurztitel"):
        assert spalte in df.columns


def test_nur_positive_preise(df):
    assert (df["preis"] > 0).all()


def test_rabatt_ist_plausibel(df):
    assert df["rabatt_pct"].between(0, 100).all()


def test_ersparnis_passt_zum_rabatt(df):
    mit_rabatt = df[df["rabatt_pct"] > 0]
    if not mit_rabatt.empty:
        assert (mit_rabatt["ersparnis"] > 0).all()


def test_kennzahlen_sind_konsistent():
    kz = datenbank.kennzahlen()
    assert kz.anzahl > 0
    assert kz.guenstigstes <= kz.median <= kz.teuerstes
    assert kz.tage_historie >= 1


def test_als_produkt_uebersetzt_eine_zeile(df):
    produkt = datenbank.als_produkt(df.iloc[0])
    assert produkt.title
    assert produkt.product_url.startswith("http")
    assert produkt.display_price.endswith("€")


def test_produkt_nach_url_findet_den_datensatz(df):
    url = df.iloc[0]["produkt_url"]
    assert datenbank.produkt_nach_url(url) is not None


def test_produkt_nach_url_bei_unbekannter_url():
    assert datenbank.produkt_nach_url("https://example.invalid/") is None
