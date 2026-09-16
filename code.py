
import yfinance as yf


class get_data:
    def __init__(self,übergabe):

        self.daten=übergabe

        self.suche = yf.Search(self.daten)
        self.ticker = self.suche.quotes[0]['symbol']


        self.aktie = yf.Ticker(self.ticker)
        self.preis = self.aktie.fast_fast_info['lastPrice']
        self.marktkapitalisierung = self.aktie.fast_info['marketCap']
        # print(f"Eine Aktie kostet von {self.suche.quotes[0]['longname']} / {self.ticker} kostet {round(self.aktie.fast_info['lastPrice'], 2)}$")
        # print(f"Die Marktkapitalisierung von {self.suche.quotes[0]['longname']} / {self.ticker} beträgt {round(self.aktie.fast_info['marketCap'], 2)}$")
