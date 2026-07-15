# pages/01_Airco Offerte.py
import streamlit as st

try:
    st.set_page_config(page_title="Airco Offerte — Solvigo", layout="wide", page_icon="❄️")
except Exception:
    pass

from auth import require_login
require_login()

from datetime import date, timedelta
import pandas as pd

from pr_core import DEFAULT_PRIJZEN, bereken_airco, maak_pdf, gen_offertenummer, eenheid_label
from storage import load_prijzen, save_project

P = load_prijzen(DEFAULT_PRIJZEN)

st.title("❄️ Airco Offerte")

# ------- eventueel geladen project toepassen -------
loaded = st.session_state.pop("load_project", None)
if loaded and loaded.get("_type") == "airco":
    for k, v in loaded.items():
        if not k.startswith("_"):
            st.session_state[f"a_{k}"] = v
    st.success("Project geladen — pas aan waar nodig.")

# ================= Klant =================
st.subheader("Klantgegevens")
c1, c2 = st.columns(2)
with c1:
    klantnaam = st.text_input("Klantnaam", key="a_klantnaam")
    bedrijf = st.text_input("Bedrijfsnaam (optioneel)", key="a_bedrijf")
    adres = st.text_area("Adres", key="a_adres", height=80)
with c2:
    email = st.text_input("E-mail", key="a_email")
    tel = st.text_input("Telefoon", key="a_tel")
    offertedatum = st.date_input("Offertedatum", date.today())
    verloopdatum = st.date_input("Geldig tot", date.today() + timedelta(days=30))

# ================= Configuratie =================
st.subheader("Configuratie")
c3, c4, c5 = st.columns(3)
with c3:
    TYPES = {"Mono-split (1 binnenunit per systeem)": 1, "Multi-split — 2 binnenunits op 1 buitenunit": 2,
             "Multi-split — 3 binnenunits op 1 buitenunit": 3, "Multi-split — 4 binnenunits op 1 buitenunit": 4}
    type_label = st.selectbox("Type installatie", list(TYPES.keys()), key="a_type")
    n_binnen = TYPES[type_label]
    aantal_systemen = st.number_input("Aantal aparte systemen (elk met eigen buitenunit)", min_value=1, value=1, step=1, key="a_aantal_systemen",
        help="Bv. 3 losse mono-split airco's = 'Mono-split' + hier 3 invullen (3× eigen buitenunit). "
             "Voor 1 buitenunit met 3 binnenunits kies je hierboven 'Multi-split — 3 binnenunits' en laat dit op 1 staan.")
    merk_model = st.text_input("Merk & model (op offerte)", key="a_merk", placeholder="bv. Daikin Perfera 3,5 kW")
with c4:
    is_mono = (n_binnen == 1)
    if is_mono:
        st.markdown("**Toestel (set binnen + buitenunit)**")
        prijs_set = st.number_input("Inkoopprijs per set (EUR)", min_value=0.0, value=1100.0, step=10.0, key="a_prijs_set",
            help="Bij mono-split koop je meestal 1 set (binnen- + buitenunit samen), geen aparte prijzen.")
        prijs_set_verkoop = st.number_input("Verkoopprijs per set (EUR, 0 = auto marge%)", min_value=0.0, value=0.0, step=10.0, key="a_prijs_set_verkoop",
            help="Laat op 0 om automatisch inkoop × marge% te gebruiken. Vul in voor een vaste verkoopprijs, los van de marge-instelling.")
        prijs_buiten, prijs_buiten_verkoop = prijs_set, prijs_set_verkoop
        prijs_binnen, prijs_binnen_verkoop = 0.0, 0.0
    else:
        st.markdown("**Buitenunit**")
        prijs_buiten = st.number_input("Inkoopprijs buitenunit (EUR)", min_value=0.0, value=900.0, step=10.0, key="a_prijs_buiten")
        prijs_buiten_verkoop = st.number_input("Verkoopprijs buitenunit (EUR, 0 = auto marge%)", min_value=0.0, value=0.0, step=10.0, key="a_prijs_buiten_verkoop",
            help="Laat op 0 om automatisch inkoop × marge% te gebruiken. Vul in als je zelf een vaste verkoopprijs hanteert (bv. Panasonic-catalogusprijs), los van de marge-instelling.")
        st.markdown("**Binnenunit**")
        prijs_binnen = st.number_input("Inkoopprijs per binnenunit (EUR)", min_value=0.0, value=450.0, step=10.0, key="a_prijs_binnen")
        prijs_binnen_verkoop = st.number_input("Verkoopprijs per binnenunit (EUR, 0 = auto marge%)", min_value=0.0, value=0.0, step=10.0, key="a_prijs_binnen_verkoop")
