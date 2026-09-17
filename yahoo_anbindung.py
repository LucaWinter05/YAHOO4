

import yfinance as yf
import currency_converter as cc



class get_data:
    def __init__(self, übergabe):

        self.daten = übergabe
        converter = cc.CurrencyConverter()
        self.suche = yf.Search(self.daten)
        quote = self.suche.quotes[0]
        self.ticker = quote['symbol']
        self.ist_aktie = quote.get('quoteType') in ('EQUITY', 'STOCK')
        self.aktie = yf.Ticker(self.ticker)
        self.währung = self.aktie.fast_info['currency']
        self.preis = converter.convert( self.aktie.fast_info['last_price'], self.währung, 'EUR'
        )
        self.währung = "EUR"
        
        self.historie = self.aktie.history(period="1y")[['Close']]

        if self.ist_aktie:
            self.marktkapitalisierung = converter.convert(self.aktie.fast_info['market_cap'], self.währung, 'EUR')
            
        else:
            fondsgröße = (self.aktie.info.get('totalAssets') or
                          self.aktie.info.get('netAssets') or
                          quote.get('totalAssets') or
                          quote.get('netAssets'))
            
        # print(f"Eine Aktie kostet von {self.suche.quotes[0]['longname']} / {self.ticker} kostet {round(self.aktie.fast_info['lastPrice'], 2)}$")
        # print(f"Die Marktkapitalisierung von {self.suche.quotes[0]['longname']} / {self.ticker} beträgt {round(self.aktie.fast_info['marketCap'], 2)}$")

class search:
    def __init__(self, searchterm):
        self.results = yf.Search(searchterm)
