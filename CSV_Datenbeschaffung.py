import json
from bs4 import BeautifulSoup
import pandas as pd
import os

os.chdir('\\seiten')

for file in os.listdir('C:\\Users\\JONASCHN\\YAHOO\\seiten'):
    # 1. Lokale HTML-Datei einlesen
    with open(file, 'r', encoding='utf-8') as datei:
        html_inhalt = datei.read()

    soup = BeautifulSoup(html_inhalt, 'html.parser')

    produkte_liste = []

    # 2. Nach den JSON-LD Blöcken suchen
    skript_tags = soup.find_all('script', type='application/ld+json')

    for tag in skript_tags:
        try:
            daten = json.loads(tag.string)

            if daten.get('@type') == 'Product':
                # Name
                name = daten.get('name')

                # Bild-URL
                bild_url = daten.get('image')

                # Produkt-Link (wir hängen die Otto-Domain davor)
                relativer_link = daten.get('url')
                produkt_link = f"https://www.otto.de{relativer_link}" if relativer_link else None

                # Marke
                brand_daten = daten.get('brand')
                marke = brand_daten.get('name') if isinstance(brand_daten, dict) else 'Unbekannt'

                # Sterne-Bewertung
                rating_daten = daten.get('aggregateRating')
                bewertung = rating_daten.get('ratingValue') if isinstance(rating_daten, dict) else None
                anzahl_bewertungen = rating_daten.get('reviewCount') if isinstance(rating_daten, dict) else 0

                # Preis aus "offers" holen
                offers = daten.get('offers')
                preis = None
                if offers:
                    if isinstance(offers, list) and len(offers) > 0:
                        preis = offers[0].get('price')
                    elif isinstance(offers, dict):
                        preis = offers.get('price')

                # Nur hinzufügen, wenn wir die wichtigsten Infos (Name, Preis, Bild) haben
                if name and preis and bild_url:
                    produkte_liste.append({
                        'Produkt': name,
                        'Preis_Euro': float(preis),
                        'Marke': marke,
                        'Bild_URL': bild_url,
                        'Produkt_URL': produkt_link,
                        'Bewertung': float(bewertung) if bewertung else 0.0,
                        'Anzahl_Bewertungen': int(anzahl_bewertungen)
                    })
        except Exception:
            # Fehlerhafte Blöcke einfach überspringen
            continue

    import os  # Ganz oben im Skript hinzufügen!
    import json
    from bs4 import BeautifulSoup
    import pandas as pd

    # ... (Hier bleibt dein bisheriger Code zum Einlesen und Parsen der HTML-Datei exakt gleich) ...

    # 3. Mit pandas speichern (Smart Append)
    if produkte_liste:
        df_neu = pd.DataFrame(produkte_liste)
        csv_name = 'otto_produkte.csv'

        # Prüfen, ob die Datei schon existiert
        if os.path.exists(csv_name):
            # 1. Die alten Daten aus der CSV einlesen
            df_alt = pd.read_csv(csv_name)

            # 2. Die alten und die neu gescrapten Daten untereinanderkleben
            df_gesamt = pd.concat([df_alt, df_neu], ignore_index=True)
            print(f"Bestehende Datei '{csv_name}' gefunden. Neue Daten werden angehängt...")
        else:
            # Wenn es die Datei noch nicht gibt, starten wir mit den neuen Daten
            df_gesamt = df_neu
            print(f"Keine bestehende Datei gefunden. Neue Datei '{csv_name}' wird erstellt...")

        # 3. Duplikate entfernen (doppelte Produkte fliegen raus)
        df_gesamt = df_gesamt.drop_duplicates(subset=['Produkt'])

        # 4. Die saubere Gesamtliste wieder in der CSV-Datei speichern
        df_gesamt.to_csv(csv_name, index=False, encoding='utf-8')

        print("--- ERFOLG ---")
        print(f"Die CSV-Datei enthält jetzt insgesamt {len(df_gesamt)} einzigartige Produkte!")
        print("Die neuesten 3 Produkte in der Liste: ")
        print(df_gesamt.tail(3))  # 'tail' zeigt die letzten Zeilen der Datei an
    else:
        print("Keine Produkte im HTML gefunden.")