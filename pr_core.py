# pr_core.py — gedeelde prijzen, berekeningen en PDF voor Solvigo Koeltechnieken
import io
import os
import re
from datetime import date

from fpdf import FPDF

# ================================================================ DEFAULT PRIJZEN
# Alles hier is aanpasbaar via de pagina "Prijsinstellingen" — dit zijn enkel startwaarden.
DEFAULT_PRIJZEN = {
    # Algemeen
    "uurtarief": 55.0,            # verkooptarief per technieker per uur
    "loonkost_intern": 38.0,      # interne kostprijs per uur (voor marge-indicatie)
    "loonkost_meetellen": 0.0,    # 1 = loonkost aftrekken van brutomarge, 0 = niet (bv. als je (nog) solo werkt)
    "marge_materiaal_pct": 25.0,  # % marge op inkoop materiaal
    "km_prijs": 0.75,             # EUR per km (enkel)
    "vast_dossier": 75.0,         # vast opstart-/dossierbedrag per offerte
    "minimum_tarief": 350.0,      # minimum offertebedrag excl. BTW

    # Airco
    "a_leiding_pm": 18.0,         # koelleiding set per meter (geïsoleerd, inkoop)
    "a_goot_pm": 22.0,            # sierlijst per meter (inkoop)
    "a_klein_basis": 60.0,        # klein materiaal basis
    "a_klein_per_unit": 25.0,     # klein materiaal per binnenunit
    "a_koelmiddel_pm": 8.0,       # extra R32 per meter boven voorvulling
    "a_condenspomp": 140.0,
    "a_console": 65.0,
    "a_elek_mat": 85.0,
    "a_hoogtewerker": 250.0,
    "a_uren_basis": 4.0,          # uren mono-split per technieker
    "a_uren_extra_unit": 2.5,     # extra uren per bijkomende binnenunit
    "a_uren_doorvoer": 0.75,      # uren per muurdoorvoer
    "a_uren_elek": 1.5,
    "a_uren_pomp": 0.5,

    # Warmtepomp
    "w_buffer_50": 380.0,
    "w_buffer_100": 520.0,
    "w_buffer_200": 740.0,
    "w_boiler_200": 1100.0,
    "w_boiler_300": 1450.0,
    "w_hydro": 650.0,
    "w_elek_mat": 350.0,
    "w_sokkel": 180.0,
    "w_afvoer_oud": 150.0,
    "w_regeling": 280.0,
    "w_klein": 120.0,
    "w_uren_monoblock": 12.0,
    "w_uren_split": 16.0,
    "w_uren_elek": 4.0,
    "w_uren_afvoer": 3.0,
    "w_uren_regeling": 1.0,
    "w_uren_radiatoren": 2.0,
    "w_uren_gemengd": 3.0,
}

PRIJS_LABELS = {
    "uurtarief": "Uurtarief technieker (verkoop, EUR/u)",
    "loonkost_intern": "Interne loonkost (EUR/u, voor marge-info)",
    "loonkost_meetellen": "Loonkost aftrekken van brutomarge? (checkbox hieronder)",
    "marge_materiaal_pct": "Marge op materiaal (%)",
    "km_prijs": "Kilometerprijs (EUR/km, enkel)",
    "vast_dossier": "Vast dossier-/opstartbedrag (EUR)",
    "minimum_tarief": "Minimumtarief offerte excl. BTW (EUR)",
    "a_leiding_pm": "Airco: koelleiding per meter (EUR, inkoop)",
    "a_goot_pm": "Airco: sierlijst per meter (EUR, inkoop)",
    "a_klein_basis": "Airco: klein materiaal basis (EUR)",
    "a_klein_per_unit": "Airco: klein materiaal per binnenunit (EUR)",
    "a_koelmiddel_pm": "Airco: extra koelmiddel per meter (EUR)",
    "a_condenspomp": "Airco: condenspomp (EUR)",
    "a_console": "Airco: muurconsole + dempers (EUR)",
    "a_elek_mat": "Airco: elektrisch materiaal (EUR)",
    "a_hoogtewerker": "Airco: hoogtewerker vast bedrag (EUR)",
    "a_uren_basis": "Airco: basisuren mono-split (u/technieker)",
    "a_uren_extra_unit": "Airco: extra uren per binnenunit (u)",
    "a_uren_doorvoer": "Airco: uren per muurdoorvoer (u)",
    "a_uren_elek": "Airco: uren elektrische voeding (u)",
    "a_uren_pomp": "Airco: uren condenspomp (u)",
    "w_buffer_50": "WP: buffervat 50 L (EUR)",
    "w_buffer_100": "WP: buffervat 100 L (EUR)",
    "w_buffer_200": "WP: buffervat 200 L (EUR)",
    "w_boiler_200": "WP: SWW-boiler 200 L (EUR)",
    "w_boiler_300": "WP: SWW-boiler 300 L (EUR)",
    "w_hydro": "WP: hydraulisch materiaal (EUR)",
    "w_elek_mat": "WP: elektrisch materiaal & sturing (EUR)",
    "w_sokkel": "WP: sokkel / grondconsole (EUR)",
    "w_afvoer_oud": "WP: afvoer oude installatie (EUR)",
    "w_regeling": "WP: slimme regeling (EUR)",
    "w_klein": "WP: klein materiaal (EUR)",
    "w_uren_monoblock": "WP: basisuren monoblock (u/technieker)",
    "w_uren_split": "WP: basisuren split (u/technieker)",
    "w_uren_elek": "WP: uren elektrisch (u)",
    "w_uren_afvoer": "WP: uren afvoer oude ketel (u)",
    "w_uren_regeling": "WP: uren slimme regeling (u)",
    "w_uren_radiatoren": "WP: extra uren radiatoren (u)",
    "w_uren_gemengd": "WP: extra uren gemengd afgiftesysteem (u)",
}


