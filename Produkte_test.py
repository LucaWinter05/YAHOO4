import produkte

meins = produkte.rand_prod()
print(meins.get_preis())
print(meins.calc_wert(150))
print("Für diese 150 Euro könntest du dir auch " + str(meins.calc_wert(150))  + " mal \"" + str(meins.get_produkt()) + "\" (" + str(meins.get_preis()) + "€) auf otto.de kaufen")