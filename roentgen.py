from bs4 import BeautifulSoup

with open('seite.html', 'r', encoding='utf-8') as datei:
    inhalt = datei.read()

soup = BeautifulSoup(inhalt, 'html.parser')

# Wir holen uns das allererste Produkt
erstes_produkt = soup.find('article')

if erstes_produkt:
    print("=== STRUKTUR DES ERSTEN PRODUKTS ===")
    # Gibt das HTML des ersten Artikels sauber formatiert aus (nur die ersten 1000 Zeichen)
    print(erstes_produkt.prettify()[:1000])
else:
    print("Kein Element gefunden.")