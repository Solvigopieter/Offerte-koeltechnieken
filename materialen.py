# materialen.py — vaste materiaallijst (artikels + prijzen) en de materiaalkeuze op de offertepagina's
#
# De lijst zelf wordt bewaard in de Google Sheet (tabblad "Materialen"), zodat je
# prijzen maar één keer moet invullen. Beheer: pagina "📦 Materialen & prijzen"
# in de app, of rechtstreeks in het tabblad in Google Sheets.
#
# Kolommen per artikel:
#   id          vaste code (bv. M010) — niet aanpassen, hieraan hangen bewaarde offertes
#   actief      ja/nee — "nee" = verborgen op de offertepagina's, maar niet verwijderd
#   toepassing  Airco / Warmtepomp / Beide — op welke offertepagina het artikel verschijnt
#   categorie   groepering op het scherm (en op de PDF bij "per categorie")
#   artikel     omschrijving zoals op de offerte
#   eenheid     m, st, set, kg, ...
#   verpakking  0 = per eenheid aanrekenen; >0 = afronden naar volle verpakking
#               (bv. 30 bij koperleiding: 12 m nodig => 30 m aangerekend)
#   inkoop      inkoopprijs per eenheid (EUR excl. BTW)
#   verkoop     verkoopprijs per eenheid (EUR excl. BTW), 0 = automatisch inkoop x marge%

from __future__ import annotations

import json
import math

import pandas as pd
import streamlit as st

MAT_HEADERS = ["id", "actief", "toepassing", "categorie", "artikel", "eenheid", "verpakking", "inkoop", "verkoop"]

TOEPASSINGEN = ["Airco", "Warmtepomp", "Beide"]

# Volgorde waarin de categorieën op het scherm verschijnen (nieuwe categorieën komen achteraan)
CATEGORIE_VOLGORDE = [
    "Koelleiding",
    "Leidinggoot",
    "Elektrische kabelgoot",
    "Elektriciteit",
    "Condensafvoer",
    "Bevestiging",
    "Koelmiddel",
    "Hydraulica",
    "Klein materiaal",
]

