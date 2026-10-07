# pages/05_Materialen.py — vaste materiaallijst met prijzen beheren
import streamlit as st

try:
    st.set_page_config(page_title="Materialen & prijzen — Solvigo", layout="wide", page_icon="📦")
except Exception:
    pass

from auth import require_login
require_login()

import pandas as pd

from materialen import DEFAULT_MATERIALEN, TOEPASSINGEN, categorieen, normaliseer
from pr_core import DEFAULT_PRIJZEN
from storage import load_materialen, load_prijzen, save_materialen

P = load_prijzen(DEFAULT_PRIJZEN)
marge = 1 + P["marge_materiaal_pct"] / 100.0

st.title("📦 Materialen & prijzen")
st.markdown(
    "Je vaste lijst met materiaal en prijzen. Wat je hier **bewaart**, onthoudt de app: op de offertepagina's "
    "vul je daarna enkel nog **aantallen** in.  \n"
    "• **Verkoop = 0** → automatisch inkoop × marge "
    f"({P['marge_materiaal_pct']:g}%, instelbaar bij Prijsinstellingen).  \n"
    "• **Verpakking** → 0 = per stuk/meter aanrekenen; bv. 30 = altijd per volle rol van 30 m.  \n"
    "• **Actief uit** → artikel verbergen op de offertes zonder het te verwijderen.  \n"
    "• Nieuw artikel: onderaan de tabel een rij toevoegen (id mag je leeg laten)."
)

if "mb_bericht" in st.session_state:
    st.success(st.session_state.pop("mb_bericht"))

materialen = load_materialen()

KOLOMMEN = {
    "id": "id", "actief": "Actief", "toepassing": "Toepassing", "categorie": "Categorie",
    "artikel": "Artikel", "eenheid": "Eenheid", "verpakking": "Verpakking",
    "inkoop": "Inkoop (€)", "verkoop": "Verkoop (€, 0=auto)",
}
TERUG = {v: k for k, v in KOLOMMEN.items()}

df = pd.DataFrame(materialen, columns=list(KOLOMMEN.keys())).rename(columns=KOLOMMEN)

# ---- filters (enkel weergave — bewaren werkt altijd op de volledige lijst)
f1, f2, f3 = st.columns([1.2, 2, 2])
with f1:
    f_toep = st.selectbox("Toepassing", ["Alle"] + TOEPASSINGEN, key="mb_f_toep")
with f2:
    f_cat = st.selectbox("Categorie", ["Alle"] + categorieen(materialen), key="mb_f_cat")
with f3:
    f_zoek = st.text_input("🔍 Zoek artikel", key="mb_f_zoek")

masker = pd.Series(True, index=df.index)
if f_toep != "Alle":
    masker &= df["Toepassing"] == f_toep
if f_cat != "Alle":
    masker &= df["Categorie"] == f_cat
if f_zoek:
    masker &= df["Artikel"].str.contains(f_zoek, case=False, na=False)
gefilterd = bool(f_toep != "Alle" or f_cat != "Alle" or f_zoek)

zicht = df[masker].copy()
zicht.insert(len(zicht.columns), "Verkoop berekend (€)",
             [round(v if v > 0 else i * marge, 2) for i, v in zip(zicht["Inkoop (€)"], zicht["Verkoop (€, 0=auto)"])])

