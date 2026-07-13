# pages/03_Projecten.py
import json

import streamlit as st

try:
    st.set_page_config(page_title="Projecten — Solvigo", layout="wide", page_icon="📁")
except Exception:
    pass

from auth import require_login
require_login()

from storage import load_projecten, delete_project

st.title("📁 Bewaarde projecten")

projecten = load_projecten()

if not projecten:
    st.info("Nog geen bewaarde projecten. Maak een offerte en klik op **Project bewaren**.")
    st.stop()

zoek = st.text_input("🔍 Zoek op klantnaam")
if zoek:
    projecten = [p for p in projecten if zoek.lower() in str(p.get("klant", "")).lower()]

for p in sorted(projecten, key=lambda x: str(x.get("id", "")), reverse=True):
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 1.2, 1.2])
        c1.markdown(f"**{p.get('klant', '')}**")
        c1.caption(p.get("datum", ""))
        c2.markdown(f"{'❄️ Airco' if p.get('type') == 'Airco' else '🔥 Warmtepomp'}")
        c3.markdown(f"**€ {float(p.get('totaal_incl', 0)):,.2f}".replace(",", " ") + "** incl. BTW")

        if c4.button("Openen", key=f"open_{p['id']}", use_container_width=True):
            try:
                payload = json.loads(p["payload"])
            except Exception:
                st.error("Kon dit project niet lezen.")
                st.stop()
            st.session_state["load_project"] = payload
            if payload.get("_type") == "airco":
                st.switch_page("pages/01_Airco Offerte.py")
            else:
                st.switch_page("pages/02_Warmtepomp Offerte.py")

        if c5.button("🗑️ Verwijderen", key=f"del_{p['id']}", use_container_width=True):
            delete_project(p["id"])
            st.rerun()