# STARTWAARDEN — prijzen zijn schattingen, pas ze aan naar je eigen inkoopprijzen.
# (koperleiding, sierlijst, condenspomp en console komen uit je bestaande Prijsinstellingen)
_D = [
    # id,     toepassing,   categorie,               artikel,                                         eenheid, verp, inkoop
    ("M001", "Airco",      "Koelleiding",           "Koperleiding geïsoleerd",                        "m",   30, 5.90),
    ("M002", "Airco",      "Koelleiding",           "Koperleiding niet-geïsoleerd",                   "m",   30, 4.70),
    ("M003", "Airco",      "Koelleiding",           "Koperleiding combi",                             "m",   30, 5.30),
    ("M004", "Airco",      "Koelleiding",           "Flare-moeren / koppelstukken (set)",             "set",  0, 6.00),
    ("M005", "Airco",      "Koelleiding",           "Isolatiebuis (Armaflex) los",                    "m",    0, 2.50),

    ("M010", "Airco",      "Leidinggoot",           "Leidinggoot / sierlijst 80 mm",                  "m",    2, 22.00),
    ("M011", "Airco",      "Leidinggoot",           "Leidinggoot / sierlijst 60 mm",                  "m",    2, 16.00),
    ("M012", "Airco",      "Leidinggoot",           "Leidinggoot vlakke bocht 90°",                   "st",   0, 7.00),
    ("M013", "Airco",      "Leidinggoot",           "Leidinggoot binnenhoek",                         "st",   0, 6.00),
    ("M014", "Airco",      "Leidinggoot",           "Leidinggoot buitenhoek",                         "st",   0, 6.00),
    ("M015", "Airco",      "Leidinggoot",           "Leidinggoot T-stuk",                             "st",   0, 9.00),
    ("M016", "Airco",      "Leidinggoot",           "Leidinggoot flexibele bocht",                    "st",   0, 12.00),
    ("M017", "Airco",      "Leidinggoot",           "Leidinggoot wandaansluiting / muurdoorvoer",     "st",   0, 5.00),
    ("M018", "Airco",      "Leidinggoot",           "Leidinggoot eindstuk",                           "st",   0, 4.00),
    ("M019", "Airco",      "Leidinggoot",           "Leidinggoot koppelstuk",                         "st",   0, 2.50),

    ("M020", "Beide",      "Elektrische kabelgoot", "Kabelgoot 25x16 mm",                             "m",    2, 2.50),
    ("M021", "Beide",      "Elektrische kabelgoot", "Kabelgoot 40x25 mm",                             "m",    2, 3.50),
    ("M022", "Beide",      "Elektrische kabelgoot", "Kabelgoot hoekstuk",                             "st",   0, 1.20),
    ("M023", "Beide",      "Elektrische kabelgoot", "Kabelgoot T-stuk",                               "st",   0, 1.50),
    ("M024", "Beide",      "Elektrische kabelgoot", "Kabelgoot eindstuk",                             "st",   0, 0.80),

    ("M030", "Beide",      "Elektriciteit",         "Voedingskabel XVB 3G2,5",                        "m",    0, 1.80),
    ("M031", "Airco",      "Elektriciteit",         "Verbindingskabel binnen-buiten H07RN-F 4G1,5",   "m",    0, 2.20),
    ("M032", "Beide",      "Elektriciteit",         "Automaat 16A 2P",                                "st",   0, 12.00),
    ("M033", "Beide",      "Elektriciteit",         "Werkschakelaar buiten (IP65)",                   "st",   0, 18.00),
    ("M034", "Beide",      "Elektriciteit",         "Wartels / kabelklemmen (set)",                   "set",  0, 4.00),

    ("M040", "Airco",      "Condensafvoer",         "Condensslang 16 mm",                             "m",    0, 1.20),
    ("M041", "Beide",      "Condensafvoer",         "PVC-afvoerbuis 32 mm",                           "m",    0, 3.00),
    ("M042", "Beide",      "Condensafvoer",         "PVC-bocht 32 mm",                                "st",   0, 1.20),
    ("M043", "Airco",      "Condensafvoer",         "Condenspomp",                                    "st",   0, 140.00),
    ("M044", "Airco",      "Condensafvoer",         "Sifon / reukafsluiter condensafvoer",            "st",   0, 8.00),

    ("M050", "Airco",      "Bevestiging",           "Muurconsole buitenunit + trillingsdempers",      "st",   0, 65.00),
    ("M051", "Beide",      "Bevestiging",           "Vloerconsole / grondsteun buitenunit",           "st",   0, 45.00),
    ("M052", "Beide",      "Bevestiging",           "Rubber trillingsdempers (set)",                  "set",  0, 15.00),
    ("M053", "Airco",      "Bevestiging",           "Dakconsole",                                     "st",   0, 90.00),

    ("M060", "Airco",      "Koelmiddel",            "Extra koelmiddel R32",                           "kg",   0, 30.00),

    ("M070", "Warmtepomp", "Hydraulica",            "Meerlagenbuis 26 mm",                            "m",    0, 6.00),
    ("M071", "Warmtepomp", "Hydraulica",            "Kogelkraan 1\"",                                 "st",   0, 15.00),
    ("M072", "Warmtepomp", "Hydraulica",            "Flexibele aansluitslangen 1\" (set)",            "set",  0, 40.00),
    ("M073", "Warmtepomp", "Hydraulica",            "Expansievat 18 L",                               "st",   0, 45.00),
    ("M074", "Warmtepomp", "Hydraulica",            "Magnetietfilter",                                "st",   0, 85.00),

    ("M080", "Beide",      "Klein materiaal",       "Pluggen & schroeven (set)",                      "set",  0, 5.00),
    ("M081", "Beide",      "Klein materiaal",       "Isolatietape",                                   "rol",  0, 3.00),
    ("M082", "Beide",      "Klein materiaal",       "Kit / siliconen",                                "st",   0, 6.00),
    ("M083", "Beide",      "Klein materiaal",       "Kabelbinders / klein bevestigingsmateriaal",     "set",  0, 4.00),
]