# ================================================================ BEREKENINGEN
def eenheid_label(aantal_tekst: str) -> str:
    """Leidt een korte eenheid-suffix af uit de aantal-tekst, voor weergave op
    het scherm (bv. '20.0 m' -> '/m', '3 st' -> '/st'). Wordt NIET op de PDF
    gebruikt — daar staat gewoon het bedrag."""
    if not aantal_tekst:
        return ""
    parts = aantal_tekst.strip().split(None, 1)
    if len(parts) < 2:
        return ""
    return f"/{parts[1].strip()}"


def _vk(inkoop: float, verkoop_override: float, marge: float) -> float:
    """Verkoopprijs: gebruik de manueel ingegeven verkoopprijs als die is ingevuld
    (> 0), anders automatisch inkoop x marge%. Zo klopt de marge altijd, ook als
    je zelf een vaste catalogus-/verkoopprijs intikt die niets met de marge% te
    maken heeft (bv. Panasonic-toestellen waar plaatsing al inbegrepen zit)."""
    return verkoop_override if verkoop_override and verkoop_override > 0 else inkoop * marge


def bereken_airco(inp: dict, P: dict) -> dict:
    marge = 1 + P["marge_materiaal_pct"] / 100.0
    n = inp["n_binnen"]                       # binnenunits per systeem
    aantal_systemen = max(1, inp.get("aantal_systemen", 1))  # aantal aparte buitenunits
    n_totaal = n * aantal_systemen             # totaal aantal binnenunits

    mat = []  # (omschrijving, aantal-tekst, inkoop-totaal, verkoop-totaal, eenheidsprijs-verkoop)

    if inp.get("mono_set") and n == 1:
        # Mono-split: 1 aankoopprijs voor het volledige toestel (binnen+buiten samen)
        set_eenheid_verkoop = _vk(inp["prijs_buiten"], inp.get("prijs_buiten_verkoop", 0), marge)
        set_inkoop = inp["prijs_buiten"] * aantal_systemen
        set_verkoop = set_eenheid_verkoop * aantal_systemen
        mat.append((f"Toestel (binnen- + buitenunit) {inp['merk_model']}".strip(), f"{aantal_systemen} st", set_inkoop, set_verkoop, set_eenheid_verkoop))
    else:
        buiten_eenheid_verkoop = _vk(inp["prijs_buiten"], inp.get("prijs_buiten_verkoop", 0), marge)
        buiten_inkoop = inp["prijs_buiten"] * aantal_systemen
        buiten_verkoop = buiten_eenheid_verkoop * aantal_systemen
        binnen_eenheid_verkoop = _vk(inp["prijs_binnen"], inp.get("prijs_binnen_verkoop", 0), marge)
        binnen_inkoop = inp["prijs_binnen"] * n_totaal
        binnen_verkoop = binnen_eenheid_verkoop * n_totaal
        mat.append((f"Buitenunit {inp['merk_model']}".strip(), f"{aantal_systemen} st", buiten_inkoop, buiten_verkoop, buiten_eenheid_verkoop))
        mat.append((f"Binnenunit(s)", f"{n_totaal} st", binnen_inkoop, binnen_verkoop, binnen_eenheid_verkoop))

    def std(om, aantal, inkoop_totaal, aantal_num=1):
        verkoop_totaal = inkoop_totaal * marge
        eenheid = verkoop_totaal / aantal_num if aantal_num else verkoop_totaal
        mat.append((om, aantal, inkoop_totaal, verkoop_totaal, eenheid))

    std("Koelleidingen (geïsoleerd)", f"{inp['leiding_m']} m", inp["leiding_m"] * P["a_leiding_pm"], aantal_num=inp["leiding_m"] or 1)
    if inp["goot_m"] > 0:
        std("Sierlijst / leidinggoot", f"{inp['goot_m']} m", inp["goot_m"] * P["a_goot_pm"], aantal_num=inp["goot_m"])
    std("Klein materiaal & bevestiging", "", P["a_klein_basis"] * aantal_systemen + n_totaal * P["a_klein_per_unit"])
    if inp["koelmiddel_m"] > 0:
        std("Extra koelmiddel R32", f"{inp['koelmiddel_m']} m", inp["koelmiddel_m"] * P["a_koelmiddel_pm"], aantal_num=inp["koelmiddel_m"])
    if inp["condenspomp"]:
        std("Condenspomp", f"{n_totaal} st" if n_totaal > 1 else "1 st", P["a_condenspomp"] * n_totaal, aantal_num=n_totaal)
    if inp["console"]:
        std("Muurconsole + trillingsdempers", f"{aantal_systemen} st", P["a_console"] * aantal_systemen, aantal_num=aantal_systemen)
    if inp["elek"]:
        std("Elektrisch materiaal", f"{aantal_systemen} circuit(s)", P["a_elek_mat"] * aantal_systemen, aantal_num=aantal_systemen)

    mat_inkoop = sum(m[2] for m in mat)
    mat_verkoop = sum(m[3] for m in mat)

    # Uren per systeem (incl. eventuele extra binnenunits binnen dat systeem),
    # daarna vermenigvuldigd met het aantal aparte systemen — want elk apart
    # systeem heeft z'n eigen buitenunit-plaatsing nodig, dat is geen "gratis" extra.
    uren_per_systeem = (
        P["a_uren_basis"]
        + (n - 1) * P["a_uren_extra_unit"]
        + (P["a_uren_elek"] if inp["elek"] else 0)
        + (P["a_uren_pomp"] if inp["condenspomp"] else 0)
    )
    uren_auto = uren_per_systeem * aantal_systemen + inp["doorvoeren"] * P["a_uren_doorvoer"]
    uren = inp["uren_manueel"] if inp["uren_manueel"] > 0 else uren_auto
    arbeid_aanrekenen = inp.get("arbeid_aanrekenen", True)
    arbeid = (uren * inp["techniekers"] * P["uurtarief"]) if arbeid_aanrekenen else 0.0

    km_kost = inp["km"] * P["km_prijs"] * 2
    extra = P["a_hoogtewerker"] if inp["hoogtewerker"] else 0.0
    dossier_aanrekenen = inp.get("dossier_aanrekenen", True)
    vast = P["vast_dossier"] if dossier_aanrekenen else 0.0

    subtotaal = mat_verkoop + arbeid + km_kost + vast + extra
    subtotaal = max(subtotaal, P["minimum_tarief"])
    btw = subtotaal * inp["btw"]
    totaal = subtotaal + btw

    loonkost = uren * inp["techniekers"] * P["loonkost_intern"] * P.get("loonkost_meetellen", 1.0)
    winst = subtotaal - mat_inkoop - loonkost - km_kost * 0.6

    return {
        "mat": mat, "mat_inkoop": mat_inkoop, "mat_verkoop": mat_verkoop,
        "uren": uren, "uren_auto": uren_auto, "arbeid": arbeid,
        "arbeid_aanrekenen": arbeid_aanrekenen,
        "km_kost": km_kost, "vast": vast, "dossier_aanrekenen": dossier_aanrekenen, "extra_hoogte": extra,
        "subtotaal": subtotaal, "btw_bedrag": btw, "totaal": totaal, "winst": winst,
        "marge": marge,
    }


