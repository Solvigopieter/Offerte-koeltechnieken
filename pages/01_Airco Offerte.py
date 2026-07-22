# pages/01_Airco Offerte.py
import streamlit as st

try:
    st.set_page_config(page_title="Airco Offerte — Solvigo", layout="wide", page_icon="❄️")
except Exception:
    pass

from auth import require_login
require_login()

from datetime import date, timedelta
import json
import math
import pandas as pd

from pr_core import DEFAULT_PRIJZEN, bereken_airco, bereken_airco_gemengd, maak_pdf, gen_offertenummer, eenheid_label
from storage import load_prijzen, save_project
import pr_catalogus as cat

P = load_prijzen(DEFAULT_PRIJZEN)

st.title("❄️ Airco Offerte")

# ------- eventueel geladen project toepassen -------
loaded = st.session_state.pop("load_project", None)
if loaded and loaded.get("_type") == "airco":
    for k, v in loaded.items():
        if not k.startswith("_") and "_btn" not in k:
            st.session_state[f"a_{k}"] = v
    if "a_blokken_json" in st.session_state:
        try:
            st.session_state["a_blokken"] = json.loads(st.session_state["a_blokken_json"])
        except Exception:
            st.session_state["a_blokken"] = []
    if "a_units_json" in st.session_state:
        try:
            st.session_state["a_units_df"] = pd.DataFrame(json.loads(st.session_state["a_units_json"]))
            st.session_state.pop("a_units_editor", None)  # forceer her-initialisatie van de tabelwidget
        except Exception:
            pass
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

# ================= Hulpfuncties (gelden voor beide modi) =================
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


def multi_buiten_picker(prefix):
    """Getrapte keuze uit MULTI_BUITEN: systeem -> buitenunit. Geeft gekozen item terug."""
    b1, b2 = st.columns(2)
    with b1:
        buiten_fams = sorted(set(x[0] for x in cat.MULTI_BUITEN))
        bfam = st.selectbox("Systeem", buiten_fams, key=f"{prefix}_fam")
    with b2:
        buiten_subset = [x for x in cat.MULTI_BUITEN if x[0] == bfam]
        bmodel = st.selectbox("Buitenunit", buiten_subset,
            format_func=lambda x: f"{x[1]} ({x[2]}) — {_fmt_eur(x[3])}", key=f"{prefix}_model")
    st.caption(f"{cat.buiten_naam(bmodel)} — adviesprijs {_fmt_eur(bmodel[3])} · geschatte inkoop (−{korting_pct:.0f}%): {_fmt_eur(_inkoop_schatting(bmodel[3]))}")
    return bmodel


def multi_binnen_picker(prefix):
    """Getrapte keuze uit MULTI_BINNEN: type -> kleur -> vermogen. Geeft gekozen item terug."""
    i1, i2, i3 = st.columns(3)
    with i1:
        binnen_fams = sorted(set(x[0] for x in cat.MULTI_BINNEN))
        ifam = st.selectbox("Type", binnen_fams, key=f"{prefix}_fam")
    binnen_subset = [x for x in cat.MULTI_BINNEN if x[0] == ifam]
    ikleuren = sorted(set(x[1] for x in binnen_subset if x[1]))
    if ikleuren:
        with i2:
            ikleur = st.selectbox("Kleur", ikleuren, key=f"{prefix}_kleur")
        binnen_subset = [x for x in binnen_subset if x[1] == ikleur]
    else:
        with i2:
            st.selectbox("Kleur", ["—"], key=f"{prefix}_kleur_x", disabled=True)
    with i3:
        ivermogens = sorted(set(x[2] for x in binnen_subset))
        ikw = st.selectbox("Vermogen (kW)", ivermogens, key=f"{prefix}_kw")
    item = [x for x in binnen_subset if x[2] == ikw][0]
    st.caption(f"{cat.binnen_naam(item)} — adviesprijs {_fmt_eur(item[3])} · geschatte inkoop (−{korting_pct:.0f}%): {_fmt_eur(_inkoop_schatting(item[3]))}")
    return item


