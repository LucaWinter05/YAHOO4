

import yfinance as yf
import currency_converter as cc
import re



class get_data:
    def __init__(self, übergabe):

        self.daten = übergabe
        converter = cc.CurrencyConverter()
        self.suche = yf.Search(self.daten)
        quote = self.suche.quotes[0]
        self.ticker = quote['symbol']
        self.ist_aktie = quote.get("quoteType") in ("EQUITY", "STOCK")
        self.ist_derivat = quote.get("quoteType") in ("OPTION", "FUTURE", "FUTURES")
        suchtext = " ".join(str(quote.get(feld, "")) for feld in ("symbol", "shortname", "longname"))
        hebel = re.search(r"(\d+(?:[.,]\d+)?)\s*x(?:\s*(?:lev|leveraged))?", suchtext, re.IGNORECASE)
        self.hebel = f"{hebel.group(1).replace(',', '.')}x" if hebel else None
        self.ist_derivat = self.ist_derivat or self.hebel is not None
        self.aktie = yf.Ticker(self.ticker)
        self.währung = self.aktie.fast_info['currency']
        self.preis = converter.convert( self.aktie.fast_info['last_price'], self.währung, 'EUR'
        )
        self.währung = "EUR"
        
        self.historie = self.aktie.history(period="1y")[['Close']]

        if self.ist_aktie:
            self.marktkapitalisierung = converter.convert(self.aktie.fast_info['market_cap'], self.währung, 'EUR')
            
        else:
            fondgröße = (self.aktie.info.get('totalAssets') or
                          self.aktie.info.get('netAssets') or
                          quote.get('totalAssets') or
                          quote.get('netAssets'))
            self.fondgröße = converter.convert(fondgröße, self.währung, 'EUR') if fondgröße is not None else None
        
        if self.ist_derivat:
            original_waehrung = self.aktie.fast_info['currency']
            self.derivat_preis = converter.convert(
                self.aktie.fast_info["last_price"],
                original_waehrung,
                "EUR"
            ) 
class search:
    def __init__(self, searchterm):
        self.results = yf.Search(searchterm)
