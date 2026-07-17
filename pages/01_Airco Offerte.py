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
import pr_catalogus as cat

P = load_prijzen(DEFAULT_PRIJZEN)

st.title("❄️ Airco Offerte")

# ------- eventueel geladen project toepassen -------
loaded = st.session_state.pop("load_project", None)
if loaded and loaded.get("_type") == "airco":
    for k, v in loaded.items():
        if not k.startswith("_") and not k.endswith("_btn"):
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
    is_mono = (n_binnen == 1)

    verschillende_toestellen = False
    if is_mono:
        verschillende_toestellen = st.checkbox("Toestellen hebben elk een andere grootte/prijs", key="a_verschillende_toestellen",
            help="Aanvinken als je bv. 3 losse mono-split airco's plaatst die niet allemaal hetzelfde vermogen/merk/prijs hebben. "
                 "Je vult dan hieronder elk toestel apart in.")

    if verschillende_toestellen:
        st.caption("Aantal systemen = aantal rijen in de tabel hieronder.")
        aantal_systemen = 1  # wordt overschreven na de tabel
        merk_model = ""
    else:
        aantal_systemen = st.number_input("Aantal aparte systemen (elk met eigen buitenunit)", min_value=1, value=1, step=1, key="a_aantal_systemen",
            help="Bv. 3 losse mono-split airco's = 'Mono-split' + hier 3 invullen (3× eigen buitenunit). "
                 "Voor 1 buitenunit met 3 binnenunits kies je hierboven 'Multi-split — 3 binnenunits' en laat dit op 1 staan.")
        merk_model = st.text_input("Merk & model (op offerte)", key="a_merk", placeholder="bv. Daikin Perfera 3,5 kW")
with c4:
    if verschillende_toestellen:
        st.markdown("**Toestellen**")
        st.caption("Prijzen en merk/model vul je hieronder per toestel in ↓")
        prijs_buiten, prijs_buiten_verkoop = 0.0, 0.0
        prijs_binnen, prijs_binnen_verkoop = 0.0, 0.0
    elif is_mono:
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

korting_pct = P.get("panasonic_korting_pct", 40.0)


def _inkoop_schatting(prijs):
    return round(prijs * (1 - korting_pct / 100), 2)


def _fmt_eur(x):
    return f"€ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def mono_picker(prefix):
    """Getrapte keuze uit MONO_SETS: familie -> kleur -> vermogen. Geeft gekozen item terug."""
    families = sorted(set(x[0] for x in cat.MONO_SETS))
    k1, k2, k3 = st.columns(3)
    with k1:
        fam = st.selectbox("Model", families, key=f"{prefix}_fam")
    subset = [x for x in cat.MONO_SETS if x[0] == fam]
    kleuren = sorted(set(x[1] for x in subset if x[1]))
    if kleuren:
        with k2:
            kleur = st.selectbox("Kleur", kleuren, key=f"{prefix}_kleur")
        subset = [x for x in subset if x[1] == kleur]
    else:
        with k2:
            st.selectbox("Kleur", ["—"], key=f"{prefix}_kleur_x", disabled=True)
    with k3:
        vermogens = sorted(set(x[2] for x in subset))
        kw = st.selectbox("Vermogen (kW)", vermogens, key=f"{prefix}_kw")
    item = [x for x in subset if x[2] == kw][0]
    st.info(f"**{cat.mono_naam(item)}** — adviesprijs {_fmt_eur(item[3])} · geschatte inkoop (−{korting_pct:.0f}%): {_fmt_eur(_inkoop_schatting(item[3]))}")
    return item