with c5:
    leiding_m = st.number_input("Totale leidinglengte, alle systemen samen (m)", min_value=0.0, value=5.0, step=0.5, key="a_leiding")
    goot_m = st.number_input("Sierlijst / leidinggoot, totaal (m)", min_value=0.0, value=3.0, step=0.5, key="a_goot")
    goot_bij_klein = st.checkbox("Kabelgoot bij 'Klein materiaal' voegen (geen aparte regel)", key="a_goot_bij_klein",
        help="Handig als er maar een klein stukje kabelgoot nodig is — de kost wordt dan meegeteld in 'Klein materiaal & bevestiging' in plaats van als eigen regel op de offerte te verschijnen.")

c6, c7, c8 = st.columns(3)
with c6:
    doorvoeren = st.number_input("Muurdoorvoeren, totaal aantal", min_value=0, value=1, key="a_doorvoeren")
    koelmiddel_m = st.number_input("Extra koelmiddel (m boven voorvulling)", min_value=0.0, value=0.0, step=1.0, key="a_koelmiddel")
with c7:
    condenspomp = st.checkbox("Condenspomp nodig (per binnenunit)", key="a_condenspomp")
    console = st.checkbox("Muurconsole + trillingsdempers (per systeem)", value=True, key="a_console")
    elek = st.checkbox("Elektrische voeding trekken (per systeem)", value=True, key="a_elek")
    hoogtewerker = st.checkbox("Hoogtewerker / moeilijke toegang", key="a_hoogtewerker")
with c8:
    techniekers = st.number_input("Aantal techniekers", min_value=1, value=2, key="a_techniekers")
    arbeid_aanrekenen = st.checkbox("Arbeid apart aanrekenen", value=True, key="a_arbeid_aanrekenen",
        help="Uitvinken als de installatie al inbegrepen zit in de toestelprijs (bv. bij sommige Panasonic-marges).")
    uren_manueel = st.number_input("Uren per technieker (0 = automatisch)", min_value=0.0, value=0.0, step=0.5, key="a_uren", disabled=not arbeid_aanrekenen)
    dossier_aanrekenen = st.checkbox("Dossier-/opstartkost aanrekenen", value=True, key="a_dossier_aanrekenen",
        help="Uitvinken om de vaste dossier-/opstartkost weg te laten van deze offerte.")
    km = st.number_input("Afstand klant (km, enkel)", min_value=0.0, value=20.0, step=1.0, key="a_km")
    btw = st.selectbox("BTW-tarief", [0.21, 0.06], format_func=lambda v: f"{int(v*100)}%" + (" — renovatie >10 jaar" if v == 0.06 else " — nieuwbouw / <10 jaar"), key="a_btw")

# ================= Berekening =================
inp = dict(n_binnen=n_binnen, aantal_systemen=aantal_systemen, mono_set=is_mono, merk_model=merk_model, prijs_buiten=prijs_buiten,
           prijs_buiten_verkoop=prijs_buiten_verkoop,
           prijs_binnen=prijs_binnen, prijs_binnen_verkoop=prijs_binnen_verkoop,
           leiding_m=leiding_m, goot_m=goot_m, goot_bij_klein=goot_bij_klein,
           doorvoeren=doorvoeren, koelmiddel_m=koelmiddel_m, condenspomp=condenspomp,
           console=console, elek=elek, hoogtewerker=hoogtewerker,
           techniekers=techniekers, uren_manueel=uren_manueel, km=km, btw=btw,
           arbeid_aanrekenen=arbeid_aanrekenen, dossier_aanrekenen=dossier_aanrekenen)
