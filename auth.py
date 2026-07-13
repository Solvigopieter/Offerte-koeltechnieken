# auth.py
import streamlit as st

def _password_ok(pw: str) -> bool:
    secret = st.secrets.get("APP_PASSWORD", "")
    return isinstance(secret, str) and pw == secret

def require_login():
    if st.session_state.get("auth_ok"):
        return
    st.markdown("### 🔒 Beveiligde toegang — Solvigo Koeltechnieken")
    with st.form("login_form", clear_on_submit=False):
        pw = st.text_input("Wachtwoord", type="password")
        ok = st.form_submit_button("Inloggen")
    if ok:
        if _password_ok(pw):
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("Onjuist wachtwoord.")
            st.stop()
    else:
        st.stop()
