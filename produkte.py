import pandas as pd
import os
import random


class rand_prod:
    def __init__(self):
        csv = pd.read_csv("otto_produkte.csv")
        produktnr = random.randint(0,len(csv)-1)
        self.produkt = csv.iloc[produktnr, 0]
        self.preis_euro = csv.iloc[produktnr, 1]
        self.marke = csv.iloc[produktnr, 2]
        self.bild_url = csv.iloc[produktnr, 3]
        self.produkt_url = csv.iloc[produktnr, 4]
        self.bewertung = csv.iloc[produktnr, 5]
        self.anzahl_bewertungen = csv.iloc[produktnr, 6]

    def get_produkt(self):
        return self.produkt
    def get_produkt_url(self):
        return self.produkt_url
    def get_preis(self):
        return self.preis_euro
    def get_marke(self):
        return self.marke
    def get_bild_url(self):
        return self.bild_url
    def get_bewertung(self):
        return self.bewertung
    def get_anzahl_bewertungen(self):
        return self.anzahl_bewertungen

    def calc_wert(self, aktie):
        return round((aktie / self.preis_euro), 2)


# mein_produkt = produkte()
# preis = mein_produkt.get_preis()
# print(preis)