# pages/02_Warmtepomp Offerte.py
import streamlit as st

try:
    st.set_page_config(page_title="Warmtepomp Offerte — Solvigo", layout="wide", page_icon="🔥")
except Exception:
    pass

from auth import require_login
require_login()

from datetime import date, timedelta
import pandas as pd

from pr_core import DEFAULT_PRIJZEN, bereken_wp, maak_pdf, gen_offertenummer, eenheid_label
from storage import load_prijzen, save_project, load_materialen
import materialen as matlijst

P = load_prijzen(DEFAULT_PRIJZEN)
MATERIALEN = load_materialen()
MAT_MODI = ["📦 Gedetailleerd (materiaallijst)", "⚡ Snel (forfaitair)"]

st.title("🔥 Lucht-water Warmtepomp Offerte")

loaded = st.session_state.pop("load_project", None)
if loaded and loaded.get("_type") == "wp":
    for k, v in loaded.items():
        if not k.startswith("_") and "_btn" not in k:
            st.session_state[f"w_{k}"] = v
    matlijst.laad_keuze_uit_json("w", loaded.get("mat_json", ""))
    if loaded.get("mat_modus") not in MAT_MODI:
        st.session_state["w_mat_modus"] = MAT_MODI[1]   # oudere projecten: bedragen ongewijzigd
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

# ================= Materiaal =================
st.subheader("Materiaal")
mat_modus = st.radio("Hoe wil je het installatiemateriaal berekenen?", MAT_MODI, key="w_mat_modus", horizontal=True,
    help="Gedetailleerd: je duidt per artikel aan hoeveel je nodig hebt, met de prijzen uit **📦 Materialen & prijzen**. "
         "Buffervat, boiler, sokkel, regeling en afvoer blijven via de keuzes hierboven/hieronder lopen. "
         "Snel: forfaitaire bedragen voor hydraulica, elektriciteit en klein materiaal, zoals voorheen.")
gedetailleerd = (mat_modus == MAT_MODI[0])
gekozen_materiaal = None
mat_weergave = "artikel"
if gedetailleerd:
    gekozen_materiaal = matlijst.materiaal_keuze_ui("w", "Warmtepomp", MATERIALEN, 1 + P["marge_materiaal_pct"] / 100.0)
    MAT_WEERGAVE = {"Elk artikel apart": "artikel", "Per categorie": "categorie", "Eén totaalregel 'Installatiemateriaal'": "totaal"}
    mat_weergave = MAT_WEERGAVE[st.selectbox("Materiaal op de PDF tonen als", list(MAT_WEERGAVE.keys()), key="w_mat_weergave")]

st.subheader("Werk & opties")
c6, c7, c8 = st.columns(3)
with c6:
    hydro = st.checkbox("Hydraulisch materiaal (leidingen, kranen, expansievat)" + (" — forfait" if not gedetailleerd else ""),
                        value=True, key="w_hydro", disabled=gedetailleerd,
                        help="In gedetailleerde modus komt het hydraulisch materiaal uit de materiaallijst." if gedetailleerd else None)
    elek = st.checkbox("Elektrische aansluiting + sturing", value=True, key="w_elek",
                       help="Telt mee in de urenschatting. In gedetailleerde modus komt het materiaal uit de materiaallijst." if gedetailleerd else None)
with c7:
    sokkel = st.checkbox("Betonsokkel / grondconsole", value=True, key="w_sokkel")
    afvoer_oud = st.checkbox("Afbraak & afvoer oude ketel", key="w_afvoer")
    regeling = st.checkbox("Slimme thermostaat / regeling", key="w_regeling")
