# storage.py — bewaart projecten en prijsinstellingen
# Werkt op 2 manieren:
#   1. Google Sheets (aanbevolen voor Streamlit Community Cloud) — zelfde gspread/service-account
#      opzet als de Solvigo CRM. Zet in Secrets: [gcp_service_account] blok + PR_SHEET_NAME.
#   2. Lokaal JSON-bestand (fallback, enkel voor lokaal testen — Community Cloud vergeet dit bij reboot).

import json
import os
from datetime import datetime

import streamlit as st

LOCAL_FILE = "pr_data.json"

PROJECT_HEADERS = ["id", "datum", "type", "klant", "totaal_incl", "payload"]


# ---------------------------------------------------------------- helpers
def _use_gsheets() -> bool:
    return "gcp_service_account" in st.secrets


@st.cache_resource
def _sheet():
    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=scopes
    )
    gc = gspread.authorize(creds)
    name = st.secrets.get("PR_SHEET_NAME", "PR Offertes")
    try:
        sh = gc.open(name)
    except gspread.SpreadsheetNotFound:
        sh = gc.create(name)
    return sh


def _ws(title: str, headers: list[str]):
    sh = _sheet()
    try:
        ws = sh.worksheet(title)
    except Exception:
        ws = sh.add_worksheet(title=title, rows=200, cols=len(headers) + 2)
        ws.append_row(headers)
    return ws


def _local_load() -> dict:
    if os.path.exists(LOCAL_FILE):
        with open(LOCAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"prijzen": {}, "projecten": []}


def _local_save(data: dict):
    with open(LOCAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------- prijzen
def load_prijzen(defaults: dict) -> dict:
    """Geeft opgeslagen prijzen terug, aangevuld met defaults voor nieuwe sleutels."""
    stored = {}
    if _use_gsheets():
        try:
            ws = _ws("Prijzen", ["key", "value"])
            for row in ws.get_all_records():
                stored[str(row["key"])] = row["value"]
        except Exception as e:
            st.warning(f"Kon prijzen niet laden uit Google Sheets: {e}")
    else:
        stored = _local_load().get("prijzen", {})

    out = dict(defaults)
    for k, v in stored.items():
        if k in out:
            try:
                out[k] = float(v)
            except (TypeError, ValueError):
                pass
    return out


def save_prijzen(prijzen: dict):
    if _use_gsheets():
        ws = _ws("Prijzen", ["key", "value"])
        ws.clear()
        ws.append_row(["key", "value"])
        rows = [[k, v] for k, v in prijzen.items()]
        if rows:
            ws.append_rows(rows)
    else:
        data = _local_load()
        data["prijzen"] = prijzen
        _local_save(data)


# ---------------------------------------------------------------- projecten
def save_project(ptype: str, klant: str, totaal_incl: float, payload: dict) -> str:
    pid = datetime.now().strftime("%Y%m%d-%H%M%S")
    rec = {
        "id": pid,
        "datum": datetime.now().strftime("%d-%m-%Y %H:%M"),
        "type": ptype,
        "klant": klant or "(naamloos)",
        "totaal_incl": round(totaal_incl, 2),
        "payload": json.dumps(payload, ensure_ascii=False),
    }
    if _use_gsheets():
        ws = _ws("Projecten", PROJECT_HEADERS)
        ws.append_row([rec[h] for h in PROJECT_HEADERS])
    else:
        data = _local_load()
        data.setdefault("projecten", []).append(rec)
        _local_save(data)
    return pid


def load_projecten() -> list[dict]:
    if _use_gsheets():
        try:
            ws = _ws("Projecten", PROJECT_HEADERS)
            return ws.get_all_records()
        except Exception as e:
            st.warning(f"Kon projecten niet laden: {e}")
            return []
    return _local_load().get("projecten", [])


def delete_project(pid: str):
    if _use_gsheets():
        ws = _ws("Projecten", PROJECT_HEADERS)
        cell = ws.find(str(pid))
        if cell:
            ws.delete_rows(cell.row)
    else:
        data = _local_load()
        data["projecten"] = [p for p in data.get("projecten", []) if str(p.get("id")) != str(pid)]
        _local_save(data)
