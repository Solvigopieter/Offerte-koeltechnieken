Solvigo Koeltechnieken — Offertegenerator
=====================================

Zelfde opzet als de Solvigo offertegenerator, met 3 extra's:
- 📁 Projecten bewaren, terug openen en verwijderen
- 📄 PDF-offerte in P&R huisstijl (navy/oranje)
- ⚙️ Alle prijzen aanpasbaar via de app (pagina "Prijsinstellingen") — geen code nodig

Structuur
---------
- app.py                          → entrypoint
- auth.py                         → wachtwoordscherm (APP_PASSWORD in Secrets)
- pr_core.py                      → prijzen, berekeningen, PDF-generatie
- storage.py                      → opslag: Google Sheets óf lokaal JSON
- pages/01_Airco Offerte.py
- pages/02_Warmtepomp Offerte.py
- pages/03_Projecten.py
- pages/04_Prijsinstellingen.py
- assets/logo.png                 → Solvigo Koeltechnieken-logo (staat er al in, komt in de PDF-header)

VOOR JE START: website en e-mailadres in pr_core.py (blok BEDRIJFSINFO) staan nog
op de tijdelijke Solvigo-waarden (www.solvigo.be / cleaning@solvigo.be) — TODO:
aanpassen naar de definitieve koeltechnieken-website en het e-mailadres zodra
die bekend zijn.

Lokaal starten
--------------
pip install -r requirements.txt
streamlit run app.py

Maak lokaal .streamlit/secrets.toml met:
    APP_PASSWORD = "JullieSterkWachtwoord123!"

Zonder Google Sheets-configuratie bewaart de app alles in pr_data.json
(prima lokaal, maar Streamlit Community Cloud vergeet dit bij elke herstart!).

Online (Streamlit Community Cloud) — met blijvende opslag
---------------------------------------------------------
1. Repo op GitHub → Deploy met entrypoint: app.py
2. Gebruik hetzelfde Google service account als de Solvigo CRM
   (project solvigo-offertes-500821) of maak een nieuw aan.
3. Maak een Google Sheet aan, bv. "Koeltechnieken offerte", en deel die met het
   service-account e-mailadres (Editor-rechten).
4. In Streamlit → Settings → Secrets:

    APP_PASSWORD = "JullieSterkWachtwoord123!"
    PR_SHEET_NAME = "Koeltechnieken offerte"

    [gcp_service_account]
    type = "service_account"
    project_id = "..."
    private_key_id = "..."
    private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
    client_email = "...@....iam.gserviceaccount.com"
    client_id = "..."
    auth_uri = "https://accounts.google.com/o/oauth2/auth"
    token_uri = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url = "..."

De app maakt zelf de tabbladen "Prijzen" en "Projecten" aan in de Sheet.

BELANGRIJK: plak je private key NOOIT in een chat of e-mail — enkel
rechtstreeks in Streamlit Secrets.

Unicode in PDF (optioneel)
--------------------------
Zet DejaVuSans.ttf in de hoofdmap voor volledige €/é/ë-ondersteuning
in de PDF. Zonder dit bestand valt de app terug op Helvetica.