res = bereken_airco(inp, P)

st.subheader("Offerte-opbouw")
def _eh(bedrag, unit=""):
    txt = f"€ {bedrag:,.2f}".replace(",", " ")
    return f"{txt} {unit}".strip() if unit else txt

rows = [{"Omschrijving": m[0], "Aantal": m[1], "Eenheidsprijs": _eh(m[4], eenheid_label(m[1])), "Verkoop totaal (EUR)": round(m[3], 2)} for m in res["mat"]]
if arbeid_aanrekenen:
    rows.append({"Omschrijving": f"Arbeid ({res['uren']:.1f} u × {techniekers} technieker(s))" + ("" if uren_manueel > 0 else " — auto"), "Aantal": "", "Eenheidsprijs": "", "Verkoop totaal (EUR)": round(res["arbeid"], 2)})
else:
    rows.append({"Omschrijving": "Arbeid — inbegrepen in toestelprijs (niet apart aangerekend)", "Aantal": "", "Eenheidsprijs": "", "Verkoop totaal (EUR)": 0.0})
rows.append({"Omschrijving": "Verplaatsing (heen & terug)", "Aantal": f"{km} km", "Eenheidsprijs": "", "Verkoop totaal (EUR)": round(res["km_kost"], 2)})
if dossier_aanrekenen:
    rows.append({"Omschrijving": "Dossier & opstart", "Aantal": "", "Eenheidsprijs": "", "Verkoop totaal (EUR)": round(res["vast"], 2)})
if res["extra_hoogte"] > 0:
    rows.append({"Omschrijving": "Hoogtewerker", "Aantal": "", "Eenheidsprijs": "", "Verkoop totaal (EUR)": round(res["extra_hoogte"], 2)})
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Subtotaal excl. BTW", f"€ {res['subtotaal']:,.2f}".replace(",", " "))
m2.metric(f"BTW {int(btw*100)}%", f"€ {res['btw_bedrag']:,.2f}".replace(",", " "))
m3.metric("Totaal incl. BTW", f"€ {res['totaal']:,.2f}".replace(",", " "))
m4.metric("Geschatte brutomarge", f"€ {res['winst']:,.2f}".replace(",", " "))

# ================= Export & bewaren =================
st.divider()
b1, b2 = st.columns(2)

klant = dict(naam=klantnaam, bedrijf=bedrijf, adres=adres, email=email, tel=tel,
             datum=offertedatum, verloop=verloopdatum,
             nummer=gen_offertenummer(klantnaam, offertedatum))

intro = ("Bedankt voor uw vertrouwen in Solvigo Koeltechnieken. Wij installeren uw airconditioning "
         "vakkundig en volgens de geldende normen, inclusief vacumeren, lektest en indienststelling. "
         "U geniet van koeling in de zomer en zuinige verwarming in de winter.")

with b1:
    titel_suffix = f" — {aantal_systemen}x apart systeem" if aantal_systemen > 1 else ""
    pdf_bytes = maak_pdf(f"Airco-installatie — {type_label}{titel_suffix}", klant, res, inp, intro)
    st.download_button("📄 Download offerte (PDF)", data=pdf_bytes,
                       file_name=f"{klant['nummer']}_airco.pdf", mime="application/pdf",
                       use_container_width=True)

with b2:
    if st.button("💾 Project bewaren", use_container_width=True):
        payload = {k.replace("a_", "", 1): v for k, v in st.session_state.items()
                   if k.startswith("a_") and isinstance(v, (str, int, float, bool))}
        payload["_type"] = "airco"
        pid = save_project("Airco", klantnaam or bedrijf, res["totaal"], payload)
        st.success(f"Bewaard als project {pid} — terug te vinden onder **Projecten**.")