def bereken_wp(inp: dict, P: dict) -> dict:
    marge = 1 + P["marge_materiaal_pct"] / 100.0

    wp_inkoop = inp["prijs_wp"]
    wp_verkoop = _vk(wp_inkoop, inp.get("prijs_wp_verkoop", 0), marge)

    mat = [(f"Warmtepomp {inp['kw']} kW {inp['type']} {inp['merk_model']}".strip(), "1 st", wp_inkoop, wp_verkoop, wp_verkoop)]

    def std(om, aantal, inkoop, aantal_num=1):
        verkoop_totaal = inkoop * marge
        eenheid = verkoop_totaal / aantal_num if aantal_num else verkoop_totaal
        mat.append((om, aantal, inkoop, verkoop_totaal, eenheid))

    if inp["buffer"] == 50:
        std("Buffervat 50 L", "1 st", P["w_buffer_50"])
    elif inp["buffer"] == 100:
        std("Buffervat 100 L", "1 st", P["w_buffer_100"])
    elif inp["buffer"] == 200:
        std("Buffervat 200 L", "1 st", P["w_buffer_200"])
    if inp["boiler"] == 200:
        std("Sanitair warmwaterboiler 200 L", "1 st", P["w_boiler_200"])
    elif inp["boiler"] == 300:
        std("Sanitair warmwaterboiler 300 L", "1 st", P["w_boiler_300"])
    if inp["hydro"]:
        std("Hydraulisch materiaal (leidingen, kranen, expansievat)", "", P["w_hydro"])
    if inp["elek"]:
        std("Elektrisch materiaal & sturing", "", P["w_elek_mat"])
    if inp["sokkel"]:
        std("Sokkel / grondconsole buitenunit", "1 st", P["w_sokkel"])
    if inp["afvoer_oud"]:
        std("Afbraak & afvoer oude installatie", "", P["w_afvoer_oud"])
    if inp["regeling"]:
        std("Slimme thermostaat / weersafhankelijke regeling", "1 st", P["w_regeling"])
    std("Klein materiaal & verbruiksgoederen", "", P["w_klein"])

    mat_inkoop = sum(m[2] for m in mat)
    mat_verkoop = sum(m[3] for m in mat)

    uren_auto = P["w_uren_monoblock"] if inp["type"] == "monoblock" else P["w_uren_split"]
    if inp["elek"]:
        uren_auto += P["w_uren_elek"]
    if inp["afvoer_oud"]:
        uren_auto += P["w_uren_afvoer"]
    if inp["regeling"]:
        uren_auto += P["w_uren_regeling"]
    if inp["afgifte"] == "Radiatoren":
        uren_auto += P["w_uren_radiatoren"]
    elif inp["afgifte"] == "Gemengd":
        uren_auto += P["w_uren_gemengd"]

    uren = inp["uren_manueel"] if inp["uren_manueel"] > 0 else uren_auto
    arbeid_aanrekenen = inp.get("arbeid_aanrekenen", True)
    arbeid = (uren * inp["techniekers"] * P["uurtarief"]) if arbeid_aanrekenen else 0.0
    km_kost = inp["km"] * P["km_prijs"] * 2
    dossier_aanrekenen = inp.get("dossier_aanrekenen", True)
    vast = P["vast_dossier"] if dossier_aanrekenen else 0.0

    subtotaal = mat_verkoop + arbeid + km_kost + vast
    subtotaal = max(subtotaal, P["minimum_tarief"])
    btw = subtotaal * inp["btw"]
    totaal = subtotaal + btw

    loonkost = uren * inp["techniekers"] * P["loonkost_intern"] * P.get("loonkost_meetellen", 1.0)
    winst = subtotaal - mat_inkoop - loonkost - km_kost * 0.6

    return {
        "mat": mat, "mat_inkoop": mat_inkoop, "mat_verkoop": mat_verkoop,
        "uren": uren, "uren_auto": uren_auto, "arbeid": arbeid,
        "arbeid_aanrekenen": arbeid_aanrekenen,
        "km_kost": km_kost, "vast": vast, "dossier_aanrekenen": dossier_aanrekenen, "extra_hoogte": 0.0,
        "subtotaal": subtotaal, "btw_bedrag": btw, "totaal": totaal, "winst": winst,
        "marge": marge,
    }


