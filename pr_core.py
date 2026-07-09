# pr_core.py — gedeelde prijzen, berekeningen en PDF voor P&R Koeltechnieken
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
def bereken_airco(inp: dict, P: dict) -> dict:
    marge = 1 + P["marge_materiaal_pct"] / 100.0
    n = inp["n_binnen"]

    mat = []  # (omschrijving, aantal-tekst, inkoop)
    mat.append((f"Buitenunit {inp['merk_model']}".strip(), "1 st", inp["prijs_buiten"]))
    mat.append((f"Binnenunit(s)", f"{n} st", inp["prijs_binnen"] * n))
    mat.append(("Koelleidingen (geïsoleerd)", f"{inp['leiding_m']} m", inp["leiding_m"] * P["a_leiding_pm"]))
    if inp["goot_m"] > 0:
        mat.append(("Sierlijst / leidinggoot", f"{inp['goot_m']} m", inp["goot_m"] * P["a_goot_pm"]))
    mat.append(("Klein materiaal & bevestiging", "", P["a_klein_basis"] + n * P["a_klein_per_unit"]))
    if inp["koelmiddel_m"] > 0:
        mat.append(("Extra koelmiddel R32", f"{inp['koelmiddel_m']} m", inp["koelmiddel_m"] * P["a_koelmiddel_pm"]))
    if inp["condenspomp"]:
        mat.append(("Condenspomp", "1 st", P["a_condenspomp"]))
    if inp["console"]:
        mat.append(("Muurconsole + trillingsdempers", "1 st", P["a_console"]))
    if inp["elek"]:
        mat.append(("Elektrisch materiaal", "", P["a_elek_mat"]))

    mat_inkoop = sum(m[2] for m in mat)
    mat_verkoop = mat_inkoop * marge

    uren_auto = (
        P["a_uren_basis"]
        + (n - 1) * P["a_uren_extra_unit"]
        + inp["doorvoeren"] * P["a_uren_doorvoer"]
        + (P["a_uren_elek"] if inp["elek"] else 0)
        + (P["a_uren_pomp"] if inp["condenspomp"] else 0)
    )
    uren = inp["uren_manueel"] if inp["uren_manueel"] > 0 else uren_auto
    arbeid = uren * inp["techniekers"] * P["uurtarief"]

    km_kost = inp["km"] * P["km_prijs"] * 2
    extra = P["a_hoogtewerker"] if inp["hoogtewerker"] else 0.0

    subtotaal = mat_verkoop + arbeid + km_kost + P["vast_dossier"] + extra
    subtotaal = max(subtotaal, P["minimum_tarief"])
    btw = subtotaal * inp["btw"]
    totaal = subtotaal + btw

    loonkost = uren * inp["techniekers"] * P["loonkost_intern"]
    winst = subtotaal - mat_inkoop - loonkost - km_kost * 0.6

    return {
        "mat": mat, "mat_inkoop": mat_inkoop, "mat_verkoop": mat_verkoop,
        "uren": uren, "uren_auto": uren_auto, "arbeid": arbeid,
        "km_kost": km_kost, "vast": P["vast_dossier"], "extra_hoogte": extra,
        "subtotaal": subtotaal, "btw_bedrag": btw, "totaal": totaal, "winst": winst,
        "marge": marge,
    }


