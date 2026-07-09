# app.py — P&R Koeltechnieken Offertegenerator
import streamlit as st

st.set_page_config(page_title="P&R Koeltechnieken • Offertegenerator", layout="wide", page_icon="❄️")

from auth import require_login
require_login()

st.markdown("""
<style>
h1 span.orange{color:#f28c28;}
</style>
<h1>P<span class="orange">&</span>R Koeltechnieken — Offertegenerator</h1>
""", unsafe_allow_html=True)

st.markdown("""
Gebruik de **sidebar** links:

- ❄️ **Airco Offerte** — mono- en multi-split installaties
- 🔥 **Warmtepomp Offerte** — lucht-water warmtepompen
- 📁 **Projecten** — bewaarde offertes terug openen of verwijderen
- ⚙️ **Prijsinstellingen** — alle tarieven en materiaalprijzen aanpassen (geen code nodig)
""")

st.info("Prijzen aanpassen? Ga naar **Prijsinstellingen** — wijzigingen gelden meteen voor alle nieuwe offertes.")
