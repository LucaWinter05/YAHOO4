"""Veraltete Yahoo-Anbindung – bitte :mod:`kern.markt` verwenden.

Diese Datei bleibt nur erhalten, damit ältere Skripte und Notebooks nicht
brechen. Sie enthält keine eigene Logik mehr, sondern reicht alles an
:func:`kern.markt.lade_markt` durch. Dort sind die Dinge behoben, die hier
früher schiefgingen:

* Marktkapitalisierung britischer Werte lag um den Faktor 100 daneben
  (Kurse notieren in Pence, die Marktkapitalisierung in Pfund).
* Jeder Aufruf löste neue Yahoo-Requests aus – jetzt greift ein Cache.
* Fehlende Felder bei ETFs und Krypto führten zu ``KeyError``.
"""

from __future__ import annotations

import warnings

from kern.markt import MarktDaten, lade_markt, suche

__all__ = ["get_data", "search", "MarktDaten"]


class get_data:  # noqa: N801 – Name aus der ersten Version beibehalten
    """Dünne Hülle um :func:`kern.markt.lade_markt`.

    Stellt die Attribute der alten Klasse bereit (``preis``, ``ticker``,
    ``historie``, ``ist_aktie`` …) und ergänzt sie um alles, was
    :class:`kern.markt.MarktDaten` sonst noch kennt.
    """

    def __init__(self, übergabe: str):
        warnings.warn(
            "yahoo_anbindung.get_data ist veraltet – nutze kern.markt.lade_markt().",
            DeprecationWarning,
            stacklevel=2,
        )
        self.daten: MarktDaten = lade_markt(übergabe)
        if self.daten.fehler:
            raise ValueError(self.daten.fehler)

        # Feldnamen der ersten Version
        self.ticker = self.daten.ticker
        self.preis = self.daten.preis
        self.währung = "EUR"
        self.historie = self.daten.historie
        self.goal = self.daten.kursziel
        self.ist_aktie = self.daten.ist_aktie
        self.ist_derivat = self.daten.ist_derivat
        self.marktkapitalisierung = self.daten.marktkapitalisierung
        self.fondgröße = self.daten.fondsgroesse
        self.derivat_preis = self.daten.preis if self.daten.ist_derivat else None
        self.basiswert_preis = self.daten.basiswert_preis
        self.hebel = self.daten.hebel

    def __getattr__(self, name: str):
        # Alles Übrige direkt vom neuen Datenobjekt holen
        return getattr(self.__dict__["daten"], name)


class search:  # noqa: N801
    """Alte Suchhülle – liefert jetzt die gecachten Treffer aus ``kern.markt``."""

    def __init__(self, searchterm: str):
        self.results = suche(searchterm)
