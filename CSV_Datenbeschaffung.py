import json
from bs4 import BeautifulSoup
import pandas as pd
import os

os.chdir('\\seiten')

for file in os.listdir('C:\\Users\\JONASCHN\\YAHOO\\seiten'):
    with open(file, 'r', encoding='utf-8') as datei:
        html_inhalt = datei.read()

    soup = BeautifulSoup(html_inhalt, 'html.parser')

    produkte_liste = []
    skript_tags = soup.find_all('script', type='application/ld+json')

    for tag in skript_tags:
        try:
            daten = json.loads(tag.string)

            if daten.get('@type') == 'Product':
                name = daten.get('name')

                bild_url = daten.get('image')

                relativer_link = daten.get('url')
                produkt_link = f"https://www.otto.de{relativer_link}" if relativer_link else None

                brand_daten = daten.get('brand')
                marke = brand_daten.get('name') if isinstance(brand_daten, dict) else 'Unbekannt'

                rating_daten = daten.get('aggregateRating')
                bewertung = rating_daten.get('ratingValue') if isinstance(rating_daten, dict) else None
                anzahl_bewertungen = rating_daten.get('reviewCount') if isinstance(rating_daten, dict) else 0

                offers = daten.get('offers')
                preis = None
                if offers:
                    if isinstance(offers, list) and len(offers) > 0:
                        preis = offers[0].get('price')
                    elif isinstance(offers, dict):
                        preis = offers.get('price')

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
            continue

    if produkte_liste:
        df_neu = pd.DataFrame(produkte_liste)
        csv_name = 'otto_produkte.csv'

        if os.path.exists(csv_name):
            df_alt = pd.read_csv(csv_name)

            df_gesamt = pd.concat([df_alt, df_neu], ignore_index=True)
            print(f"Bestehende Datei '{csv_name}' gefunden. Neue Daten werden angehängt...")
        else:
            df_gesamt = df_neu
            print(f"Keine bestehende Datei gefunden. Neue Datei '{csv_name}' wird erstellt...")

        df_gesamt = df_gesamt.drop_duplicates(subset=['Produkt'])

        df_gesamt.to_csv(csv_name, index=False, encoding='utf-8')

        print("--- ERFOLG ---")
        print(f"Die CSV-Datei enthält jetzt insgesamt {len(df_gesamt)} einzigartige Produkte!")
        print("Die neuesten 3 Produkte in der Liste: ")
        print(df_gesamt.tail(3))  # 'tail' zeigt die letzten Zeilen der Datei an
    else:
        print("Keine Produkte im HTML gefunden.")