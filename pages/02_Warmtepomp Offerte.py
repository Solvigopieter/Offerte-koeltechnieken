# pages/02_Warmtepomp Offerte.py
import streamlit as st

try:
    st.set_page_config(page_title="Warmtepomp Offerte — P&R", layout="wide", page_icon="🔥")
except Exception:
    pass

from auth import require_login
require_login()

from datetime import date, timedelta
import pandas as pd

from pr_core import DEFAULT_PRIJZEN, bereken_wp, maak_pdf, gen_offertenummer, eenheid_label
from storage import load_prijzen, save_project

P = load_prijzen(DEFAULT_PRIJZEN)

st.title("🔥 Lucht-water Warmtepomp Offerte")

loaded = st.session_state.pop("load_project", None)
if loaded and loaded.get("_type") == "wp":
    for k, v in loaded.items():
        if not k.startswith("_"):
            st.session_state[f"w_{k}"] = v
    st.success("Project geladen — pas aan waar nodig.")

# ================= Klant =================
st.subheader("Klantgegevens")
c1, c2 = st.columns(2)
with c1:
    klantnaam = st.text_input("Klantnaam", key="w_klantnaam")
    bedrijf = st.text_input("Bedrijfsnaam (optioneel)", key="w_bedrijf")
    adres = st.text_area("Adres", key="w_adres", height=80)
with c2:
    email = st.text_input("E-mail", key="w_email")
    tel = st.text_input("Telefoon", key="w_tel")
    offertedatum = st.date_input("Offertedatum", date.today())
    verloopdatum = st.date_input("Geldig tot", date.today() + timedelta(days=30))

# ================= Configuratie =================
st.subheader("Configuratie")
c3, c4, c5 = st.columns(3)
with c3:
    wtype = st.selectbox("Type warmtepomp", ["monoblock", "split"],
                         format_func=lambda v: "Monoblock (alles buiten)" if v == "monoblock" else "Split (binnen- + buitenunit)",
                         key="w_wtype")
    kw = st.selectbox("Vermogen (kW)", [6, 8, 11, 14, 16], index=1, key="w_kw")
    merk_model = st.text_input("Merk & model (op offerte)", key="w_merk", placeholder="bv. Daikin Altherma 3")
with c4:
    prijs_wp = st.number_input("Inkoopprijs warmtepomp (EUR)", min_value=0.0, value=5200.0, step=50.0, key="w_prijs")
    prijs_wp_verkoop = st.number_input("Verkoopprijs warmtepomp (EUR, 0 = auto marge%)", min_value=0.0, value=0.0, step=50.0, key="w_prijs_verkoop",
        help="Laat op 0 om automatisch inkoop × marge% te gebruiken. Vul in als je zelf een vaste verkoopprijs hanteert, los van de marge-instelling.")
    afgifte = st.selectbox("Afgiftesysteem", ["Vloerverwarming", "Radiatoren", "Gemengd"], key="w_afgifte")
with c5:
    buffer = st.selectbox("Buffervat", [0, 50, 100, 200], index=1,
                          format_func=lambda v: "Geen" if v == 0 else f"{v} L", key="w_buffer")
    boiler = st.selectbox("Sanitair warmwaterboiler", [0, 200, 300], index=2,
                          format_func=lambda v: "Geen" if v == 0 else f"{v} L", key="w_boiler")

c6, c7, c8 = st.columns(3)
with c6:
    hydro = st.checkbox("Hydraulisch materiaal (leidingen, kranen, expansievat)", value=True, key="w_hydro")
    elek = st.checkbox("Elektrische aansluiting + sturing", value=True, key="w_elek")
with c7:
    sokkel = st.checkbox("Betonsokkel / grondconsole", value=True, key="w_sokkel")
    afvoer_oud = st.checkbox("Afbraak & afvoer oude ketel", key="w_afvoer")
    regeling = st.checkbox("Slimme thermostaat / regeling", key="w_regeling")
with c8:
    techniekers = st.number_input("Aantal techniekers", min_value=1, value=2, key="w_techniekers")
    arbeid_aanrekenen = st.checkbox("Arbeid apart aanrekenen", value=True, key="w_arbeid_aanrekenen",
        help="Uitvinken als de installatie al inbegrepen zit in de toestelprijs (bv. bij sommige Panasonic-marges).")
    uren_manueel = st.number_input("Uren per technieker (0 = automatisch)", min_value=0.0, value=0.0, step=0.5, key="w_uren", disabled=not arbeid_aanrekenen)
    km = st.number_input("Afstand klant (km, enkel)", min_value=0.0, value=20.0, step=1.0, key="w_km")
    btw = st.selectbox("BTW-tarief", [0.06, 0.21], format_func=lambda v: f"{int(v*100)}%" + (" — renovatie >10 jaar" if v == 0.06 else " — nieuwbouw / <10 jaar"), key="w_btw")

# ================= Berekening =================
inp = dict(type=wtype, kw=kw, merk_model=merk_model, prijs_wp=prijs_wp,
           prijs_wp_verkoop=prijs_wp_verkoop, afgifte=afgifte,
           buffer=buffer, boiler=boiler, hydro=hydro, elek=elek, sokkel=sokkel,
           afvoer_oud=afvoer_oud, regeling=regeling,
           techniekers=techniekers, uren_manueel=uren_manueel, km=km, btw=btw,
           arbeid_aanrekenen=arbeid_aanrekenen)
res = bereken_wp(inp, P)

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
rows.append({"Omschrijving": "Dossier & opstart", "Aantal": "", "Eenheidsprijs": "", "Verkoop totaal (EUR)": round(res["vast"], 2)})
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

intro = ("Bedankt voor uw vertrouwen in P&R Koeltechnieken. Wij plaatsen uw lucht-water warmtepomp "
         "volledig sleutel-op-de-deur: hydraulische en elektrische aansluiting, vullen, ontluchten, "
         "configuratie van de regeling en indienststelling met uitleg voor de gebruiker.")

with b1:
    typetekst = "Monoblock" if wtype == "monoblock" else "Split"
    pdf_bytes = maak_pdf(f"Lucht-water warmtepomp {kw} kW — {typetekst}", klant, res, inp, intro)
    st.download_button("📄 Download offerte (PDF)", data=pdf_bytes,
                       file_name=f"{klant['nummer']}_warmtepomp.pdf", mime="application/pdf",
                       use_container_width=True)

with b2:
    if st.button("💾 Project bewaren", use_container_width=True):
        payload = {k.replace("w_", "", 1): v for k, v in st.session_state.items()
                   if k.startswith("w_") and isinstance(v, (str, int, float, bool))}
        payload["_type"] = "wp"
        pid = save_project("Warmtepomp", klantnaam or bedrijf, res["totaal"], payload)
        st.success(f"Bewaard als project {pid} — terug te vinden onder **Projecten**.")