# ================= Panasonic-catalogus: automatische prijsinvulling =================
if not verschillende_toestellen:
    with st.expander("📋 Kies toestel uit Panasonic-catalogus (vult prijs & merk/model automatisch in)"):
        if is_mono:
            item = mono_picker("a_cat_mono")

            def _vul_mono(gekozen=None):
                st.session_state["a_merk"] = cat.mono_naam(st.session_state["_a_cat_mono_item"])
                st.session_state["a_prijs_set"] = _inkoop_schatting(st.session_state["_a_cat_mono_item"][3])
                st.session_state["a_prijs_set_verkoop"] = float(st.session_state["_a_cat_mono_item"][3])

            st.session_state["_a_cat_mono_item"] = item
            st.button("↳ Vul deze prijs in", key="a_cat_mono_btn", on_click=_vul_mono)
        else:
            st.markdown("**Buitenunit**")
            b1, b2 = st.columns(2)
            with b1:
                buiten_fams = sorted(set(x[0] for x in cat.MULTI_BUITEN))
                bfam = st.selectbox("Systeem", buiten_fams, key="a_cat_bfam")
            with b2:
                buiten_subset = [x for x in cat.MULTI_BUITEN if x[0] == bfam]
                bmodel = st.selectbox("Buitenunit", buiten_subset,
                    format_func=lambda x: f"{x[1]} ({x[2]}) — {_fmt_eur(x[3])}", key="a_cat_bmodel")
            st.session_state["_a_cat_buiten_item"] = bmodel

            def _vul_buiten():
                it = st.session_state["_a_cat_buiten_item"]
                st.session_state["a_merk"] = cat.buiten_naam(it)
                st.session_state["a_prijs_buiten"] = _inkoop_schatting(it[3])
                st.session_state["a_prijs_buiten_verkoop"] = float(it[3])

            st.button("↳ Vul buitenunit-prijs in", key="a_cat_buiten_btn", on_click=_vul_buiten)

            st.markdown("**Binnenunit** (prijs per stuk)")
            i1, i2, i3 = st.columns(3)
            with i1:
                binnen_fams = sorted(set(x[0] for x in cat.MULTI_BINNEN))
                ifam = st.selectbox("Type", binnen_fams, key="a_cat_ifam")
            binnen_subset = [x for x in cat.MULTI_BINNEN if x[0] == ifam]
            ikleuren = sorted(set(x[1] for x in binnen_subset if x[1]))
            if ikleuren:
                with i2:
                    ikleur = st.selectbox("Kleur", ikleuren, key="a_cat_ikleur")
                binnen_subset = [x for x in binnen_subset if x[1] == ikleur]
            else:
                with i2:
                    st.selectbox("Kleur", ["—"], key="a_cat_ikleur_x", disabled=True)
            with i3:
                ivermogens = sorted(set(x[2] for x in binnen_subset))
                ikw = st.selectbox("Vermogen (kW)", ivermogens, key="a_cat_ikw")
            binnen_item = [x for x in binnen_subset if x[2] == ikw][0]
            st.info(f"**{cat.binnen_naam(binnen_item)}** — adviesprijs {_fmt_eur(binnen_item[3])} · geschatte inkoop: {_fmt_eur(_inkoop_schatting(binnen_item[3]))}")
            st.session_state["_a_cat_binnen_item"] = binnen_item

            def _vul_binnen():
                it = st.session_state["_a_cat_binnen_item"]
                st.session_state["a_prijs_binnen"] = _inkoop_schatting(it[3])
                st.session_state["a_prijs_binnen_verkoop"] = float(it[3])

            st.button("↳ Vul binnenunit-prijs in", key="a_cat_binnen_btn", on_click=_vul_binnen)
        st.caption(f"Inkoopprijs = adviesprijs × {(100-korting_pct)/100:.2f} ({korting_pct:.0f}% dealerkorting — instelbaar bij Prijsinstellingen). "
                   f"Verkoopprijs = Panasonic-adviesprijs, zelf aan te passen.")

