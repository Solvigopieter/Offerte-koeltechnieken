# pr_catalogus.py — Panasonic RAC Prijscatalogus 2026|2027 (bruto adviesprijzen, excl. BTW)
# Bron: PS0428_wt_Prijscatalogus_RAC_2026_Belgie_NL_V1_ONLINE.pdf
# Alle prijzen zijn Panasonic's "Bruto adviesprijs" — dus een aanbevolen VERKOOPPRIJS,
# niet jouw inkoopprijs. Bij selectie wordt daarom:
#   - de Verkoopprijs automatisch op deze catalogusprijs gezet (zelf aan te passen)
#   - de Inkoopprijs automatisch geschat als catalogusprijs x (1 - jouw kortingspercentage),
#     in te stellen bij Prijsinstellingen → "Panasonic-kortingspercentage"

# ---------------------------------------------------------------- MONO-SPLIT SETS
# Complete sets (binnen- + buitenunit samen), zoals gebruikt bij "Mono-split" in de tool.
MONO_SETS = [
    # Wandmodel Etherea (kleur maakt prijsverschil)
    ("Etherea", "Mat Wit", 2.0, 1699), ("Etherea", "Mat Wit", 2.5, 1848), ("Etherea", "Mat Wit", 3.5, 2229),
    ("Etherea", "Mat Wit", 4.2, 2765), ("Etherea", "Mat Wit", 5.0, 2956), ("Etherea", "Mat Wit", 7.1, 4167),
    ("Etherea", "Graphite", 2.0, 1795), ("Etherea", "Graphite", 2.5, 1957), ("Etherea", "Graphite", 3.5, 2361),
    ("Etherea", "Graphite", 4.2, 2933),
    ("Etherea", "Zilvergrijs", 2.0, 1773), ("Etherea", "Zilvergrijs", 2.5, 1984), ("Etherea", "Zilvergrijs", 3.5, 2330),
    ("Etherea", "Zilvergrijs", 5.0, 3180),
    # Wandmodel TZ
    ("TZ", "", 2.0, 1198), ("TZ", "", 2.5, 1325), ("TZ", "", 3.5, 1571), ("TZ", "", 4.2, 2188),
    ("TZ", "", 5.0, 2486), ("TZ", "", 6.0, 2818), ("TZ", "", 7.1, 3621),
    # Wandmodel BZ
    ("BZ", "", 2.5, 1144), ("BZ", "", 3.5, 1319), ("BZ", "", 5.0, 1979), ("BZ", "", 6.0, 2563),
    # Vloerconsole
    ("Vloerconsole", "", 2.5, 2238), ("Vloerconsole", "", 3.5, 2619), ("Vloerconsole", "", 5.0, 3199),
    # Kanaalmodel met lage statische druk
    ("Kanaalmodel lage druk", "", 2.5, 2478), ("Kanaalmodel lage druk", "", 3.5, 2812),
    ("Kanaalmodel lage druk", "", 5.0, 3075), ("Kanaalmodel lage druk", "", 6.0, 3519),
    # RAC Solo (geïntegreerd, geen aparte buitenunit)
    ("RAC Solo", "", 1.7, 2818), ("RAC Solo", "", 2.0, 3100), ("RAC Solo", "", 2.5, 3333), ("RAC Solo", "", 3.0, 3488),
]

# ---------------------------------------------------------------- MULTI-SPLIT BUITENUNITS
MULTI_BUITEN = [
    ("Multi Z", "CU-2Z35CBE", "3,2~6,0 kW", 1674),
    ("Multi Z", "CU-2Z41CBE", "3,2~6,0 kW", 1985),
    ("Multi Z", "CU-2Z50CBE", "3,2~7,7 kW", 2253),
    ("Multi Z", "CU-3Z52CBE", "4,5~9,5 kW", 2559),
    ("Multi Z", "CU-3Z68CBE", "4,5~11,2 kW", 2950),
    ("Multi Z", "CU-4Z68CBE", "4,5~11,5 kW", 3380),
    ("Multi Z", "CU-4Z80CBE", "4,5~14,7 kW", 3889),
    ("Multi Z", "CU-5Z90CBE", "4,5~18,3 kW", 4614),
    ("Multi TZ", "CU-2TZ41TBE", "3,2~6,0 kW", 1696),
    ("Multi TZ", "CU-2TZ50TBE", "3,2~7,7 kW", 2005),
    ("Multi TZ", "CU-3TZ52TBE", "4,5~9,5 kW", 2464),
    ("Power Heat Multi", "CU-2Z50ABEC", "4,0~8,5 kW", 3012),
    ("Power Heat Multi", "CU-3Z75ABEC", "4,5~11,0 kW", 4031),
]