with c8:
    techniekers = st.number_input("Aantal techniekers", min_value=1, value=2, key="w_techniekers")
    arbeid_aanrekenen = st.checkbox("Arbeid apart aanrekenen", value=True, key="w_arbeid_aanrekenen",
        help="Uitvinken als de installatie al inbegrepen zit in de toestelprijs (bv. bij sommige Panasonic-marges).")
    arbeid_tonen = False
    if not arbeid_aanrekenen:
        arbeid_tonen = st.checkbox("Arbeid toch apart tonen op de offerte", key="w_arbeid_tonen",
            help="De werkuren worden uit de toestelprijs gehaald en als aparte regel getoond. "
                 "De warmtepomp lijkt zo goedkoper, de totaalprijs en je marge blijven exact gelijk.")
    arbeid_tonen_modus, arbeid_tonen_pct, arbeid_tonen_vast = "uren", 20.0, 0.0
    if arbeid_tonen:
        _modi = {"% van de toestelprijs": "pct", "Vast bedrag": "vast", "Uren × uurtarief": "uren"}
        arbeid_tonen_modus = _modi[st.selectbox("Installatieregel berekenen als", list(_modi.keys()), key="w_arbeid_tonen_modus")]
        if arbeid_tonen_modus == "pct":
            arbeid_tonen_pct = st.number_input("% van de toestelprijs naar installatie", min_value=0.0, max_value=60.0, value=20.0,
                                               step=1.0, key="w_arbeid_tonen_pct")
        elif arbeid_tonen_modus == "vast":
            arbeid_tonen_vast = st.number_input("Bedrag installatie (EUR excl. BTW)", min_value=0.0, value=550.0,
                                                step=10.0, key="w_arbeid_tonen_vast")
    uren_manueel = st.number_input("Uren per technieker (0 = automatisch)", min_value=0.0, value=0.0, step=0.5, key="w_uren",
                                   disabled=not (arbeid_aanrekenen or (arbeid_tonen and arbeid_tonen_modus == "uren")),
                                   help="Bij % of vast bedrag tellen de uren enkel nog mee voor je marge-berekening (loonkost).")
    dossier_aanrekenen = st.checkbox("Dossier-/opstartkost aanrekenen", value=True, key="w_dossier_aanrekenen",
        help="Uitvinken om de vaste dossier-/opstartkost weg te laten van deze offerte.")
    km = st.number_input("Afstand klant (km, enkel)", min_value=0.0, value=20.0, step=1.0, key="w_km")
    btw = st.selectbox("BTW-tarief", [0.06, 0.21], format_func=lambda v: f"{int(v*100)}%" + (" — renovatie >10 jaar" if v == 0.06 else " — nieuwbouw / <10 jaar"), key="w_btw")
    voorschot_vragen = st.checkbox(f"Voorschot vragen ({P.get('voorschot_pct', 40):g}% bij goedkeuring)", value=True, key="w_voorschot",
        help="Komt als betalingsvoorwaarde op de PDF. Percentage aanpasbaar bij Prijsinstellingen. Uitvinken voor kleine jobs.")

# ================= Korting =================
with st.expander("💶 Korting geven (bv. familie- of volumekorting)"):
    kc1, kc2, kc3 = st.columns(3)
    with kc1:
        korting_keuze = st.selectbox("Type korting", ["Geen korting", "Percentage (%)", "Vast bedrag (EUR)"], key="w_korting_type")
    with kc2:
        korting_waarde = st.number_input("Waarde", min_value=0.0, value=0.0, step=1.0, key="w_korting_waarde",
            help="Bij percentage: bv. 5 = 5% op het subtotaal. Bij vast bedrag: bedrag in EUR excl. BTW.",
            disabled=(korting_keuze == "Geen korting"))
    with kc3:
        korting_label = st.text_input("Omschrijving op offerte", value="Korting", key="w_korting_label",
            help="Bv. 'Familiekorting' — zo verschijnt het op de PDF.",
            disabled=(korting_keuze == "Geen korting"))
korting_type = {"Geen korting": "geen", "Percentage (%)": "pct", "Vast bedrag (EUR)": "vast"}[korting_keuze]

# ================= Berekening =================
inp = dict(type=wtype, kw=kw, merk_model=merk_model, prijs_wp=prijs_wp,
           prijs_wp_verkoop=prijs_wp_verkoop, afgifte=afgifte,
           buffer=buffer, boiler=boiler, hydro=hydro, elek=elek, sokkel=sokkel,
           afvoer_oud=afvoer_oud, regeling=regeling,
           techniekers=techniekers, uren_manueel=uren_manueel, km=km, btw=btw,
           arbeid_aanrekenen=arbeid_aanrekenen, arbeid_tonen=arbeid_tonen, arbeid_tonen_modus=arbeid_tonen_modus, arbeid_tonen_pct=arbeid_tonen_pct, arbeid_tonen_vast=arbeid_tonen_vast, dossier_aanrekenen=dossier_aanrekenen,
           korting_type=korting_type, korting_waarde=korting_waarde, korting_label=korting_label,
           materialen=gekozen_materiaal, mat_weergave=mat_weergave,
           voorschot_pct=(P.get("voorschot_pct", 40.0) if voorschot_vragen else 0.0))
res = bereken_wp(inp, P)

st.subheader("Offerte-opbouw")
def _eh(bedrag, unit=""):
    txt = f"€ {bedrag:,.2f}".replace(",", " ")
    return f"{txt} {unit}".strip() if unit else txt

rows = [{"Omschrijving": m[0].replace("\n", " — "), "Aantal": m[1], "Eenheidsprijs": _eh(m[4], eenheid_label(m[1])), "Verkoop totaal (EUR)": round(m[3], 2)} for m in res["mat"]]
if res["arbeid_aanrekenen"]:
    if arbeid_tonen and arbeid_tonen_modus == "pct":
        _arb_label = f"Installatie — {arbeid_tonen_pct:g}% uit toestelprijs"
    elif arbeid_tonen and arbeid_tonen_modus == "vast":
        _arb_label = "Installatie — vast bedrag uit toestelprijs"
    else:
        _arb_label = (f"Arbeid ({res['uren']:.1f} u × {techniekers} technieker(s))" + ("" if uren_manueel > 0 else " — auto")
                      + (" — uit toestelprijs gehaald" if arbeid_tonen else ""))
    rows.append({"Omschrijving": _arb_label, "Aantal": "", "Eenheidsprijs": "", "Verkoop totaal (EUR)": round(res["arbeid"], 2)})
