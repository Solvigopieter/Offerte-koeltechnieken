"""
crm_koppeling.py — Rechtstreeks een offerte naar de Solvigo Koeltechnieken CRM sturen.

Schrijft, met hetzelfde service account als de offerte-sheet zelf, rechtstreeks
een organisatie + deal + offerte weg naar de CRM's eigen Google Sheet — zodat
"Verstuur naar CRM" meteen in de Pipeline verschijnt, zonder dat je nog naar
het CRM zelf moet gaan om te importeren.

Vereist in Streamlit secrets (naast wat de offertegenerator al gebruikt):
    crm_sheet_id = "ID_VAN_DE_KOELTECHNIEKEN_CRM_SHEET"
"""
from __future__ import annotations

import time

import streamlit as st

# Kolomstructuur MOET exact overeenkomen met db.TABEL_KOLOMMEN in het CRM zelf,
# anders schuiven waarden naar de verkeerde kolom. Bij een schema-wijziging in
# het CRM moet dit hier manueel mee bijgewerkt worden.
ORG_KOLOMMEN = [
    "id", "naam", "type", "btw", "adres", "gemeente", "sector", "website",
    "status", "relatietype", "notities", "aangemaakt",
    "klantnummer", "email", "telefoon",
]
DEAL_KOLOMMEN = [
    "id", "titel", "type_installatie", "organisatie_id", "partner_id",
    "installatie_id", "contact_id", "waarde", "kans", "bron", "deadline",
    "verantwoordelijke", "stadium", "prioriteit", "aangemaakt", "gewijzigd",
]
OFFERTE_KOLOMMEN = [
    "id", "deal_id", "installatie_id", "nummer", "type", "totaalprijs",
    "btw_tarief", "status", "datum", "opmerkingen", "bron", "generator_id",
    "pdf_bestandsnaam", "materiaalkost", "nettowinst",
]


def crm_koppeling_beschikbaar() -> bool:
    try:
        return "gcp_service_account" in st.secrets and bool(st.secrets.get("crm_sheet_id"))
    except Exception:
        return False


def _met_retry(functie, *args, pogingen: int = 4, **kwargs):
    """Herprobeert bij tijdelijke Google Sheets-fouten (bv. rate limit)."""
    laatste_fout = None
    for poging in range(pogingen):
        try:
            return functie(*args, **kwargs)
        except Exception as e:
            laatste_fout = e
            tekst = (type(e).__name__ + " " + str(e)).lower()
            tijdelijk = ("apierror" in tekst or "429" in tekst or "rate" in tekst
                        or "quota" in tekst or "timeout" in tekst or "503" in tekst)
            if not tijdelijk or poging == pogingen - 1:
                raise
            time.sleep(1.5 * (2 ** poging))
    raise laatste_fout


@st.cache_resource
def _crm_sheet():
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
    return gc.open_by_key(str(st.secrets["crm_sheet_id"]))


def _ws(titel: str, kolommen: list[str]):
    sh = _crm_sheet()
    try:
        ws = sh.worksheet(titel)
    except Exception:
        ws = sh.add_worksheet(title=titel, rows=1000, cols=max(20, len(kolommen)))
        _met_retry(ws.update, values=[kolommen], range_name="A1")
    return ws


def _als_sheet_waarde(waarde):
    """Zelfde bescherming als in het CRM zelf: getallen met decimalen worden
    als forced-text (apostrof-voorvoegsel) weggeschreven, anders kan Google
    Sheets (Belgische locale) een kommagetal verkeerd interpreteren."""
    if waarde is None:
        return ""
    if isinstance(waarde, bool):
        return int(waarde)
    if isinstance(waarde, float):
        return f"'{waarde:.2f}"
    return waarde


def _volgend_id(ws, kolommen) -> int:
    records = _met_retry(ws.get_all_records, expected_headers=kolommen)
    ids = []
    for r in records:
        try:
            ids.append(int(r.get("id") or 0))
        except (TypeError, ValueError):
            continue
    return (max(ids) + 1) if ids else 1