# ================================================================ PDF
NAVY = (17, 50, 211)      # Solvigo-blauw (uit logo)
ORANGE = (196, 144, 0)    # Goud/geel-accent, verduisterd voor leesbaarheid op wit
GREY = (245, 246, 250)

# Tekens die de standaard Helvetica/latin-1 encoding niet aankan (crasht anders de PDF)
_PDF_REPLACEMENTS = {
    "\u2014": "-", "\u2013": "-",      # em-dash, en-dash
    "\u2018": "'", "\u2019": "'",      # curly quotes
    "\u201c": '"', "\u201d": '"',
    "\u2026": "...",
}


def _safe(text, use_uni: bool) -> str:
    """Maakt tekst veilig voor de PDF-font: vervangt bekende speciale tekens,
    en vangt al de rest op zodat de app nooit crasht op een onverwacht teken."""
    if text is None:
        return ""
    text = str(text)
    if use_uni:
        return text
    for k, v in _PDF_REPLACEMENTS.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")

BEDRIJFSINFO = [
    "Solvigo BV",
    "Baksveld 38, 2260 Westerlo",
    "Tel.: 0471 42 56 69",
    "BTW: BE 0677.778.392",
    "IBAN: BE59 0018 1682 5558",
    "www.solvigo.be",              # TODO: aanpassen naar definitief website-adres (koeltechnieken)
    "cleaning@solvigo.be",         # TODO: aanpassen naar definitief e-mailadres (koeltechnieken)
]