TYPE_OPTIES = {"Mono-split (1 binnenunit)": 1, "Multi-split — 2 binnenunits op 1 buitenunit": 2,
               "Multi-split — 3 binnenunits op 1 buitenunit": 3, "Multi-split — 4 binnenunits op 1 buitenunit": 4}

# ================= Type installatie =================
gemengd = st.checkbox("🔀 Gemengde installatie (bv. multi-split + losse mono-split samen in dezelfde woning)", key="a_gemengd",
    help="Gebruik dit wanneer je in dezelfde offerte verschillende SOORTEN systemen combineert "
         "(bv. een multi-split met 3 binnenunits voor de living, plus een losse mono-split voor een slaapkamer). "
         "Leidingwerk, klein materiaal, arbeid en verplaatsing vul je dan één keer in voor de volledige job.")

if not gemengd:
    # ============================================================ ENKELVOUDIGE INSTALLATIE
    st.subheader("Configuratie")
    c3, c4 = st.columns(2)
    with c3:
        type_label = st.selectbox("Type installatie", list(TYPE_OPTIES.keys()), key="a_type")
        n_binnen = TYPE_OPTIES[type_label]
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

    # ---- Panasonic-catalogus: automatische prijsinvulling ----
    if not verschillende_toestellen:
        with st.expander("📋 Kies toestel uit Panasonic-catalogus (vult prijs & merk/model automatisch in)"):
            if is_mono:
                item = mono_picker("a_cat_mono")

                def _vul_mono():
                    st.session_state["a_merk"] = cat.mono_naam(st.session_state["_a_cat_mono_item"])
                    st.session_state["a_prijs_set"] = _inkoop_schatting(st.session_state["_a_cat_mono_item"][3])
                    st.session_state["a_prijs_set_verkoop"] = float(st.session_state["_a_cat_mono_item"][3])

                st.session_state["_a_cat_mono_item"] = item
                st.button("↳ Vul deze prijs in", key="a_cat_mono_btn", on_click=_vul_mono)
            else:
                st.markdown("**Buitenunit**")
                bmodel = multi_buiten_picker("a_cat_buiten")
                st.session_state["_a_cat_buiten_item"] = bmodel

                def _vul_buiten():
                    it = st.session_state["_a_cat_buiten_item"]
                    st.session_state["a_merk"] = cat.buiten_naam(it)
                    st.session_state["a_prijs_buiten"] = _inkoop_schatting(it[3])
                    st.session_state["a_prijs_buiten_verkoop"] = float(it[3])

                st.button("↳ Vul buitenunit-prijs in", key="a_cat_buiten_btn", on_click=_vul_buiten)

                st.markdown("**Binnenunit** (prijs per stuk)")
                binnen_item = multi_binnen_picker("a_cat_binnen")
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

