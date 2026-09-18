"""Smoke-Test: Läuft die App ohne Exception durch?

Ohne gewählten Ticker ruft die App keine Netzwerk-Endpunkte auf – der Test
bleibt damit offline und schnell.
"""

import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WURZEL))

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest


def test_startseite_rendert_ohne_fehler():
    at = AppTest.from_file(str(WURZEL / "app.py"), default_timeout=60).run()
    assert not at.exception
    # Hero + Kennzahlen-Kacheln landen als Markdown im Baum
    assert any("Aktien-Matcher" in m.value for m in at.sidebar.markdown)


def test_farbschema_laesst_sich_umschalten():
    at = AppTest.from_file(str(WURZEL / "app.py"), default_timeout=60).run()
    auswahl = [r for r in at.sidebar.radio if r.label == "Farbschema"]
    assert auswahl, "Farbschema-Auswahl fehlt"
    auswahl[0].set_value("Dunkel").run()
    assert not at.exception
    assert at.session_state["theme_modus"] == "Dunkel"


def test_anzahl_anteile_veraendert_das_budget():
    at = AppTest.from_file(str(WURZEL / "app.py"), default_timeout=60).run()
    feld = [n for n in at.sidebar.number_input if n.label == "Anzahl Anteile"]
    assert feld
    feld[0].set_value(5).run()
    assert not at.exception
    assert at.session_state["menge"] == 5