def bereken_wp(inp: dict, P: dict) -> dict:
    marge = 1 + P["marge_materiaal_pct"] / 100.0

    mat = [(f"Warmtepomp {inp['kw']} kW {inp['type']} {inp['merk_model']}".strip(), "1 st", inp["prijs_wp"])]
    if inp["buffer"] == 50:
        mat.append(("Buffervat 50 L", "1 st", P["w_buffer_50"]))
    elif inp["buffer"] == 100:
        mat.append(("Buffervat 100 L", "1 st", P["w_buffer_100"]))
    elif inp["buffer"] == 200:
        mat.append(("Buffervat 200 L", "1 st", P["w_buffer_200"]))
    if inp["boiler"] == 200:
        mat.append(("Sanitair warmwaterboiler 200 L", "1 st", P["w_boiler_200"]))
    elif inp["boiler"] == 300:
        mat.append(("Sanitair warmwaterboiler 300 L", "1 st", P["w_boiler_300"]))
    if inp["hydro"]:
        mat.append(("Hydraulisch materiaal (leidingen, kranen, expansievat)", "", P["w_hydro"]))
    if inp["elek"]:
        mat.append(("Elektrisch materiaal & sturing", "", P["w_elek_mat"]))
    if inp["sokkel"]:
        mat.append(("Sokkel / grondconsole buitenunit", "1 st", P["w_sokkel"]))
    if inp["afvoer_oud"]:
        mat.append(("Afbraak & afvoer oude installatie", "", P["w_afvoer_oud"]))
    if inp["regeling"]:
        mat.append(("Slimme thermostaat / weersafhankelijke regeling", "1 st", P["w_regeling"]))
    mat.append(("Klein materiaal & verbruiksgoederen", "", P["w_klein"]))

    mat_inkoop = sum(m[2] for m in mat)
    mat_verkoop = mat_inkoop * marge

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
    arbeid = uren * inp["techniekers"] * P["uurtarief"]
    km_kost = inp["km"] * P["km_prijs"] * 2

    subtotaal = mat_verkoop + arbeid + km_kost + P["vast_dossier"]
    subtotaal = max(subtotaal, P["minimum_tarief"])
    btw = subtotaal * inp["btw"]
    totaal = subtotaal + btw

    loonkost = uren * inp["techniekers"] * P["loonkost_intern"]
    winst = subtotaal - mat_inkoop - loonkost - km_kost * 0.6

    return {
        "mat": mat, "mat_inkoop": mat_inkoop, "mat_verkoop": mat_verkoop,
        "uren": uren, "uren_auto": uren_auto, "arbeid": arbeid,
        "km_kost": km_kost, "vast": P["vast_dossier"], "extra_hoogte": 0.0,
        "subtotaal": subtotaal, "btw_bedrag": btw, "totaal": totaal, "winst": winst,
        "marge": marge,
    }


# ================================================================ PDF
NAVY = (14, 42, 71)
ORANGE = (242, 140, 40)
GREY = (244, 246, 248)

BEDRIJFSINFO = [
    "P&R Koeltechnieken",
    "Westerlo",                    # TODO: volledig adres invullen
    "Tel.: 0471 42 56 69",         # TODO: aanpassen
    "BTW-nr: BE 0XXX.XXX.XXX",     # TODO: invullen
    "IBAN: BE00 0000 0000 0000",   # TODO: invullen
    "info@prkoeltechnieken.be",    # TODO: aanpassen
]