else:
    # ============================================================ GEMENGDE INSTALLATIE
    st.subheader("Systemen")
    st.caption("Voeg elk apart systeem toe — bv. eerst het multi-split systeem voor de living, dan de losse "
               "mono-split voor de slaapkamer. Leidingwerk, klein materiaal, arbeid e.d. vul je hieronder "
               "(bij 'Gedeelde gegevens') één keer in voor de volledige job.")

    if "a_blokken" not in st.session_state:
        st.session_state["a_blokken"] = []

    with st.expander("➕ Systeem toevoegen", expanded=len(st.session_state["a_blokken"]) == 0):
        bl1, bl2, bl3 = st.columns(3)
        with bl1:
            blok_naam = st.text_input("Naam (bv. 'Living')", key="a_blok_naam")
        with bl2:
            blok_type_label = st.selectbox("Type", list(TYPE_OPTIES.keys()), key="a_blok_type")
        blok_n = TYPE_OPTIES[blok_type_label]
        with bl3:
            blok_aantal = st.number_input("Aantal van dit systeem", min_value=1, value=1, step=1, key="a_blok_aantal",
                help="Bv. 2 losse mono-split airco's van dezelfde grootte in dit blok = hier 2 invullen.")

        blok_verschillende_binnen = False
        if blok_n > 1:
            blok_verschillende_binnen = st.checkbox(
                "Binnenunits zijn niet allemaal hetzelfde (bv. wandmodel + vloerconsole samen op 1 buitenunit)",
                key="a_blok_verschillende_binnen")

        with st.expander("📋 Prijs uit Panasonic-catalogus halen (optioneel)"):
            if blok_n == 1:
                blok_item = mono_picker("a_blok_cat_mono")
                st.session_state["_a_blok_cat_mono_item"] = blok_item

                def _vul_blok_mono():
                    it = st.session_state["_a_blok_cat_mono_item"]
                    st.session_state["a_blok_merk"] = cat.mono_naam(it)
                    st.session_state["a_blok_prijs_buiten"] = _inkoop_schatting(it[3])
                    st.session_state["a_blok_prijs_buiten_verkoop"] = float(it[3])

                st.button("↳ Vul deze prijs in", key="a_blok_cat_mono_btn", on_click=_vul_blok_mono)
            else:
                st.markdown("**Buitenunit**")
                blok_bmodel = multi_buiten_picker("a_blok_cat_buiten")
                st.session_state["_a_blok_cat_buiten_item"] = blok_bmodel

                def _vul_blok_buiten():
                    it = st.session_state["_a_blok_cat_buiten_item"]
                    st.session_state["a_blok_merk"] = cat.buiten_naam(it)
                    st.session_state["a_blok_prijs_buiten"] = _inkoop_schatting(it[3])
                    st.session_state["a_blok_prijs_buiten_verkoop"] = float(it[3])

                st.button("↳ Vul buitenunit-prijs in", key="a_blok_cat_buiten_btn", on_click=_vul_blok_buiten)

                if not blok_verschillende_binnen:
                    st.markdown("**Binnenunit** (prijs per stuk)")
                    blok_binnen_item = multi_binnen_picker("a_blok_cat_binnen")
                    st.session_state["_a_blok_cat_binnen_item"] = blok_binnen_item

                    def _vul_blok_binnen():
                        it = st.session_state["_a_blok_cat_binnen_item"]
                        st.session_state["a_blok_prijs_binnen"] = _inkoop_schatting(it[3])
                        st.session_state["a_blok_prijs_binnen_verkoop"] = float(it[3])

                    st.button("↳ Vul binnenunit-prijs in", key="a_blok_cat_binnen_btn", on_click=_vul_blok_binnen)
                else:
                    st.markdown("**Binnenunit toevoegen aan dit systeem**")
                    blok_binnen_item = multi_binnen_picker("a_blok_cat_binnen_multi")
                    st.session_state["_a_blok_cat_binnen_multi_item"] = blok_binnen_item

                    def _voeg_blok_binnen_toe():
                        it = st.session_state["_a_blok_cat_binnen_multi_item"]
                        naam = cat.binnen_naam(it)
                        nieuwe_rij = pd.DataFrame([{
                            "Merk & model": naam, "Inkoopprijs (EUR)": _inkoop_schatting(it[3]),
                            "Verkoopprijs (EUR, 0=auto)": float(it[3]),
                        }])
                        bestaand = st.session_state.get("a_blok_binnen_df")
                        if bestaand is None or bestaand.empty:
                            st.session_state["a_blok_binnen_df"] = nieuwe_rij
                        else:
                            st.session_state["a_blok_binnen_df"] = pd.concat([bestaand, nieuwe_rij], ignore_index=True)
                        st.session_state.pop("a_blok_binnen_editor", None)

                    st.button("↳ Toevoegen aan tabel hieronder", key="a_blok_cat_binnen_multi_btn",
                             on_click=_voeg_blok_binnen_toe)

        blok_custom_binnen = []
        if blok_n > 1 and blok_verschillende_binnen:
            st.markdown("**Binnenunits in dit systeem — elk apart**")
            binnen_default = pd.DataFrame({
                "Merk & model": pd.Series(dtype="str"),
                "Inkoopprijs (EUR)": pd.Series(dtype="float"),
                "Verkoopprijs (EUR, 0=auto)": pd.Series(dtype="float"),
            })
            blok_binnen_edited = st.data_editor(
                st.session_state.get("a_blok_binnen_df", binnen_default),
                num_rows="dynamic", use_container_width=True, key="a_blok_binnen_editor",
                column_config={
                    "Inkoopprijs (EUR)": st.column_config.NumberColumn(min_value=0.0, step=10.0, format="%.2f"),
                    "Verkoopprijs (EUR, 0=auto)": st.column_config.NumberColumn(min_value=0.0, step=10.0, format="%.2f"),
                },
            )
            st.session_state["a_blok_binnen_df"] = blok_binnen_edited
            for _, row in blok_binnen_edited.iterrows():
                naam_ruw = row.get("Merk & model")
                naam = "" if pd.isna(naam_ruw) else str(naam_ruw).strip()
                inkoop_ruw = row.get("Inkoopprijs (EUR)")
                inkoop = 0.0 if pd.isna(inkoop_ruw) else float(inkoop_ruw)
                verkoop_ruw = row.get("Verkoopprijs (EUR, 0=auto)")
                verkoop = 0.0 if pd.isna(verkoop_ruw) else float(verkoop_ruw)
                if naam or inkoop > 0:
                    blok_custom_binnen.append({"merk_model": naam, "inkoop": inkoop, "verkoop": verkoop})
            if not blok_custom_binnen:
                st.warning("Voeg minstens één binnenunit toe aan de tabel hierboven.")

        pb1, pb2 = st.columns(2)
        with pb1:
            if blok_n == 1:
                blok_prijs_buiten = st.number_input("Inkoopprijs set (EUR)", min_value=0.0, value=0.0, step=10.0, key="a_blok_prijs_buiten")
                blok_prijs_buiten_verkoop = st.number_input("Verkoopprijs set (EUR, 0=auto)", min_value=0.0, value=0.0, step=10.0, key="a_blok_prijs_buiten_verkoop")
            else:
                blok_prijs_buiten = st.number_input("Inkoopprijs buitenunit (EUR)", min_value=0.0, value=0.0, step=10.0, key="a_blok_prijs_buiten")
                blok_prijs_buiten_verkoop = st.number_input("Verkoopprijs buitenunit (EUR, 0=auto)", min_value=0.0, value=0.0, step=10.0, key="a_blok_prijs_buiten_verkoop")
        with pb2:
            if blok_n > 1 and not blok_verschillende_binnen:
                blok_prijs_binnen = st.number_input("Inkoopprijs per binnenunit (EUR)", min_value=0.0, value=0.0, step=10.0, key="a_blok_prijs_binnen")
                blok_prijs_binnen_verkoop = st.number_input("Verkoopprijs per binnenunit (EUR, 0=auto)", min_value=0.0, value=0.0, step=10.0, key="a_blok_prijs_binnen_verkoop")
            else:
                blok_prijs_binnen, blok_prijs_binnen_verkoop = 0.0, 0.0

        blok_merk = st.text_input("Merk & model (op offerte)", key="a_blok_merk")

        if st.button("✅ Systeem toevoegen aan offerte", key="a_blok_add_btn"):
            if blok_prijs_buiten <= 0:
                st.error("Vul eerst een inkoopprijs voor de buitenunit in vóór je dit systeem toevoegt.")
            elif blok_n > 1 and blok_verschillende_binnen and not blok_custom_binnen:
                st.error("Voeg minstens één binnenunit toe aan de tabel.")
            elif blok_n > 1 and not blok_verschillende_binnen and blok_prijs_binnen <= 0:
                st.error("Vul ook een inkoopprijs voor de binnenunit in vóór je dit systeem toevoegt "
                         "(nu nog op € 0 — vergeten in te vullen of de catalogus-knop niet aangeklikt?).")
            else:
                nieuw_blok = dict(
                    naam=blok_naam or f"Systeem {len(st.session_state['a_blokken']) + 1}",
                    type="mono" if blok_n == 1 else "multi",
                    n_binnen=(len(blok_custom_binnen) if (blok_n > 1 and blok_verschillende_binnen) else blok_n),
                    aantal_systemen=int(blok_aantal),
                    merk_model=blok_merk, prijs_buiten=float(blok_prijs_buiten), prijs_buiten_verkoop=float(blok_prijs_buiten_verkoop),
                    prijs_binnen=float(blok_prijs_binnen), prijs_binnen_verkoop=float(blok_prijs_binnen_verkoop),
                )
                if blok_n > 1 and blok_verschillende_binnen:
                    nieuw_blok["custom_binnenunits"] = blok_custom_binnen
                st.session_state["a_blokken"].append(nieuw_blok)
                st.session_state["a_blok_binnen_df"] = pd.DataFrame({
                    "Merk & model": pd.Series(dtype="str"),
                    "Inkoopprijs (EUR)": pd.Series(dtype="float"),
                    "Verkoopprijs (EUR, 0=auto)": pd.Series(dtype="float"),
                })
                st.rerun()

    if st.session_state["a_blokken"]:
        st.markdown("**Toegevoegde systemen:**")
        for i, blok in enumerate(st.session_state["a_blokken"]):
            rcol1, rcol2 = st.columns([6, 1])
            with rcol1:
                typetxt = "Mono-split" if blok["type"] == "mono" else f"Multi-split ({blok['n_binnen']} binnenunits)"
                st.write(f"**{blok['naam']}** — {typetxt} × {blok['aantal_systemen']} — {blok.get('merk_model', '') or '(geen merk/model)'}")
            with rcol2:
                if st.button("🗑️ Verwijder", key=f"a_blok_del_btn_{i}"):
                    st.session_state["a_blokken"].pop(i)
                    st.rerun()
    else:
        st.warning("Nog geen systemen toegevoegd — voeg er hierboven minstens één toe.")

    blokken = st.session_state["a_blokken"]
    aantal_systemen = sum(b["aantal_systemen"] for b in blokken) if blokken else 0
    merk_model = " + ".join(b["naam"] for b in blokken) if blokken else ""

