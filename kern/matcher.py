"""Die eigentliche Matching-Logik: Aktienpreis rein, Einkaufsliste raus.

Drei Betriebsarten:

``hauptprodukt``  Das teuerste Einzelprodukt, das vom Budget noch bezahlbar ist.
``alternativen``  Mehrere günstigere Produkte inkl. „wie oft geht das rein?“.
``warenkorb``     Ein möglichst voll ausgereizter Einkaufswagen (Greedy-Packung).

Bewusst ohne Streamlit-Import – dadurch bleibt alles einzeln testbar.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

__all__ = [
    "Filter",
    "Treffer",
    "Warenkorb",
    "filtere",
    "finde_hauptprodukt",
    "finde_alternativen",
    "baue_warenkorb",
    "vielfaches",
    "budget_ampel",
]


# --------------------------------------------------------------------------- #
# Filter
# --------------------------------------------------------------------------- #
@dataclass
class Filter:
    """Alle Einschränkungen, die der Nutzer in der Seitenleiste setzen kann."""

    min_preis: float = 0.0
    max_preis: float | None = None
    min_bewertung: float = 0.0
    min_bewertungen: int = 0
    nur_rabatt: bool = False
    nur_mit_bild: bool = False
    marken: tuple[str, ...] = ()
    kategorien: tuple[str, ...] = ()
    datum: str | None = None

    def ist_aktiv(self) -> bool:
        return bool(
            self.min_preis > 0
            or self.max_preis
            or self.min_bewertung > 0
            or self.min_bewertungen > 0
            or self.nur_rabatt
            or self.nur_mit_bild
            or self.marken
            or self.kategorien
        )


def filtere(df: pd.DataFrame, f: Filter | None = None) -> pd.DataFrame:
    """Wendet einen :class:`Filter` auf den Produkt-DataFrame an."""
    if df.empty or f is None:
        return df

    maske = pd.Series(True, index=df.index)

    if f.datum:
        maske &= df["scraped_date"] == f.datum
    if f.min_preis:
        maske &= df["preis"] >= f.min_preis
    if f.max_preis:
        maske &= df["preis"] <= f.max_preis
    if f.min_bewertung:
        maske &= df["bewertung"].fillna(0) >= f.min_bewertung
    if f.min_bewertungen:
        maske &= df["anzahl_bewertungen"].fillna(0) >= f.min_bewertungen
    if f.nur_rabatt:
        maske &= df["rabatt_pct"] > 0
    if f.nur_mit_bild:
        maske &= df["bild_url"].astype(str).str.len() > 0
    if f.marken:
        maske &= df["marke"].isin(list(f.marken))
    if f.kategorien:
        maske &= df["suchbegriff"].isin(list(f.kategorien))

    return df[maske]


# --------------------------------------------------------------------------- #
# Ergebnis-Typen
# --------------------------------------------------------------------------- #
@dataclass
class Treffer:
    """Ein Produkt plus die Anzahl, die vom Budget bezahlbar wäre."""

    zeile: pd.Series
    anzahl: int = 1

    @property
    def preis(self) -> float:
        return float(self.zeile["preis"])

    @property
    def gesamt(self) -> float:
        return round(self.preis * self.anzahl, 2)

    @property
    def url(self) -> str:
        return str(self.zeile["produkt_url"])

    @property
    def titel(self) -> str:
        return str(self.zeile.get("kurztitel") or self.zeile["titel"])


@dataclass
class Warenkorb:
    """Ergebnis der Greedy-Packung."""

    positionen: list[Treffer] = field(default_factory=list)
    budget: float = 0.0

    @property
    def summe(self) -> float:
        return round(sum(t.gesamt for t in self.positionen), 2)

    @property
    def rest(self) -> float:
        return round(self.budget - self.summe, 2)

    @property
    def ausnutzung(self) -> float:
        """Wie viel Prozent des Budgets landen im Einkaufswagen?"""
        if self.budget <= 0:
            return 0.0
        return min(100.0, self.summe / self.budget * 100)

    @property
    def stueckzahl(self) -> int:
        return sum(t.anzahl for t in self.positionen)

    def __bool__(self) -> bool:
        return bool(self.positionen)


# --------------------------------------------------------------------------- #
# Matching
# --------------------------------------------------------------------------- #
def vielfaches(preis: float | None, budget: float, minimum: int = 1) -> int:
    """Wie oft passt ``preis`` in ``budget``? (mindestens ``minimum``)"""
    if not preis or preis <= 0 or budget <= 0:
        return minimum
    return max(minimum, int(budget // preis))


def finde_hauptprodukt(df: pd.DataFrame, budget: float) -> pd.Series | None:
    """Das teuerste Produkt, das gerade noch ins Budget passt."""
    if df.empty or budget <= 0:
        return None
    bezahlbar = df[df["preis"] <= budget]
    if bezahlbar.empty:
        return None
    return bezahlbar.sort_values("preis", ascending=False).iloc[0]


def finde_alternativen(
    df: pd.DataFrame,
    budget: float,
    ausschluss_urls: tuple[str, ...] = (),
    anzahl: int = 3,
    min_vielfaches: int = 2,
) -> list[Treffer]:
    """Günstigere Alternativen, die mindestens ``min_vielfaches``-mal reingehen.

    Pro Kategorie (``suchbegriff``) wird höchstens ein Produkt vorgeschlagen,
    damit nicht dreimal derselbe Teppich in unterschiedlicher Farbe erscheint.
    """
    if df.empty or budget <= 0 or anzahl <= 0:
        return []

    obergrenze = budget / max(min_vielfaches, 1)
    kandidaten = df[(df["preis"] <= obergrenze) & (~df["produkt_url"].isin(list(ausschluss_urls)))]
    if kandidaten.empty:
        return []

    kandidaten = kandidaten.sort_values("preis", ascending=False)

    treffer: list[Treffer] = []
    gesehene_kategorien: set[str] = set()
    for _, zeile in kandidaten.iterrows():
        kategorie = str(zeile.get("suchbegriff", ""))
        if kategorie in gesehene_kategorien:
            continue
        gesehene_kategorien.add(kategorie)
        treffer.append(Treffer(zeile, vielfaches(zeile["preis"], budget, min_vielfaches)))
        if len(treffer) >= anzahl:
            break
    return treffer


def baue_warenkorb(
    df: pd.DataFrame,
    budget: float,
    max_positionen: int = 12,
    mehrfach_erlauben: bool = True,
) -> Warenkorb:
    """Füllt das Budget möglichst gut mit verschiedenen Produkten aus.

    Verfahren: Greedy von teuer nach günstig – dabei jede Kategorie nur einmal.
    Anschließend wird der Restbetrag in einer zweiten Runde mit allem gefüllt,
    was noch passt. Das ist keine exakte Rucksack-Lösung (die wäre bei großen
    Budgets zu teuer), liefert aber in der Praxis über 95 % Ausnutzung.
    """
    korb = Warenkorb(budget=budget)
    if df.empty or budget <= 0:
        return korb

    kandidaten = df[df["preis"] <= budget].sort_values("preis", ascending=False)
    if kandidaten.empty:
        return korb

    rest = budget
    gesehene_kategorien: set[str] = set()
    genommene_urls: set[str] = set()

    # Runde 1: möglichst teure, möglichst verschiedene Produkte
    for _, zeile in kandidaten.iterrows():
        if len(korb.positionen) >= max_positionen:
            break
        preis = float(zeile["preis"])
        kategorie = str(zeile.get("suchbegriff", ""))
        if preis > rest or kategorie in gesehene_kategorien:
            continue
        korb.positionen.append(Treffer(zeile, 1))
        genommene_urls.add(str(zeile["produkt_url"]))
        gesehene_kategorien.add(kategorie)
        rest = round(rest - preis, 2)

    # Runde 2: Restbetrag mit allem auffüllen, was noch hineinpasst
    if rest > 0:
        nachzuegler = kandidaten[~kandidaten["produkt_url"].isin(genommene_urls)]
        for _, zeile in nachzuegler.iterrows():
            if rest <= 0:
                break
            preis = float(zeile["preis"])
            if preis > rest:
                continue
            if len(korb.positionen) < max_positionen:
                korb.positionen.append(Treffer(zeile, 1))
                genommene_urls.add(str(zeile["produkt_url"]))
                rest = round(rest - preis, 2)

    # Runde 3: was übrig bleibt, geht in Mehrfachkäufe des günstigsten Artikels
    if mehrfach_erlauben and rest > 0 and korb.positionen:
        guenstigste = min(korb.positionen, key=lambda t: t.preis)
        zusatz = int(rest // guenstigste.preis) if guenstigste.preis > 0 else 0
        if zusatz > 0:
            guenstigste.anzahl += zusatz

    return korb


def budget_ampel(ausnutzung: float) -> tuple[str, str]:
    """Farbe + Text zur Budgetausnutzung (für die UI-Badges)."""
    if ausnutzung >= 95:
        return "gut", "Budget nahezu perfekt ausgereizt"
    if ausnutzung >= 80:
        return "ok", "Solide Ausnutzung – ein bisschen Luft bleibt"
    return "schwach", "Viel Restgeld – probier mehr Positionen oder weniger Filter"
