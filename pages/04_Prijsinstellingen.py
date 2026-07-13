# pages/04_Prijsinstellingen.py
import streamlit as st

try:
    st.set_page_config(page_title="Prijsinstellingen — Solvigo", layout="wide", page_icon="⚙️")
except Exception:
    pass

from auth import require_login
require_login()

from pr_core import DEFAULT_PRIJZEN, PRIJS_LABELS
from storage import load_prijzen, save_prijzen

st.title("⚙️ Prijsinstellingen")
st.markdown("Pas hier alle tarieven en materiaalprijzen aan. **Bewaren** onderaan — wijzigingen gelden meteen voor alle nieuwe offertes.")

# Sleutels die eigenlijk een aan/uit-schakelaar zijn (opgeslagen als 1.0 / 0.0)
BOOLEAN_KEYS = {"loonkost_meetellen"}

P = load_prijzen(DEFAULT_PRIJZEN)

st.checkbox(
    "💶 Interne loonkost aftrekken van de brutomarge",
    value=bool(P.get("loonkost_meetellen", 0.0)),
    key="p_loonkost_meetellen_cb",
    help="Zet AAN zodra je met personeel of een vennoot werkt en hun uren jou echt geld kosten. "
         "Zet UIT als je (nog) volledig solo werkt — dan trekt de marge-berekening geen loonkost af, "
         "want er is niemand om uit te betalen.",
)
st.divider()

GROEPEN = {
    "Algemeen (tarieven & marges)": [k for k in DEFAULT_PRIJZEN if not k.startswith(("a_", "w_")) and k not in BOOLEAN_KEYS],
    "Airco — materiaal": [k for k in DEFAULT_PRIJZEN if k.startswith("a_") and not k.startswith("a_uren")],
    "Airco — urenschatting": [k for k in DEFAULT_PRIJZEN if k.startswith("a_uren")],
    "Warmtepomp — materiaal": [k for k in DEFAULT_PRIJZEN if k.startswith("w_") and not k.startswith("w_uren")],
    "Warmtepomp — urenschatting": [k for k in DEFAULT_PRIJZEN if k.startswith("w_uren")],
}

nieuw = {"loonkost_meetellen": 1.0 if st.session_state["p_loonkost_meetellen_cb"] else 0.0}
for groep, keys in GROEPEN.items():
    with st.expander(groep, expanded=(groep.startswith("Algemeen"))):
        cols = st.columns(3)
        for i, k in enumerate(keys):
            with cols[i % 3]:
                nieuw[k] = st.number_input(PRIJS_LABELS.get(k, k), value=float(P[k]), step=0.5, key=f"p_{k}")

c1, c2 = st.columns([1, 1])
with c1:
    if st.button("💾 Prijzen bewaren", type="primary", use_container_width=True):
        save_prijzen(nieuw)
        st.success("Prijzen opgeslagen. Nieuwe offertes gebruiken deze waarden.")
with c2:
    if st.button("↩️ Terug naar fabrieksinstellingen", use_container_width=True):
        save_prijzen(dict(DEFAULT_PRIJZEN))
        st.rerun()