# ---------------------------------------------------------------- ALGEMENE VOORWAARDEN
# Pas gerust aan — dit is een degelijke basis voor een Belgische HVAC-installateur,
# maar laat ze idealiter nog eens nalezen door je boekhouder of een jurist vóór
# je ze structureel gebruikt. LET OP: art. 11 (bevoegde rechtbank) invullen!
ALGEMENE_VOORWAARDEN = [
    ("Art. 1 — Toepassing",
     "Deze algemene voorwaarden zijn van toepassing op alle offertes, overeenkomsten, leveringen en werken van "
     "Solvigo Koeltechnieken (hierna 'de installateur'). Afwijkingen zijn enkel geldig indien schriftelijk overeengekomen. "
     "De voorwaarden van de klant zijn niet tegenstelbaar aan de installateur, tenzij uitdrukkelijk schriftelijk aanvaard."),

    ("Art. 2 — Offertes en prijzen",
     "Offertes zijn geldig tot de vermelde vervaldatum en zijn opgemaakt op basis van de door de klant verstrekte "
     "informatie. Alle prijzen zijn exclusief BTW tenzij anders vermeld. De installateur behoudt zich het recht voor "
     "prijzen aan te passen indien de kostprijs van materialen tussen offerte en uitvoering aantoonbaar stijgt met "
     "meer dan 5%, en dit beperkt tot het gedeelte van de prijs dat betrekking heeft op die materialen. Kennelijke "
     "vergissingen of schrijffouten in de offerte binden de installateur niet."),

    ("Art. 3 — BTW-tarief",
     "Bij toepassing van het verlaagd BTW-tarief van 6% verklaart de klant dat de woning ouder is dan 10 jaar, "
     "hoofdzakelijk als privéwoning wordt gebruikt en dat de werken worden geleverd en gefactureerd aan de "
     "eindgebruiker. De klant is als enige aansprakelijk voor de juistheid van deze verklaring en vrijwaart de "
     "installateur voor elke naheffing, boete of interest die uit een onjuiste verklaring voortvloeit."),

    ("Art. 4 — Uitvoering en toegang tot de werf",
     "Uitvoeringstermijnen zijn indicatief en binden de installateur niet, behoudens uitdrukkelijk anders "
     "overeengekomen. Vertraging geeft geen recht op schadevergoeding of ontbinding. De klant zorgt voor vrije en "
     "veilige toegang tot de werf, een werkende elektrische aansluiting en de nodige nutsvoorzieningen. Wachttijden "
     "of nutteloze verplaatsingen te wijten aan de klant kunnen in regie worden aangerekend."),

    ("Art. 5 — Meerwerken en onvoorziene omstandigheden",
     "Werken die niet in de offerte zijn opgenomen (o.a. asbestverwijdering, ontoegankelijke leidingtraces, extra "
     "doorboringen, aanpassingen aan de elektrische installatie, grondwerken) zijn meerwerken. Meerwerken worden "
     "slechts uitgevoerd na overleg met de klant en worden aangerekend in regie of volgens afzonderlijke prijsopgave."),

    ("Art. 6 — Betaling",
     "Behoudens andersluidende vermelding zijn facturen betaalbaar binnen 14 kalenderdagen na factuurdatum. De "
     "installateur kan een voorschot vragen vóór bestelling van de toestellen. Bij niet-betaling op de vervaldag is "
     "van rechtswege en zonder ingebrekestelling een verwijlintrest verschuldigd conform de wet van 2 augustus 2002 "
     "betreffende de bestrijding van de betalingsachterstand, evenals een forfaitaire schadevergoeding van 10% van "
     "het factuurbedrag met een minimum van 125 EUR. Bij consumenten gelden de wettelijke regels inzake eerste "
     "kosteloze herinnering en maximale vergoedingen (Boek XIX WER)."),

    ("Art. 7 — Eigendomsvoorbehoud",
     "Geleverde toestellen en materialen blijven eigendom van de installateur tot volledige betaling van de "
     "hoofdsom, kosten en interesten. Het risico gaat evenwel over op de klant vanaf de levering op de werf."),

    ("Art. 8 — Garantie",
     "Op toestellen geldt de fabrieksgarantie volgens de voorwaarden van de fabrikant. Voor consumenten geldt "
     "daarnaast de wettelijke garantie van 2 jaar op consumptiegoederen. Op de uitgevoerde installatiewerken "
     "verleent de installateur een waarborg van 2 jaar op verborgen gebreken in de uitvoering. De garantie vervalt "
     "bij foutief gebruik, gebrekkig onderhoud, ingrepen door derden, bevriezing, over- of onderspanning op het "
     "elektriciteitsnet of externe oorzaken. Periodiek onderhoud volgens de voorschriften van de fabrikant is een "
     "voorwaarde voor het behoud van de garantie."),

    ("Art. 9 — Aansprakelijkheid",
     "De aansprakelijkheid van de installateur is beperkt tot de directe schade die het rechtstreeks gevolg is van "
     "een bewezen fout in de uitvoering, en tot maximaal het bedrag van de betreffende overeenkomst. De installateur "
     "is niet aansprakelijk voor indirecte schade zoals gebruiksderving, productieverlies of gevolgschade, behoudens "
     "in geval van opzet of zware fout. Deze beperkingen doen geen afbreuk aan de wettelijke rechten van consumenten."),

    ("Art. 10 — Annulering en klachten",
     "Bij annulering van de overeenkomst door de klant vóór aanvang van de werken is een forfaitaire vergoeding "
     "verschuldigd van 15% van het offertebedrag, verhoogd met de kosten van reeds bestelde of geleverde materialen "
     "die niet kosteloos geretourneerd kunnen worden. Zichtbare gebreken dienen op straffe van verval gemeld te "
     "worden binnen 8 kalenderdagen na oplevering; verborgen gebreken binnen 2 maanden na ontdekking, telkens per "
     "aangetekend schrijven of e-mail met ontvangstbevestiging."),

    ("Art. 11 — Toepasselijk recht en bevoegde rechtbank",
     "Op alle overeenkomsten is uitsluitend het Belgisch recht van toepassing. Geschillen behoren tot de uitsluitende "
     "bevoegdheid van de rechtbanken van het gerechtelijk arrondissement van de maatschappelijke zetel van de "
     "installateur, onverminderd dwingende bevoegdheidsregels ten aanzien van consumenten."),
]