def gen_offertenummer(klantnaam: str, d: date) -> str:
    base = re.sub(r"[^A-Za-z0-9]", "", (klantnaam or "").upper())
    tag = base[:5] if base else "CLIENT"
    return f"PR-{d:%Y%m%d}-{tag}"


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

    # --- Navy header-balk ---
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 210, 30, "F")
    logo_ok = False
    for lp in ("assets/logo.png", "Logo.png", "logo.png"):
        if os.path.exists(lp):
            try:
                pdf.image(lp, x=12, y=5, h=20)
                logo_ok = True
                break
            except Exception:
                pass
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(F, "B", 18)
    pdf.set_xy(12 if not logo_ok else 45, 8)
    pdf.cell(0, 8, "P&R KOELTECHNIEKEN")
    pdf.set_font(F, "", 9)
    pdf.set_xy(12 if not logo_ok else 45, 17)
    pdf.set_text_color(*ORANGE)
    pdf.cell(0, 5, "AIRCO  ·  WARMTEPOMPEN  ·  KOELTECHNIEK")

    # --- Titel + offertedetails links, bedrijfsinfo rechts ---
    pdf.set_text_color(*NAVY)
    pdf.set_xy(12, 38)
    pdf.set_font(F, "B", 20)
    pdf.cell(0, 10, "Offerte", ln=1)
    pdf.set_font(F, "B", 12)
    pdf.set_text_color(*ORANGE)
    pdf.cell(0, 7, titel, ln=1)

    pdf.set_text_color(60, 60, 60)
    pdf.set_font(F, "", 9)
    y0 = pdf.get_y() + 2
    details = [
        f"Offertenummer: {klant['nummer']}",
        f"Offertedatum: {klant['datum']:%d-%m-%Y}",
        f"Geldig tot: {klant['verloop']:%d-%m-%Y}",
        f"BTW-tarief: {int(inp['btw']*100)}%",
    ]
    for i, d in enumerate(details):
        pdf.set_xy(12, y0 + i * 5)
        pdf.cell(90, 5, d)
    for i, lijn in enumerate(BEDRIJFSINFO):
        pdf.set_xy(130, y0 + i * 5)
        pdf.cell(0, 5, lijn)

    # --- Klant ---
    pdf.set_y(y0 + max(len(details), len(BEDRIJFSINFO)) * 5 + 6)
    pdf.set_font(F, "B", 11)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, "Klant", ln=1)
    pdf.set_font(F, "", 10)
    pdf.set_text_color(40, 40, 40)
    for veld in ("bedrijf", "naam"):
        if klant.get(veld, "").strip():
            pdf.cell(0, 5, klant[veld], ln=1)
    for regel in klant.get("adres", "").split("\n"):
        if regel.strip():
            pdf.cell(0, 5, regel, ln=1)
    for veld, prefix in (("email", "E-mail: "), ("tel", "Tel.: ")):
        if klant.get(veld, "").strip():
            pdf.cell(0, 5, prefix + klant[veld], ln=1)

    # --- Intro ---
    pdf.ln(4)
    pdf.set_font(F, "", 9)
    pdf.set_text_color(60, 60, 60)
    pdf.multi_cell(0, 5, intro)
    pdf.ln(4)

    # --- Kostentabel ---
    pdf.set_font(F, "B", 11)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 7, "Overzicht", ln=1)

    pdf.set_font(F, "B", 9)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_draw_color(200, 205, 212)
    pdf.cell(110, 8, "Omschrijving", border=1, fill=True)
    pdf.cell(35, 8, "Aantal", border=1, align="C", fill=True)
    pdf.cell(41, 8, "Totaal (EUR)", border=1, align="R", fill=True)
    pdf.ln(8)

    pdf.set_font(F, "", 9)
    pdf.set_text_color(40, 40, 40)
    fill = False
    def row(om, aantal, bedrag):
        nonlocal fill
        pdf.set_fill_color(*(GREY if fill else (255, 255, 255)))
        pdf.cell(110, 7, om[:68], border=1, fill=True)
        pdf.cell(35, 7, aantal, border=1, align="C", fill=True)
        pdf.cell(41, 7, f"{bedrag:,.2f}".replace(",", " "), border=1, align="R", fill=True)
        pdf.ln(7)
        fill = not fill

    for om, aantal, inkoop in res["mat"]:
        row(om, aantal, inkoop * res["marge"])
    row(f"Installatie & indienststelling ({res['uren']:.1f} u x {inp['techniekers']} technieker(s))", "", res["arbeid"])
    if res["km_kost"] > 0:
        row("Verplaatsing", f"{inp['km']} km", res["km_kost"])
    row("Dossier & opstart", "", res["vast"])
    if res["extra_hoogte"] > 0:
        row("Hoogtewerker / moeilijke toegang", "", res["extra_hoogte"])

    # --- Totalen ---
    pdf.ln(3)
    def tot_row(label, bedrag, bold=False, orange=False):
        pdf.set_font(F, "B" if bold else "", 10 if not bold else 11)
        pdf.set_text_color(*(ORANGE if orange else NAVY))
        pdf.cell(145, 7, label, align="R")
        pdf.cell(41, 7, f"EUR {bedrag:,.2f}".replace(",", " "), align="R", ln=1)

    tot_row("Subtotaal excl. BTW", res["subtotaal"])
    tot_row(f"BTW {int(inp['btw']*100)}%", res["btw_bedrag"])
    tot_row("Totaal incl. BTW", res["totaal"], bold=True, orange=True)

    # --- Voorwaarden ---
    pdf.ln(6)
    pdf.set_font(F, "", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 4.5,
        "Deze offerte is opgemaakt op basis van de door de klant verstrekte informatie. "
        "Prijzen zijn geldig tot de vermelde vervaldatum. Meerwerken door onvoorziene omstandigheden "
        "(bv. asbest, ontoegankelijke leidingtrace's, extra doorboringen) worden in regie aangerekend na overleg. "
        "Opdrachtgever voorziet een vrije en veilige toegang tot de werf en een werkende elektrische aansluiting. "
        "Bij toepassing van 6% BTW bevestigt de klant dat de woning ouder is dan 10 jaar en hoofdzakelijk privé wordt gebruikt.")

    out = pdf.output(dest="S")
    return bytes(out) if isinstance(out, (bytes, bytearray)) else out.encode("latin-1")
