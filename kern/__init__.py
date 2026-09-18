"""Kern-Module des OTTO Aktien-Matchers.

Das Paket bündelt alles, was nicht direkt Streamlit-UI ist:

* :mod:`kern.formatierung` – Zahlen, Preise und Namen hübsch machen
* :mod:`kern.markt`        – Yahoo-Finance-Anbindung (gecacht & robust)
* :mod:`kern.datenbank`    – Zugriff auf die OTTO-Produktdatenbank
* :mod:`kern.matcher`      – Matching-Logik (Hauptprodukt, Alternativen, Warenkorb)
* :mod:`kern.theme`        – Design-System, CSS und UI-Bausteine
"""

__all__ = ["formatierung", "markt", "datenbank", "matcher", "theme"]