# ================= Gedeelde gegevens (gelden voor de volledige job) =================
st.subheader("Gedeelde gegevens" if gemengd else "Leidingwerk")
c5a, c5b = st.columns(2)
with c5a:
    leiding_m = st.number_input("Totale leidinglengte, alle systemen samen (m)", min_value=0.0, value=5.0, step=0.5, key="a_leiding")
    leiding_type_label = st.selectbox(
        "Type koelleiding",
        ["Geïsoleerd (bv. gasleiding)", "Niet-geïsoleerd (bv. vloeistofleiding)", "Combi"],
        key="a_leiding_type_label",
        help="Combi = 1 rol met een eigen prijs per meter (tussen geïsoleerd en niet-geïsoleerd "
             "in — instelbaar bij Prijsinstellingen), voor als je in de praktijk 1 gezamenlijke "
             "rol/product gebruikt in plaats van 2 aparte.")
    leiding_type = {"Geïsoleerd (bv. gasleiding)": "geisoleerd", "Niet-geïsoleerd (bv. vloeistofleiding)": "niet_geisoleerd",
                    "Combi": "combi"}[leiding_type_label]
    _rol_m = P.get("a_leiding_rol_m", 30.0)
    if leiding_m > 0:
        _aantal_rollen = math.ceil(leiding_m / _rol_m)
        st.caption(f"→ {leiding_m:g}m nodig ⇒ {_aantal_rollen} rol(len) van {_rol_m:g}m "
                  f"= {_aantal_rollen * _rol_m:.0f}m aangerekend.")
