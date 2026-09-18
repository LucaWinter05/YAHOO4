import sqlite3
con = sqlite3.connect("otto_produkte.db")
print("Teuerstes:  ", con.execute(
    "SELECT titel, preis, suchbegriff FROM produkte "
    "WHERE preis IS NOT NULL ORDER BY preis DESC LIMIT 1").fetchone())
print("Guenstigstes:", con.execute(
    "SELECT titel, preis, suchbegriff FROM produkte "
    "WHERE preis IS NOT NULL ORDER BY preis ASC LIMIT 1").fetchone())