else:
    rows.append({"Omschrijving": "Arbeid — inbegrepen in toestelprijs (niet apart aangerekend)", "Aantal": "", "Eenheidsprijs": "", "Verkoop totaal (EUR)": 0.0})
rows.append({"Omschrijving": "Verplaatsing (heen & terug)", "Aantal": f"{km} km", "Eenheidsprijs": "", "Verkoop totaal (EUR)": round(res["km_kost"], 2)})
if dossier_aanrekenen:
    rows.append({"Omschrijving": "Dossier & opstart", "Aantal": "", "Eenheidsprijs": "", "Verkoop totaal (EUR)": round(res["vast"], 2)})
if res.get("korting_bedrag", 0) > 0:
    rows.append({"Omschrijving": f"Korting — {res['korting_label']}", "Aantal": "", "Eenheidsprijs": "", "Verkoop totaal (EUR)": -round(res["korting_bedrag"], 2)})
st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
if arbeid_tonen:
    _vol = res.get("arbeid_gevraagd", 0.0)
    if res["arbeid"] + 0.01 < _vol:
        st.warning(f"Gevraagd: € {_vol:,.2f} installatie, maar er kan maar € {res['arbeid']:,.2f} uit de toestelprijs "
                   "gehaald worden zonder onder je inkoopprijs te zakken. Kies een lager % of bedrag.".replace(",", " "))
    else:
        st.caption(f"€ {res['arbeid']:,.2f} arbeid uit de toestelprijs gehaald — totaal en marge blijven gelijk.".replace(",", " "))

m1, m2, m3, m4 = st.columns(4)
m1.metric("Subtotaal excl. BTW", f"€ {res['subtotaal']:,.2f}".replace(",", " "))
m2.metric(f"BTW {int(btw*100)}%", f"€ {res['btw_bedrag']:,.2f}".replace(",", " "))
m3.metric("Totaal incl. BTW", f"€ {res['totaal']:,.2f}".replace(",", " "))
m4.metric("Geschatte brutomarge", f"€ {res['winst']:,.2f}".replace(",", " "))
if inp.get("voorschot_pct", 0) > 0:
    _vs = res["totaal"] * inp["voorschot_pct"] / 100
    st.caption(f"Voorschot {inp['voorschot_pct']:g}%: € {_vs:,.2f} · saldo na oplevering: € {res['totaal'] - _vs:,.2f}".replace(",", " "))

# ================= Export & bewaren =================
st.divider()
import crm_koppeling
b1, b2, b3 = st.columns(3)

klant = dict(naam=klantnaam, bedrijf=bedrijf, adres=adres, email=email, tel=tel,
             datum=offertedatum, verloop=verloopdatum,
             nummer=gen_offertenummer(klantnaam, offertedatum))

intro = ("Bedankt voor uw vertrouwen in Solvigo Koeltechnieken. Wij plaatsen uw lucht-water warmtepomp "
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
        st.session_state["w_mat_json"] = matlijst.keuze_als_json("w")
        payload = {k.replace("w_", "", 1): v for k, v in st.session_state.items()
                   if k.startswith("w_") and "_btn" not in k
                   and isinstance(v, (str, int, float, bool))}
        payload["_type"] = "wp"
        try:
            pid = save_project("Warmtepomp", klantnaam or bedrijf, res["totaal"], payload,
                              mat_inkoop=res.get("mat_inkoop", 0), netto_winst=res.get("winst", 0))
        except TypeError:
            pid = save_project("Warmtepomp", klantnaam or bedrijf, res["totaal"], payload)
        st.success(f"Bewaard als project {pid} — terug te vinden onder **Projecten**.")

with b3:
    if not crm_koppeling.crm_koppeling_beschikbaar():
        st.button("📤 Verstuur naar CRM", use_container_width=True, disabled=True,
                 help="Niet beschikbaar: zet 'crm_sheet_id' in de Secrets (zie README) om dit te activeren.")
    elif st.button("📤 Verstuur naar CRM", use_container_width=True, type="primary",
                  help="Maakt automatisch een klant + deal + offerte aan in het CRM, meteen zichtbaar in Pipeline."):
        if not (klantnaam or bedrijf).strip():
            st.error("Vul minstens een klantnaam of bedrijfsnaam in.")
        else:
            try:
                resultaat = crm_koppeling.verstuur_naar_crm(
                    klantnaam=klantnaam or bedrijf, adres=adres, email=email, tel=tel,
                    offerte_type="Warmtepomp", totaal=res["totaal"],
                    mat_inkoop=res.get("mat_inkoop", 0), winst=res.get("winst", 0),
                    offertenummer=klant["nummer"], btw_tarief=f"{int(btw*100)}%")
                extra = " (bestaande klant hergebruikt)" if resultaat["organisatie_hergebruikt"] else \
                        f" (nieuwe klant {resultaat['klantnummer']} aangemaakt)"
                st.success(f"✅ Verstuurd naar CRM{extra} — {resultaat['klantnaam']} staat nu in de Pipeline "
                          f"bij 'Offerte verstuurd', met deze offerte gekoppeld.")
            except Exception as e:
                st.error(f"Versturen naar CRM mislukt: {e}")