custom_units = []
if verschillende_toestellen:
    st.markdown("**Toestellen — elk apart merk, model en prijs**")

    with st.expander("📋 Toestel uit Panasonic-catalogus toevoegen aan de tabel"):
        item_add = mono_picker("a_cat_add")
        st.session_state["_a_cat_add_item"] = item_add
        aantal_add = st.number_input("Aantal van dit toestel toevoegen", min_value=1, value=1, step=1, key="a_cat_add_n")

        def _voeg_toe():
            it = st.session_state["_a_cat_add_item"]
            naam = cat.mono_naam(it)
            nieuwe_rijen = pd.DataFrame([
                {"Merk & model": naam, "Inkoopprijs (EUR)": _inkoop_schatting(it[3]), "Verkoopprijs (EUR, 0=auto)": float(it[3])}
                for _ in range(int(st.session_state["a_cat_add_n"]))
            ])
            bestaand = st.session_state.get("a_units_df")
            if bestaand is None or bestaand.empty:
                st.session_state["a_units_df"] = nieuwe_rijen
            else:
                st.session_state["a_units_df"] = pd.concat([bestaand, nieuwe_rijen], ignore_index=True)
            # widget-cache wissen zodat de tabel de nieuwe rijen effectief toont
            st.session_state.pop("a_units_editor", None)

        st.button("↳ Toevoegen aan tabel", key="a_cat_add_btn", on_click=_voeg_toe)

    default_rows = pd.DataFrame({
        "Merk & model": pd.Series(dtype="str"),
        "Inkoopprijs (EUR)": pd.Series(dtype="float"),
        "Verkoopprijs (EUR, 0=auto)": pd.Series(dtype="float"),
    })
    edited = st.data_editor(
        st.session_state.get("a_units_df", default_rows),
        num_rows="dynamic", use_container_width=True, key="a_units_editor",
        column_config={
            "Inkoopprijs (EUR)": st.column_config.NumberColumn(min_value=0.0, step=10.0, format="%.2f"),
            "Verkoopprijs (EUR, 0=auto)": st.column_config.NumberColumn(min_value=0.0, step=10.0, format="%.2f"),
        },
    )
    st.session_state["a_units_df"] = edited
    for _, row in edited.iterrows():
        naam_ruw = row.get("Merk & model")
        naam = "" if pd.isna(naam_ruw) else str(naam_ruw).strip()
        inkoop_ruw = row.get("Inkoopprijs (EUR)")
        inkoop = 0.0 if pd.isna(inkoop_ruw) else float(inkoop_ruw)
        verkoop_ruw = row.get("Verkoopprijs (EUR, 0=auto)")
        verkoop = 0.0 if pd.isna(verkoop_ruw) else float(verkoop_ruw)
        if naam or inkoop > 0:
            custom_units.append({"merk_model": naam, "inkoop": inkoop, "verkoop": verkoop})
    aantal_systemen = max(1, len(custom_units))
    if not custom_units:
        st.warning("Vul minstens één toestel in de tabel hierboven in, of voeg er een toe uit de catalogus.")

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

# ================= Korting =================
with st.expander("💶 Korting geven (bv. familie- of volumekorting)"):
    kc1, kc2, kc3 = st.columns(3)
    with kc1:
        korting_keuze = st.selectbox("Type korting", ["Geen korting", "Percentage (%)", "Vast bedrag (EUR)"], key="a_korting_type")
    with kc2:
        korting_waarde = st.number_input("Waarde", min_value=0.0, value=0.0, step=1.0, key="a_korting_waarde",
            help="Bij percentage: bv. 5 = 5% op het subtotaal. Bij vast bedrag: bedrag in EUR excl. BTW.",
            disabled=(korting_keuze == "Geen korting"))
    with kc3:
        korting_label = st.text_input("Omschrijving op offerte", value="Korting", key="a_korting_label",
            help="Bv. 'Familiekorting' of 'Volumekorting 3 toestellen' — zo verschijnt het op de PDF.",
            disabled=(korting_keuze == "Geen korting"))
korting_type = {"Geen korting": "geen", "Percentage (%)": "pct", "Vast bedrag (EUR)": "vast"}[korting_keuze]

# ================= Berekening =================
inp = dict(n_binnen=n_binnen, aantal_systemen=aantal_systemen, mono_set=is_mono, custom_units=custom_units, merk_model=merk_model, prijs_buiten=prijs_buiten,
           prijs_buiten_verkoop=prijs_buiten_verkoop,
           prijs_binnen=prijs_binnen, prijs_binnen_verkoop=prijs_binnen_verkoop,
           leiding_m=leiding_m, goot_m=goot_m, goot_bij_klein=goot_bij_klein,
           doorvoeren=doorvoeren, koelmiddel_m=koelmiddel_m, condenspomp=condenspomp,
           console=console, elek=elek, hoogtewerker=hoogtewerker,
           techniekers=techniekers, uren_manueel=uren_manueel, km=km, btw=btw,
           arbeid_aanrekenen=arbeid_aanrekenen, dossier_aanrekenen=dossier_aanrekenen,
           korting_type=korting_type, korting_waarde=korting_waarde, korting_label=korting_label)
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
if res.get("korting_bedrag", 0) > 0:
    rows.append({"Omschrijving": f"Korting — {res['korting_label']}", "Aantal": "", "Eenheidsprijs": "", "Verkoop totaal (EUR)": -round(res["korting_bedrag"], 2)})
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
        # Knoppen (eindigen op _btn) en andere widget-interne/niet-scalaire status
        # mogen NOOIT herladen worden in st.session_state — dat geeft een Streamlit-fout.
        payload = {k.replace("a_", "", 1): v for k, v in st.session_state.items()
                   if k.startswith("a_") and not k.endswith("_btn")
                   and isinstance(v, (str, int, float, bool))}
        payload["_type"] = "airco"
        pid = save_project("Airco", klantnaam or bedrijf, res["totaal"], payload)
        st.success(f"Bewaard als project {pid} — terug te vinden onder **Projecten**.")