def _volgend_klantnummer(org_ws) -> str:
    records = _met_retry(org_ws.get_all_records, expected_headers=ORG_KOLOMMEN)
    hoogste = 0
    for r in records:
        waarde = str(r.get("klantnummer") or "")
        if waarde.upper().startswith("AC") and waarde[2:].isdigit():
            hoogste = max(hoogste, int(waarde[2:]))
    return f"AC{hoogste + 1:04d}"


def _vind_organisatie(org_ws, naam: str):
    records = _met_retry(org_ws.get_all_records, expected_headers=ORG_KOLOMMEN)
    for r in records:
        if str(r.get("naam") or "").strip().lower() == naam.strip().lower():
            try:
                return int(r.get("id"))
            except (TypeError, ValueError):
                continue
    return None


def verstuur_naar_crm(klantnaam: str, adres: str, email: str, tel: str,
                       offerte_type: str, totaal: float, mat_inkoop: float,
                       winst: float, offertenummer: str, btw_tarief: str) -> dict:
    """Maakt (of hergebruikt) een organisatie, en maakt daar een deal + offerte
    voor aan in de CRM-sheet. Geeft een dict terug met info voor de succesmelding."""
    klantnaam = (klantnaam or "").strip() or "(naamloos)"

    org_ws = _ws("organisaties", ORG_KOLOMMEN)
    org_id = _vind_organisatie(org_ws, klantnaam)
    hergebruikt = org_id is not None
    if org_id is None:
        org_id = _volgend_id(org_ws, ORG_KOLOMMEN)
        klantnummer = _volgend_klantnummer(org_ws)
        rij = {
            "id": org_id, "naam": klantnaam, "type": "Eindklant", "btw": "",
            "adres": adres or "", "gemeente": "", "sector": "", "website": "",
            "status": "Actief", "relatietype": "Eenmalige klant", "notities": "",
            "aangemaakt": "", "klantnummer": klantnummer,
            "email": email or "", "telefoon": tel or "",
        }
        waarden = [_als_sheet_waarde(rij.get(k, "")) for k in ORG_KOLOMMEN]
        _met_retry(org_ws.append_row, waarden, value_input_option="USER_ENTERED")
    else:
        klantnummer = None

    deal_ws = _ws("deals", DEAL_KOLOMMEN)
    deal_id = _volgend_id(deal_ws, DEAL_KOLOMMEN)
    deal_rij = {
        "id": deal_id, "titel": f"{offerte_type} — {klantnaam}",
        "type_installatie": offerte_type, "organisatie_id": org_id,
        "partner_id": "", "installatie_id": "", "contact_id": "",
        "waarde": float(totaal), "kans": 70, "bron": "Offertegenerator",
        "deadline": "", "verantwoordelijke": "", "stadium": "Offerte verstuurd",
        "prioriteit": "Normaal", "aangemaakt": "", "gewijzigd": "",
    }
    waarden = [_als_sheet_waarde(deal_rij.get(k, "")) for k in DEAL_KOLOMMEN]
    _met_retry(deal_ws.append_row, waarden, value_input_option="USER_ENTERED")

    offerte_ws = _ws("offertes", OFFERTE_KOLOMMEN)
    offerte_id = _volgend_id(offerte_ws, OFFERTE_KOLOMMEN)
    offerte_rij = {
        "id": offerte_id, "deal_id": deal_id, "installatie_id": "",
        "nummer": offertenummer, "type": offerte_type, "totaalprijs": float(totaal),
        "btw_tarief": btw_tarief, "status": "Verstuurd", "datum": "",
        "opmerkingen": f"Rechtstreeks verstuurd vanuit de offertegenerator (klant: {klantnaam})",
        "bron": "Generator", "generator_id": "", "pdf_bestandsnaam": "",
        "materiaalkost": float(mat_inkoop or 0), "nettowinst": float(winst or 0),
    }
    waarden = [_als_sheet_waarde(offerte_rij.get(k, "")) for k in OFFERTE_KOLOMMEN]
    _met_retry(offerte_ws.append_row, waarden, value_input_option="USER_ENTERED")

    return {
        "klantnaam": klantnaam, "klantnummer": klantnummer,
        "organisatie_hergebruikt": hergebruikt, "deal_id": deal_id,
        "offerte_id": offerte_id,
    }