with c5b:
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
if not gemengd:
    inp = dict(n_binnen=n_binnen, aantal_systemen=aantal_systemen, mono_set=is_mono, custom_units=custom_units, merk_model=merk_model, prijs_buiten=prijs_buiten,
               prijs_buiten_verkoop=prijs_buiten_verkoop,
               prijs_binnen=prijs_binnen, prijs_binnen_verkoop=prijs_binnen_verkoop,
               leiding_m=leiding_m, leiding_type=leiding_type, goot_m=goot_m, goot_bij_klein=goot_bij_klein,
               doorvoeren=doorvoeren, koelmiddel_m=koelmiddel_m, condenspomp=condenspomp,
               console=console, elek=elek, hoogtewerker=hoogtewerker,
               techniekers=techniekers, uren_manueel=uren_manueel, km=km, btw=btw,
               arbeid_aanrekenen=arbeid_aanrekenen, dossier_aanrekenen=dossier_aanrekenen,
               korting_type=korting_type, korting_waarde=korting_waarde, korting_label=korting_label)
    res = bereken_airco(inp, P)
else:
    gedeeld = dict(leiding_m=leiding_m, leiding_type=leiding_type, goot_m=goot_m, goot_bij_klein=goot_bij_klein,
                   doorvoeren=doorvoeren, koelmiddel_m=koelmiddel_m, condenspomp=condenspomp,
                   console=console, elek=elek, hoogtewerker=hoogtewerker,
                   techniekers=techniekers, uren_manueel=uren_manueel, km=km, btw=btw,
                   arbeid_aanrekenen=arbeid_aanrekenen, dossier_aanrekenen=dossier_aanrekenen,
                   korting_type=korting_type, korting_waarde=korting_waarde, korting_label=korting_label)
    res = bereken_airco_gemengd(blokken, gedeeld, P)
    inp = gedeeld

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