bewerkt = st.data_editor(
    zicht,
    key=f"mb_editor_{f_toep}_{f_cat}_{f_zoek}",
    num_rows="dynamic",
    hide_index=True,
    use_container_width=True,
    height=min(38 * (len(zicht) + 2), 700),
    disabled=["id", "Verkoop berekend (€)"],
    column_config={
        "id": st.column_config.TextColumn(width="small", help="Wordt automatisch ingevuld"),
        "Actief": st.column_config.CheckboxColumn(default=True, width="small"),
        "Toepassing": st.column_config.SelectboxColumn(options=TOEPASSINGEN, default="Beide", required=True),
        "Categorie": st.column_config.TextColumn(help="Bestaande of nieuwe categorie, bv. 'Leidinggoot'"),
        "Artikel": st.column_config.TextColumn(width="large", required=True),
        "Eenheid": st.column_config.TextColumn(width="small", default="st"),
        "Verpakking": st.column_config.NumberColumn(min_value=0.0, step=1.0, format="%g", default=0.0,
                                                    help="0 = per eenheid; bv. 30 = per volle rol van 30 m"),
        "Inkoop (€)": st.column_config.NumberColumn(min_value=0.0, step=0.1, format="%.2f", default=0.0),
        "Verkoop (€, 0=auto)": st.column_config.NumberColumn(min_value=0.0, step=0.1, format="%.2f", default=0.0),
        "Verkoop berekend (€)": st.column_config.NumberColumn(format="%.2f",
                                                             help="Wat er effectief op de offerte komt (wordt bijgewerkt na bewaren)"),
    },
)

if gefilterd:
    st.caption("Filter actief: je ziet maar een deel van de lijst. Bij bewaren blijven de verborgen artikels gewoon behouden.")


def _samenvoegen() -> list[dict]:
    """Bewerkte (gefilterde) rijen + alle rijen die buiten de filter vielen."""
    nieuw = bewerkt.drop(columns=["Verkoop berekend (€)"]).rename(columns=TERUG).to_dict("records")
    zichtbare_ids = set(zicht["id"].astype(str))
    buiten_filter = [m for m in materialen if str(m["id"]) not in zichtbare_ids]
    # originele volgorde behouden: eerst de bestaande lijst, nieuwe rijen achteraan
    bewerkt_per_id = {str(r.get("id")): r for r in nieuw if r.get("id") and str(r.get("id")) != "nan"}
    resultaat = []
    for m in materialen:
        mid = str(m["id"])
        if mid in zichtbare_ids:
            if mid in bewerkt_per_id:          # niet verwijderd
                resultaat.append(bewerkt_per_id[mid])
        else:
            resultaat.append(m)
    resultaat += [r for r in nieuw if not r.get("id") or str(r.get("id")) == "nan"]
    return resultaat


c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    if st.button("💾 Materiaallijst bewaren", type="primary", use_container_width=True):
        lijst = normaliseer(_samenvoegen())
        try:
            save_materialen(lijst)
            # tabelstatus wissen, anders worden toegevoegde rijen na de herlaadbeurt dubbel getoond
            for k in [k for k in st.session_state if k.startswith("mb_editor_")]:
                st.session_state.pop(k, None)
            st.session_state["mb_bericht"] = f"Bewaard — {len(lijst)} artikels. Nieuwe offertes gebruiken meteen deze prijzen."
            st.rerun()
        except Exception as e:
            st.error(f"Bewaren mislukt: {e}")
with c2:
    st.download_button("⬇️ Exporteer als CSV", use_container_width=True,
                       data=df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
                       file_name="materiaallijst.csv", mime="text/csv")
with c3:
    with st.popover("↩️ Startlijst terugzetten", use_container_width=True):
        st.warning("Dit vervangt je volledige materiaallijst door de standaard startlijst. Je eigen prijzen gaan verloren.")
        if st.button("Ja, startlijst terugzetten", key="mb_reset_btn"):
            save_materialen([dict(m) for m in DEFAULT_MATERIALEN])
            for k in [k for k in st.session_state if k.startswith("mb_editor_")]:
                st.session_state.pop(k, None)
            st.session_state["mb_bericht"] = "Startlijst teruggezet."
            st.rerun()

st.divider()
st.caption("Tip: je kan de lijst ook rechtstreeks aanpassen in Google Sheets, tabblad **Materialen** "
           "(de app leest wijzigingen binnen 5 minuten in, of meteen na een herstart). "
           "Laat de kolom **id** ongemoeid: bewaarde offertes verwijzen ernaar.")