def gen_offertenummer(klantnaam: str, d: date) -> str:
    base = re.sub(r"[^A-Za-z0-9]", "", (klantnaam or "").upper())
    tag = base[:5] if base else "CLIENT"
    return f"SLV-{d:%Y%m%d}-{tag}"


def maak_pdf(titel: str, klant: dict, res: dict, inp: dict, intro: str) -> bytes:
    pdf = FPDF()
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    use_uni = False
    try:
        if os.path.exists("DejaVuSans.ttf"):
            pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
            pdf.add_font("DejaVu", "B", "DejaVuSans.ttf", uni=True)
            use_uni = True
    except Exception:
        pass
    F = "DejaVu" if use_uni else "Helvetica"
    S = lambda t: _safe(t, use_uni)

    # --- Header: logo, rustige tagline, dunne scheidingslijn ---
    logo_ok = False
    for lp in ("assets/logo.png", "Logo.png", "logo.png"):
        if os.path.exists(lp):
            try:
                pdf.image(lp, x=12, y=8, h=22)
                logo_ok = True
                break
            except Exception:
                pass
    if not logo_ok:
        pdf.set_text_color(*NAVY)
        pdf.set_font(F, "B", 16)
        pdf.set_xy(12, 10)
        pdf.cell(0, 8, "SOLVIGO KOELTECHNIEKEN")
    pdf.set_font(F, "", 8)
    pdf.set_text_color(140, 140, 140)
    pdf.set_xy(12 if not logo_ok else 65, 17)
    pdf.cell(0, 5, "AIRCO   ·   WARMTEPOMPEN   ·   KOELTECHNIEK")
    pdf.set_draw_color(224, 226, 231)
    pdf.set_line_width(0.3)
    pdf.line(12, 34, 198, 34)

    # --- Titel + offertedetails links, bedrijfsinfo rechts ---
    pdf.set_text_color(*NAVY)
    pdf.set_xy(12, 40)
    pdf.set_font(F, "B", 18)
    pdf.cell(0, 9, "Offerte", ln=1)
    pdf.set_font(F, "", 10.5)
    pdf.set_text_color(90, 90, 90)
    pdf.set_x(12)
    pdf.cell(0, 6, S(titel), ln=1)

    pdf.set_text_color(90, 90, 90)
    pdf.set_font(F, "", 8.5)
    y0 = pdf.get_y() + 3
    details = [
        f"Offertenummer: {klant['nummer']}",
        f"Offertedatum: {klant['datum']:%d-%m-%Y}",
        f"Geldig tot: {klant['verloop']:%d-%m-%Y}",
        f"BTW-tarief: {int(inp['btw']*100)}%",
    ]
    for i, d in enumerate(details):
        pdf.set_xy(12, y0 + i * 4.6)
        pdf.cell(90, 4.6, S(d))
    for i, lijn in enumerate(BEDRIJFSINFO):
        pdf.set_xy(130, y0 + i * 4.6)
        pdf.cell(0, 4.6, S(lijn))

    # --- Klant ---
    pdf.set_y(y0 + max(len(details), len(BEDRIJFSINFO)) * 4.6 + 7)
    pdf.set_font(F, "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 6, "KLANT", ln=1)
    pdf.set_font(F, "", 10)
    pdf.set_text_color(40, 40, 40)
    for veld in ("bedrijf", "naam"):
        if klant.get(veld, "").strip():
            pdf.cell(0, 5, S(klant[veld]), ln=1)
    for regel in klant.get("adres", "").split("\n"):
        if regel.strip():
            pdf.cell(0, 5, S(regel), ln=1)
    for veld, prefix in (("email", "E-mail: "), ("tel", "Tel.: ")):
        if klant.get(veld, "").strip():
            pdf.cell(0, 5, S(prefix + klant[veld]), ln=1)

    # --- Intro ---
    pdf.ln(4)
    pdf.set_font(F, "", 9)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(0, 5, S(intro))
    pdf.ln(5)

    # --- Kostentabel: rustige lijnenstijl (geen volledig grid, geen felle vlakken) ---
    pdf.set_font(F, "B", 9)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 6, "OVERZICHT", ln=1)
    pdf.ln(1)

    pdf.set_font(F, "B", 8.5)
    pdf.set_text_color(120, 120, 120)
    pdf.set_draw_color(*NAVY)
    pdf.set_line_width(0.4)
    pdf.cell(110, 7, "OMSCHRIJVING")
    pdf.cell(35, 7, "AANTAL", align="C")
    pdf.cell(41, 7, "TOTAAL (EUR)", align="R")
    pdf.ln(7)
    pdf.set_x(12)
    pdf.line(12, pdf.get_y(), 198, pdf.get_y())
    pdf.ln(1.5)

    pdf.set_font(F, "", 9.5)
    pdf.set_text_color(50, 50, 50)
    pdf.set_draw_color(230, 232, 236)
    pdf.set_line_width(0.2)
    idx = 0
    def row(om, aantal, bedrag):
        nonlocal idx
        if idx % 2 == 1:
            pdf.set_fill_color(*GREY)
            pdf.rect(12, pdf.get_y(), 186, 7, "F")
        pdf.cell(110, 7, S(om)[:68])
        pdf.cell(35, 7, S(aantal), align="C")
        pdf.cell(41, 7, f"{bedrag:,.2f}".replace(",", " "), align="R")
        pdf.ln(7)
        pdf.set_x(12)
        pdf.line(12, pdf.get_y(), 198, pdf.get_y())
        idx += 1

    for om, aantal, inkoop, verkoop, eenheid in res["mat"]:
        row(om, aantal, verkoop)

    if res.get("arbeid_aanrekenen", True):
        row(f"Installatie & indienststelling ({res['uren']:.1f} u x {inp['techniekers']} technieker(s))", "", res["arbeid"])
    # indien arbeid niet apart aangerekend wordt: geen regel op de offerte

    if res["km_kost"] > 0:
        row("Verplaatsing", f"{inp['km']} km", res["km_kost"])
    if res.get("dossier_aanrekenen", True):
        row("Dossier & opstart", "", res["vast"])
    if res["extra_hoogte"] > 0:
        row("Hoogtewerker / moeilijke toegang", "", res["extra_hoogte"])

    # --- Totalen ---
    pdf.ln(3)
    def tot_row(label, bedrag, bold=False, groot=False):
        pdf.set_font(F, "B" if bold else "", 12 if groot else 9.5)
        pdf.set_text_color(*NAVY if bold else (90, 90, 90))
        pdf.cell(145, 7 if not groot else 9, S(label), align="R")
        pdf.cell(41, 7 if not groot else 9, f"EUR {bedrag:,.2f}".replace(",", " "), align="R", ln=1)

    tot_row("Subtotaal excl. BTW", res["subtotaal"])
    tot_row(f"BTW {int(inp['btw']*100)}%", res["btw_bedrag"])
    pdf.set_draw_color(*NAVY)
    pdf.set_line_width(0.4)
    pdf.line(145, pdf.get_y() + 1, 198, pdf.get_y() + 1)
    pdf.ln(2.5)
    tot_row("Totaal incl. BTW", res["totaal"], bold=True, groot=True)

    # --- Verwijzing naar algemene voorwaarden ---
    pdf.ln(5)
    pdf.set_font(F, "", 8)
    pdf.set_text_color(140, 140, 140)
    pdf.multi_cell(0, 4.5, S(
        "Op deze offerte zijn onze algemene voorwaarden van toepassing (zie volgende pagina). "
        "Door ondertekening of schriftelijke aanvaarding van deze offerte verklaart de klant "
        "hiervan kennis te hebben genomen en deze te aanvaarden."))

    # --- Handtekeningvakken ---
    pdf.ln(9)
    pdf.set_draw_color(224, 226, 231)
    pdf.set_line_width(0.3)
    y_box = pdf.get_y()
    pdf.line(12, y_box + 16, 90, y_box + 16)
    pdf.line(120, y_box + 16, 198, y_box + 16)
    pdf.set_font(F, "", 9)
    pdf.set_text_color(90, 90, 90)
    pdf.set_xy(12, y_box + 18)
    pdf.cell(78, 5, "Voor akkoord, de klant")
    pdf.set_xy(120, y_box + 18)
    pdf.cell(0, 5, "Solvigo Koeltechnieken")
    pdf.set_font(F, "", 7.5)
    pdf.set_text_color(150, 150, 150)
    pdf.set_xy(12, y_box + 23)
    pdf.cell(78, 4, "(datum + handtekening, voorafgegaan door 'gelezen en goedgekeurd')")

    # ================= PAGINA 2: ALGEMENE VOORWAARDEN =================
    pdf.add_page()
    pdf.set_font(F, "B", 14)
    pdf.set_text_color(*NAVY)
    pdf.set_xy(12, 14)
    pdf.cell(0, 8, "Algemene voorwaarden")
    pdf.set_font(F, "", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.set_xy(140, 16)
    pdf.cell(58, 5, "SOLVIGO KOELTECHNIEKEN", align="R")
    pdf.set_draw_color(224, 226, 231)
    pdf.set_line_width(0.3)
    pdf.line(12, 24, 198, 24)

    # Cursor expliciet terug naar de linkermarge zetten (x én y) — de cellen
    # hierboven gebruiken een vaste breedte, maar dit is de vangnet-fix zodat
    # de tekst hierna altijd over de volledige paginabreedte kan starten.
    pdf.set_xy(12, 32)
    for titel_art, tekst_art in ALGEMENE_VOORWAARDEN:
        pdf.set_x(12)
        pdf.set_font(F, "B", 8.5)
        pdf.set_text_color(*NAVY)
        pdf.multi_cell(0, 4.2, S(titel_art))
        pdf.set_x(12)
        pdf.set_font(F, "", 7.8)
        pdf.set_text_color(60, 60, 60)
        pdf.multi_cell(0, 3.9, S(tekst_art))
        pdf.ln(1.5)
        pdf.set_x(12)

    out = pdf.output(dest="S")
    return bytes(out) if isinstance(out, (bytes, bytearray)) else out.encode("latin-1")
