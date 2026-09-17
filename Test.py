import sqlite3
con = sqlite3.connect("otto_produkte.db")
con.row_factory = sqlite3.Row

row = con.execute(
            "SELECT titel, marke, preis, old_price, currency, bild_url, produkt_url, "
            "bewertung, anzahl_bewertungen, verfuegbarkeit, sku, gtin "
            "FROM produkte WHERE preis IS NOT NULL "
            "ORDER BY preis DESC LIMIT 1",
        ).fetchone()
print(row["Preis"])