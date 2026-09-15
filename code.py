
import yfinance as yf

firma = input("Gib einen Firmennamen/ Ticker ein: ")

# 2. Ticker automatisch über die Suche finden
suche = yf.Search(firma)
ticker = suche.quotes[0]['symbol']

# 3. Preis abrufen und anzeigen
aktie = yf.Ticker(ticker)
preis = aktie.fast_info['lastPrice']
print(f"Eine Aktie kostet von {suche.quotes[0]['longname']} / {ticker} kostet {round(aktie.fast_info['lastPrice'], 2)}$")
print(f"Die Marktkapitalisierung von {suche.quotes[0]['longname']} / {ticker} beträgt {round(aktie.fast_info['marketCap'], 2)}$")
