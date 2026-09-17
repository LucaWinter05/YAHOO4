"""Täglicher OTTO-Scrape: alle Suchbegriffe aus randomprodukte.txt, je 5 Produkte in SQLite-DB.

Aufruf:
    python daily_scrape.py
    python daily_scrape.py --limit 5 --db otto_produkte.db
    python daily_scrape.py --max-terms 2 --limit 2   # zum Testen

Die GitHub Action ruft später einfach `python daily_scrape.py` einmal am Tag auf.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sqlite3
import sys
import time
from pathlib import Path

from otto_scraper import search_otto

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_TERMS_FILE = BASE_DIR / "randomprodukte.txt"
DEFAULT_DB = BASE_DIR / "otto_produkte.db"
DEFAULT_LIMIT = 5

# noinspection SqlNoDataSourceInspection,SqlDialectInspection
SCHEMA = """
CREATE TABLE IF NOT EXISTS produkte (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scraped_date TEXT NOT NULL,
    suchbegriff TEXT NOT NULL,
    titel TEXT NOT NULL,
    marke TEXT DEFAULT '',
    preis REAL,
    old_price REAL,
    currency TEXT DEFAULT 'EUR',
    bild_url TEXT DEFAULT '',
    produkt_url TEXT NOT NULL,
    bewertung REAL,
    anzahl_bewertungen INTEGER,
    verfuegbarkeit TEXT DEFAULT '',
    sku TEXT DEFAULT '',
    gtin TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(scraped_date, produkt_url)
);
"""


def load_search_terms(path: Path) -> list[str]:
    """Liest alle \"Suchbegriffe\" aus randomprodukte.txt (gleiche Logik wie app.py)."""
    text = path.read_text(encoding="utf-8")
    terms = [t.strip() for t in re.findall(r'"([^"]+)"', text) if t.strip()]
    # Duplikate entfernen, Reihenfolge behalten
    return list(dict.fromkeys(terms))


def init_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(SCHEMA)
    conn.commit()
    return conn


def save_products(
    conn: sqlite3.Connection,
    scraped_date: str,
    suchbegriff: str,
    products: list,
) -> int:
    """Speichert Produkte eines Suchbegriffs (idempotent pro Tag via INSERT OR REPLACE)."""
    saved = 0
    for p in products:
        conn.execute(
            """
            INSERT OR REPLACE INTO produkte
                (scraped_date, suchbegriff, titel, marke, preis, old_price,
                 currency, bild_url, produkt_url, bewertung,
                 anzahl_bewertungen, verfuegbarkeit, sku, gtin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scraped_date,
                suchbegriff,
                p.title,
                p.brand or "",
                p.price,
                p.old_price,
                p.currency or "EUR",
                p.image_url or "",
                p.product_url,
                p.rating,
                p.review_count,
                p.availability or "",
                p.sku or "",
                p.gtin or "",
            ),
        )
        saved += 1
    conn.commit()
    return saved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OTTO Daily-Scrape in SQLite-DB")
    parser.add_argument("--terms-file", type=Path, default=DEFAULT_TERMS_FILE)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help="Produkte pro Suchbegriff (default: 5)")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Pause in Sekunden zwischen Suchbegriffen (default: 1.0)")
    parser.add_argument("--max-terms", type=int, default=0,
                        help="Nur für Tests: max. Anzahl Suchbegriffe (0 = alle)")
    args = parser.parse_args(argv)

    if not args.terms_file.exists():
        print(f"FEHLER: Suchbegriffe-Datei nicht gefunden: {args.terms_file}", file=sys.stderr)
        return 2

    terms = load_search_terms(args.terms_file)
    if args.max_terms and args.max_terms > 0:
        terms = terms[: args.max_terms]
    print(f"{len(terms)} Suchbegriffe aus {args.terms_file.name}, je {args.limit} Produkte -> {args.db.name}")

    conn = init_db(args.db)
    scraped_date = datetime.date.today().isoformat()

    total_saved = 0
    failed: list[str] = []
    for i, term in enumerate(terms, 1):
        try:
            products = search_otto(term, limit=args.limit)
            if not products:
                print(f"[{i}/{len(terms)}] '{term}': keine Treffer")
            else:
                n = save_products(conn, scraped_date, term, products)
                total_saved += n
                print(f"[{i}/{len(terms)}] '{term}': {n} gespeichert")
        except KeyboardInterrupt:
            print("\nAbgebrochen durch Benutzer.", file=sys.stderr)
            break
        except Exception as e:  # noqa: BLE001 - ein Begriff darf den Day-Run nicht killen
            failed.append(term)
            print(f"[{i}/{len(terms)}] '{term}': FEHLER {e}", file=sys.stderr)
        if args.delay > 0 and i < len(terms):
            time.sleep(args.delay)

    conn.close()
    print(f"Fertig: {total_saved} Produkte gespeichert (Datum: {scraped_date}).")
    if failed:
        print(f"{len(failed)} Suchbegriffe fehlgeschlagen: {', '.join(failed[:10])}"
              + (" ..." if len(failed) > 10 else ""), file=sys.stderr)
    return 0 if total_saved > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