if not gemengd:
    titel_suffix = f" — {aantal_systemen}x apart systeem" if aantal_systemen > 1 else ""
    titel = f"Airco-installatie — {type_label}{titel_suffix}"
else:
    titel = "Airco-installatie — Gemengde installatie" + (f" ({', '.join(b['naam'] for b in blokken)})" if blokken else "")

with b1:
    pdf_bytes = maak_pdf(titel, klant, res, inp, intro)
    st.download_button("📄 Download offerte (PDF)", data=pdf_bytes,
                       file_name=f"{klant['nummer']}_airco.pdf", mime="application/pdf",
                       use_container_width=True)

with b2:
    if st.button("💾 Project bewaren", use_container_width=True):
        if gemengd:
            st.session_state["a_blokken_json"] = json.dumps(st.session_state.get("a_blokken", []))
        if not gemengd and verschillende_toestellen:
            units_df = st.session_state.get("a_units_df")
            if units_df is not None and not units_df.empty:
                st.session_state["a_units_json"] = units_df.to_json(orient="records")
        # Knoppen (eindigen op _btn) en andere widget-interne/niet-scalaire status
        # mogen NOOIT herladen worden in st.session_state — dat geeft een Streamlit-fout.
        payload = {k.replace("a_", "", 1): v for k, v in st.session_state.items()
                   if k.startswith("a_") and "_btn" not in k
                   and isinstance(v, (str, int, float, bool))}
        payload["_type"] = "airco"
        try:
            pid = save_project("Airco", klantnaam or bedrijf, res["totaal"], payload,
                              mat_inkoop=res.get("mat_inkoop", 0), netto_winst=res.get("winst", 0))
        except TypeError:
            # Vangnet: als storage.py nog een oudere versie is (zonder mat_inkoop/netto_winst-
            # parameters), toch gewoon opslaan zonder die twee extra velden i.p.v. te crashen.
            pid = save_project("Airco", klantnaam or bedrijf, res["totaal"], payload)
        st.success(f"Bewaard als project {pid} — terug te vinden onder **Projecten**.")