# ---------------------------------------------------------------- MULTI-SPLIT BINNENUNITS
MULTI_BINNEN = [
    # Multi Z - Wandmodel Etherea (kleur)
    ("Multi Z Etherea", "Wit", 1.6, 567), ("Multi Z Etherea", "Wit", 2.0, 609), ("Multi Z Etherea", "Wit", 2.5, 685),
    ("Multi Z Etherea", "Wit", 3.5, 842), ("Multi Z Etherea", "Wit", 4.2, 994), ("Multi Z Etherea", "Wit", 5.0, 1133),
    ("Multi Z Etherea", "Wit", 7.1, 1737),
    ("Multi Z Etherea", "Grafietgrijs", 2.0, 705), ("Multi Z Etherea", "Grafietgrijs", 2.5, 794),
    ("Multi Z Etherea", "Grafietgrijs", 3.5, 974), ("Multi Z Etherea", "Grafietgrijs", 4.2, 1162),
    ("Multi Z Etherea", "Zilver", 2.0, 683), ("Multi Z Etherea", "Zilver", 2.5, 821),
    ("Multi Z Etherea", "Zilver", 3.5, 943), ("Multi Z Etherea", "Zilver", 5.0, 1357),
    # Multi Z - Wandmodel TZ
    ("Multi Z TZ", "", 1.6, 419), ("Multi Z TZ", "", 2.0, 431), ("Multi Z TZ", "", 2.5, 509),
    ("Multi Z TZ", "", 3.5, 607), ("Multi Z TZ", "", 4.2, 770), ("Multi Z TZ", "", 5.0, 898),
    ("Multi Z TZ", "", 6.0, 1135), ("Multi Z TZ", "", 7.1, 1509),
    # Multi Z - Vloerconsole
    ("Multi Z Vloerconsole", "", 2.0, 1135), ("Multi Z Vloerconsole", "", 2.5, 1187),
    ("Multi Z Vloerconsole", "", 3.5, 1365), ("Multi Z Vloerconsole", "", 5.0, 1712),
    # Multi Z - 4-weg cassette 60x60 (excl. paneel CZ-KPY4, €277 apart)
    ("Multi Z 60x60 cassette", "", 2.0, 1199), ("Multi Z 60x60 cassette", "", 2.5, 1250),
    ("Multi Z 60x60 cassette", "", 3.6, 1345), ("Multi Z 60x60 cassette", "", 5.0, 1660),
    ("Multi Z 60x60 cassette", "", 6.0, 1962),
    # Multi Z - Kanaalmodel met lage statische druk
    ("Multi Z Kanaalmodel", "", 2.0, 1286), ("Multi Z Kanaalmodel", "", 2.5, 1427),
    ("Multi Z Kanaalmodel", "", 3.5, 1558), ("Multi Z Kanaalmodel", "", 5.0, 1588),
    ("Multi Z Kanaalmodel", "", 6.0, 1752),
    # Multi TZ - Wandmodel TZ
    ("Multi TZ Wandmodel TZ", "", 1.6, 419), ("Multi TZ Wandmodel TZ", "", 2.0, 431),
    ("Multi TZ Wandmodel TZ", "", 2.5, 509), ("Multi TZ Wandmodel TZ", "", 3.5, 607),
    ("Multi TZ Wandmodel TZ", "", 4.2, 770), ("Multi TZ Wandmodel TZ", "", 5.0, 898),
    # Power Heat Multi - Wandmodel Etherea
    ("Power Heat Etherea", "Wit", 2.0, 609), ("Power Heat Etherea", "Wit", 2.5, 685),
    ("Power Heat Etherea", "Wit", 3.5, 842), ("Power Heat Etherea", "Wit", 5.0, 1133),
    ("Power Heat Etherea", "Grafietgrijs", 2.0, 705), ("Power Heat Etherea", "Grafietgrijs", 2.5, 794),
    ("Power Heat Etherea", "Grafietgrijs", 3.5, 974),
    ("Power Heat Etherea", "Zilver", 2.0, 683), ("Power Heat Etherea", "Zilver", 2.5, 821),
    ("Power Heat Etherea", "Zilver", 3.5, 943), ("Power Heat Etherea", "Zilver", 5.0, 1357),
]


def mono_label(item):
    familie, kleur, vermogen, prijs = item
    kleurtxt = f" ({kleur})" if kleur else ""
    prijs_txt = f"{prijs:,.0f}".replace(",", " ")
    return f"Panasonic {familie}{kleurtxt} {vermogen} kW — € {prijs_txt}"


def mono_naam(item):
    familie, kleur, vermogen, prijs = item
    kleurtxt = f" {kleur}" if kleur else ""
    return f"Panasonic {familie}{kleurtxt} {vermogen} kW"


def buiten_label(item):
    familie, code, bereik, prijs = item
    prijs_txt = f"{prijs:,.0f}".replace(",", " ")
    return f"Panasonic {familie} {code} ({bereik}) — € {prijs_txt}"


def buiten_naam(item):
    familie, code, bereik, prijs = item
    return f"Panasonic {familie} {code}"


def binnen_label(item):
    familie, kleur, vermogen, prijs = item
    kleurtxt = f" ({kleur})" if kleur else ""
    prijs_txt = f"{prijs:,.0f}".replace(",", " ")
    return f"Panasonic {familie}{kleurtxt} {vermogen} kW — € {prijs_txt}"


def binnen_naam(item):
    familie, kleur, vermogen, prijs = item
    kleurtxt = f" {kleur}" if kleur else ""
    return f"Panasonic {familie}{kleurtxt} {vermogen} kW"