DEFAULT_MATERIALEN = [
    {"id": i, "actief": True, "toepassing": t, "categorie": c, "artikel": a,
     "eenheid": e, "verpakking": float(v), "inkoop": float(p), "verkoop": 0.0}
    for (i, t, c, a, e, v, p) in _D
]


# ---------------------------------------------------------------- normaliseren
def _getal(x) -> float:
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return 0.0 if (isinstance(x, float) and math.isnan(x)) else float(x)
    tekst = str(x).strip().lstrip("'").replace("€", "").strip()
    if not tekst:
        return 0.0
    try:
        return float(tekst)
    except ValueError:
        pass
    try:  # Belgische notatie 1.234,56
        return float(tekst.replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0


def _ja(x) -> bool:
    if isinstance(x, bool):
        return x
    return str(x).strip().lower() not in ("nee", "no", "false", "0", "uit")


def normaliseer(rijen: list[dict]) -> list[dict]:
    """Maakt een lijst artikels proper: juiste types, unieke id's, lege rijen weg."""
    out, gezien = [], set()
    volgnr = 1 + max([int(str(r.get("id", ""))[1:]) for r in rijen
                      if str(r.get("id", "")).startswith("M") and str(r.get("id", ""))[1:].isdigit()] or [0])
    for r in rijen:
        artikel = str(r.get("artikel") or "").strip()
        if not artikel or artikel.lower() == "nan":
            continue
        mid = str(r.get("id") or "").strip()
        if not mid or mid.lower() == "nan" or mid in gezien:
            mid = f"M{volgnr:03d}"
            volgnr += 1
        gezien.add(mid)
        toep = str(r.get("toepassing") or "Beide").strip()
        out.append({
            "id": mid,
            "actief": _ja(r.get("actief", True)),
            "toepassing": toep if toep in TOEPASSINGEN else "Beide",
            "categorie": (str(r.get("categorie") or "").strip() or "Overig"),
            "artikel": artikel,
            "eenheid": (str(r.get("eenheid") or "").strip() or "st"),
            "verpakking": max(0.0, _getal(r.get("verpakking"))),
            "inkoop": max(0.0, _getal(r.get("inkoop"))),
            "verkoop": max(0.0, _getal(r.get("verkoop"))),
        })
    return out


def categorieen(materialen: list[dict]) -> list[str]:
    aanwezig = []
    for m in materialen:
        if m["categorie"] not in aanwezig:
            aanwezig.append(m["categorie"])
    vast = [c for c in CATEGORIE_VOLGORDE if c in aanwezig]
    return vast + [c for c in aanwezig if c not in vast]


# ---------------------------------------------------------------- berekening per lijn
def aangerekende_hoeveelheid(aantal: float, verpakking: float) -> float:
    """Rondt af naar volle verpakking als die ingesteld is (bv. rol van 30 m)."""
    if aantal <= 0:
        return 0.0
    if verpakking and verpakking > 0:
        return math.ceil(round(aantal / verpakking, 6)) * verpakking
    return aantal


# ---------------------------------------------------------------- UI op de offertepagina
_EXTRA_KOLOMMEN = ["Omschrijving", "Categorie", "Eenheid", "Aantal", "Inkoop/eenheid", "Verkoop/eenheid (0=auto)"]


def _leeg_extra_df() -> pd.DataFrame:
    return pd.DataFrame({
        "Omschrijving": pd.Series(dtype="str"),
        "Categorie": pd.Series(dtype="str"),
        "Eenheid": pd.Series(dtype="str"),
        "Aantal": pd.Series(dtype="float"),
        "Inkoop/eenheid": pd.Series(dtype="float"),
        "Verkoop/eenheid (0=auto)": pd.Series(dtype="float"),
    })


def reset_keuze(prefix: str):
    """Wist de interne tabelstatus zodat de materiaalkeuze opnieuw opgebouwd wordt
    (na het laden van een project)."""
    for k in list(st.session_state.keys()):
        if k.startswith(f"_{prefix}_matbase_") or k.startswith(f"{prefix}_mated_") \
                or k in (f"_{prefix}_extra_base", f"{prefix}_matextra_ed"):
            st.session_state.pop(k, None)


def laad_keuze_uit_json(prefix: str, tekst: str):
    """Zet een bewaarde materiaalkeuze (JSON-tekst) terug in de sessie."""
    try:
        data = json.loads(tekst) if tekst else {}
    except Exception:
        data = {}
    st.session_state[f"{prefix}_mat_aantallen"] = {str(k): float(v) for k, v in (data.get("aantallen") or {}).items()}
    st.session_state[f"{prefix}_mat_extra"] = list(data.get("extra") or [])
    reset_keuze(prefix)


def keuze_als_json(prefix: str) -> str:
    return json.dumps({
        "aantallen": {k: v for k, v in st.session_state.get(f"{prefix}_mat_aantallen", {}).items() if v},
        "extra": st.session_state.get(f"{prefix}_mat_extra", []),
    }, ensure_ascii=False)


def materiaal_keuze_ui(prefix: str, toepassing: str, materialen: list[dict], marge: float) -> list[dict]:
    """Toont per categorie een tabel waarin je enkel het aantal invult.
    Geeft de gekozen lijnen terug als lijst dicts voor de berekening."""
    aantallen: dict = st.session_state.setdefault(f"{prefix}_mat_aantallen", {})
    lijst = [m for m in materialen if m["actief"] and m["toepassing"] in (toepassing, "Beide")]
    cats = categorieen(lijst)

    gekozen: list[dict] = []
    # Vaste tabnamen (zonder tellers): als de naam verandert, springt Streamlit terug naar de eerste tab.
    tabs = st.tabs(cats + ["➕ Ander materiaal"])

    for ci, (cat, tab) in enumerate(zip(cats, tabs)):
        items = [m for m in lijst if m["categorie"] == cat]
        handtekening = tuple((m["id"], m["artikel"], m["eenheid"], m["inkoop"], m["verkoop"], m["verpakking"]) for m in items)
        base_key = f"_{prefix}_matbase_{ci}"
        ed_key = f"{prefix}_mated_{ci}"
        if st.session_state.get(base_key, {}).get("sig") != handtekening:
            st.session_state[base_key] = {
                "sig": handtekening,
                "df": pd.DataFrame([{
                    "id": m["id"],
                    "Artikel": m["artikel"],
                    "Eenheid": m["eenheid"] + (f" (per {m['verpakking']:g})" if m["verpakking"] else ""),
                    "Prijs/eenheid": round(m["verkoop"] if m["verkoop"] > 0 else m["inkoop"] * marge, 2),
                    "Aantal": float(aantallen.get(m["id"], 0.0)),
                } for m in items]),
            }
            st.session_state.pop(ed_key, None)
        with tab:
            edited = st.data_editor(
                st.session_state[base_key]["df"], key=ed_key, hide_index=True, use_container_width=True,
                disabled=["id", "Artikel", "Eenheid", "Prijs/eenheid"],
                column_order=["Artikel", "Eenheid", "Prijs/eenheid", "Aantal"],
                column_config={
                    "Prijs/eenheid": st.column_config.NumberColumn("Verkoop/eenheid (€)", format="%.2f"),
                    "Aantal": st.column_config.NumberColumn(min_value=0.0, step=0.5, format="%g"),
                },
            )
            for _, r in edited.iterrows():
                a = _getal(r["Aantal"])
                if a > 0:
                    aantallen[r["id"]] = a
                else:
                    aantallen.pop(r["id"], None)

    for m in lijst:
        a = aantallen.get(m["id"], 0.0)
        if a > 0:
            gekozen.append({"id": m["id"], "categorie": m["categorie"], "artikel": m["artikel"],
                            "eenheid": m["eenheid"], "aantal": a, "verpakking": m["verpakking"],
                            "inkoop": m["inkoop"], "verkoop": m["verkoop"]})

    # ---- vrije lijnen (eenmalig materiaal dat niet in de lijst staat)
    with tabs[-1]:
        st.caption("Voor eenmalig materiaal dat niet in je vaste lijst staat. Vaak nodig? "
                   "Zet het dan bij **📦 Materialen & prijzen**, dan moet je de prijs maar één keer invullen.")
        extra_base = f"_{prefix}_extra_base"
        if extra_base not in st.session_state:
            rijen = st.session_state.get(f"{prefix}_mat_extra", [])
            st.session_state[extra_base] = pd.DataFrame(rijen, columns=_EXTRA_KOLOMMEN) if rijen else _leeg_extra_df()
        extra_df = st.data_editor(
            st.session_state[extra_base], key=f"{prefix}_matextra_ed", num_rows="dynamic",
            hide_index=True, use_container_width=True,
            column_config={
                "Aantal": st.column_config.NumberColumn(min_value=0.0, step=0.5, format="%g"),
                "Inkoop/eenheid": st.column_config.NumberColumn(min_value=0.0, step=0.5, format="%.2f"),
                "Verkoop/eenheid (0=auto)": st.column_config.NumberColumn(min_value=0.0, step=0.5, format="%.2f"),
            },
        )
        extra_rijen = []
        for _, r in extra_df.iterrows():
            om = "" if pd.isna(r.get("Omschrijving")) else str(r.get("Omschrijving")).strip()
            a = _getal(r.get("Aantal"))
            if not om or a <= 0:
                continue
            rij = {
                "Omschrijving": om,
                "Categorie": ("" if pd.isna(r.get("Categorie")) else str(r.get("Categorie")).strip()) or "Overig",
                "Eenheid": ("" if pd.isna(r.get("Eenheid")) else str(r.get("Eenheid")).strip()) or "st",
                "Aantal": a,
                "Inkoop/eenheid": _getal(r.get("Inkoop/eenheid")),
                "Verkoop/eenheid (0=auto)": _getal(r.get("Verkoop/eenheid (0=auto)")),
            }
            extra_rijen.append(rij)
            gekozen.append({"id": "", "categorie": rij["Categorie"], "artikel": om, "eenheid": rij["Eenheid"],
                            "aantal": a, "verpakking": 0.0, "inkoop": rij["Inkoop/eenheid"],
                            "verkoop": rij["Verkoop/eenheid (0=auto)"]})
        st.session_state[f"{prefix}_mat_extra"] = extra_rijen

    # ---- samenvatting van wat gekozen is
    if gekozen:
        samenvatting = []
        for g in gekozen:
            aangerekend = aangerekende_hoeveelheid(g["aantal"], g["verpakking"])
            vk = g["verkoop"] if g["verkoop"] > 0 else g["inkoop"] * marge
            opm = f"{g['aantal']:g} nodig → {aangerekend:g} aangerekend" if aangerekend != g["aantal"] else ""
            samenvatting.append({"Categorie": g["categorie"], "Artikel": g["artikel"],
                                 "Aantal": f"{aangerekend:g} {g['eenheid']}", "Opmerking": opm,
                                 "Inkoop (€)": round(aangerekend * g["inkoop"], 2),
                                 "Verkoop (€)": round(aangerekend * vk, 2)})
        sdf = pd.DataFrame(samenvatting)
        totaal_txt = f"{sdf['Verkoop (€)'].sum():,.2f}".replace(",", " ")
        with st.expander(f"📋 Gekozen materiaal — {len(gekozen)} lijn(en), verkoop € {totaal_txt}", expanded=False):
            st.dataframe(sdf, hide_index=True, use_container_width=True)
            per_cat = sdf.groupby("Categorie", sort=False)[["Inkoop (€)", "Verkoop (€)"]].sum().reset_index()
            st.dataframe(per_cat, hide_index=True, use_container_width=True)
        if st.button("🧹 Alle materiaalaantallen wissen", key=f"{prefix}_mat_wis_btn"):
            st.session_state[f"{prefix}_mat_aantallen"] = {}
            st.session_state[f"{prefix}_mat_extra"] = []
            reset_keuze(prefix)
            st.rerun()
    else:
        st.caption("Nog geen materiaal gekozen — vul hierboven bij elk artikel het aantal in.")

    return gekozen
