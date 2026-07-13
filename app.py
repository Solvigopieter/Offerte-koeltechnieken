# app.py — Solvigo Koeltechnieken Offertegenerator
import streamlit as st

st.set_page_config(page_title="Solvigo Koeltechnieken • Offertegenerator", layout="wide", page_icon="❄️")

from auth import require_login
require_login()

st.markdown("""
<style>
h1 span.gold{color:#c49000;}
</style>
<h1><span style="color:#1132d3;">Solvigo</span> <span class="gold">Koeltechnieken</span> — Offertegenerator</h1>
""", unsafe_allow_html=True)

st.markdown("""
Gebruik de **sidebar** links:

- ❄️ **Airco Offerte** — mono- en multi-split installaties
- 🔥 **Warmtepomp Offerte** — lucht-water warmtepompen
- 📁 **Projecten** — bewaarde offertes terug openen of verwijderen
- ⚙️ **Prijsinstellingen** — alle tarieven en materiaalprijzen aanpassen (geen code nodig)
""")

st.info("Prijzen aanpassen? Ga naar **Prijsinstellingen** — wijzigingen gelden meteen voor alle nieuwe offertes.")
