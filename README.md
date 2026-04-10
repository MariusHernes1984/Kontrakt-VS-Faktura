# Kontraktskontroll (Kontrakt-VS-Faktura)

AI-drevet Proof of Concept for innkjøpsavdelingen som automatisk verifiserer at innkommende fakturaer samsvarer med leverandørens kontraktuelle forpliktelser. Bygget som en Python Flask-webapp og driftet på Azure.

**Live demo:** https://kontraktskontroll-poc.azurewebsites.net

---

## Funksjonalitet

### Kjernefunksjoner
- **PDF-opplasting av fakturaer** – Last opp leverandørfaktura som PDF direkte i webgrensesnittet.
- **PDF-opplasting av kontrakter** – Last opp kontrakt-PDF og la AI automatisk ekstrahere felter:
  - Leverandørnavn, kontraktsnummer, timepris, maks timer, rabatter, gyldighetsperiode m.m.
  - Per-felt **konfidensscorer** (høy/middels/lav) med fargekodede indikatorer (grønn/gul/rød).
  - Forhåndsvis og juster AI-foreslåtte verdier før lagring.
  - Advarsel ved duplikat kontraktsnummer.
- **OCR-støtte** – Skannede/bildebaserte PDF-er håndteres automatisk via Tesseract OCR med norsk språkpakke.
- **AI-analyse** – Azure OpenAI (`gpt-5.3-chat`) ekstraherer strukturerte data fra fakturaen (leverandør, fakturanummer, timepris, antall timer, totalbeløp, prosjekt-ID, periode m.m.).
- **Automatisk kontraktsmatching** – Appen finner tilhørende kontrakt basert på leverandørnavn og/eller prosjekt-ID.
- **Valideringsmotor** med 6 regler:
  1. Timepris mot avtalt timepris
  2. Antall timer mot maks timer per måned
  3. Totalbeløp mot maks månedlig beløp (inkl. rabatt)
  4. Fakturaperiode innenfor kontraktsperiode
  5. Prosjekt-ID samsvar
  6. Leverandørnavn samsvar
- **Tre statusnivåer:**
  - **GODKJENT** – ingen avvik
  - **ADVARSEL** – mindre avvik / manglende data
  - **AVVIK FUNNET** – brudd på kontraktsvilkår
- **Avviksrapport (PDF)** – Genereres automatisk med `fpdf2` og kan lastes ned eller sendes som vedlegg.

### Kontraktsforvaltning
- **To måter å opprette kontrakt:**
  1. **Last opp PDF** → AI leser og foreslår verdier → verifiser/juster → lagre.
  2. **Manuelt skjema** → fyll ut feltene selv.
- Se kontraktsdetaljer med innebygget PDF-visning.
- Slett eller oppdater kontrakter.
- **Auto-seed ved tom database** – Demo-data lastes automatisk ved første oppstart.

### Varsling (e-post)
- Egen **Varsling**-side for å administrere mottakere av avviksvarsel.
- **Granulær konfigurasjon:**
  - Mottakere uten leverandør → varsles for *alle* leverandører.
  - Mottakere koblet til en spesifikk leverandør → varsles kun for den.
- E-post sendes automatisk ved status `ADVARSEL` eller `AVVIK FUNNET`.
- Avviksrapporten legges ved som PDF.
- Mottakere kan aktiveres/deaktiveres uten å slettes.

### Historikk og oversikt
- Dashboard med nøkkeltall (antall fakturaer, avvik, godkjente).
- Full fakturalogg med status, leverandør, dato og rapport.

---

## Infrastruktur / Arkitektur

```
                  +----------------------------+
                  |   Bruker (nettleser)       |
                  +--------------+-------------+
                                 | HTTPS
                  +--------------v-------------+
                  |  Azure App Service         |
                  |  kontraktskontroll-poc     |
                  |  (Linux, Python 3.12)      |
                  |  Flask + gunicorn          |
                  +---+---------+----------+---+
                      |         |          |
            +---------v--+  +---v-----+  +-v-------------------+
            | SQLite DB  |  | Azure   |  | Azure Communication |
            | kontrakter |  | OpenAI  |  | Services Email      |
            | .db        |  | gpt-5.3 |  | (Azure-managed      |
            |            |  | -chat   |  |  domain)            |
            +------------+  +---------+  +---------------------+
```

### Komponenter
| Lag | Teknologi |
|-----|-----------|
| Web / UI | Flask 3.1, Jinja2, vanilla HTML/CSS (norsk UI, Atea-farger) |
| WSGI | gunicorn 23 |
| Hosting | Azure App Service (Linux, Python 3.12) |
| AI | Azure OpenAI – deployment `gpt-5.3-chat` |
| PDF-ekstraksjon | PyPDF2 + Tesseract OCR (fallback for skannede PDF-er) |
| PDF-generering | fpdf2 (avviksrapport, kontrakter) |
| Database | SQLite (`kontrakter.db`) |
| E-post | Azure Communication Services Email (`azure-communication-email`) |
| Deploy | `az webapp deploy` med Python-generert zip |

### Database (SQLite)
- `kontrakter` – leverandørkontrakter med priser, SLA, perioder, PDF-filsti.
- `faktura_logg` – historikk over analyserte fakturaer med status og rapport.
- `varslingsmottakere` – e-postmottakere (globalt eller per leverandør).

### Azure-ressurser (`rg-kontraktskontroll`)
- **App Service:** `kontraktskontroll-poc`
- **Azure OpenAI:** deployment `gpt-5.3-chat`
- **Communication Services:** `kontraktskontroll-comm`
- **Email Services:** `kontraktskontroll-email` + Azure-managed domain
  - Avsender: `DoNotReply@<domene>.azurecomm.net`

### Miljøvariabler (App Service / `.env`)
```
AZURE_OPENAI_ENDPOINT=https://<din-openai>.openai.azure.com/
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_DEPLOYMENT=gpt-5.3-chat
AZURE_OPENAI_API_VERSION=2024-12-01-preview
ACS_CONNECTION_STRING=endpoint=https://...;accesskey=...
ACS_SENDER_EMAIL=DoNotReply@<din-domene>.azurecomm.net
FLASK_SECRET_KEY=<random>
```

---

## Hvordan kjøre demo

### Alternativ 1 – Bruk deployet versjon
1. Gå til https://kontraktskontroll-poc.azurewebsites.net
2. **Kontrakter → Last opp PDF** – last opp en kontrakt-PDF og la AI fylle ut feltene automatisk, eller bruk **Ny kontrakt** for manuell registrering.
3. **Varsling → Legg til mottaker** – legg til din e-post (la leverandør stå tom for å få alle varsler).
4. **Last opp faktura** – last opp en PDF-faktura fra samme leverandør.
5. Se resultatet: status, avviksrapport og e-postvarsel i innboksen.

### Alternativ 2 – Kjør lokalt

**Forutsetninger:** Python 3.12, git, tilgang til Azure OpenAI (og evt. Azure Communication Services for e-post).

```bash
# 1. Klon repo
git clone https://github.com/<bruker>/Kontrakt-VS-Faktura.git
cd Kontrakt-VS-Faktura

# 2. Opprett virtuelt miljø
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Installer avhengigheter
pip install -r requirements.txt

# 4. Konfigurer miljøvariabler
#    Opprett .env basert på eksempelet over

# 5. Start appen
flask --app app run
# Åpne http://127.0.0.1:5000
```

Databasen (`kontrakter.db`) opprettes og populeres automatisk med demodata ved første oppstart (13 kontrakter, 48 fakturaer).

### Demoflyt (forslag)
1. **AI-utfylling av kontrakt:** Gå til Kontrakter → Last opp PDF → bruk en av demo-kontraktene i `demo_kontrakter/` → sjekk konfidensscorer og lagre.
2. Legg til varslingsmottaker på Varsling-siden.
3. Last opp en testfaktura der timepris = 1400 → forventet status **AVVIK FUNNET**.
4. Last ned avviksrapport-PDF og sjekk e-postvarsel.
5. Last opp en gyldig faktura (timepris 1200) → forventet status **GODKJENT**.

---

## Prosjektstruktur

```
.
├── app.py                    # Flask-ruter og applikasjonslogikk
├── database.py               # SQLite CRUD
├── analyzer.py               # Azure OpenAI-integrasjon (faktura + kontrakt)
├── pdf_extractor.py          # PDF-ekstraksjon med OCR-fallback
├── validator.py              # Valideringsregler
├── report_generator.py       # Avviksrapport (fpdf2)
├── email_client.py           # Azure Communication Services Email
├── seed_data.py              # Seed-data for demo
├── seed_extra.py             # Ekstra seed-data
├── generate_contracts.py     # Genererer demo-kontrakt-PDF-er
├── generate_invoices.py      # Genererer demo-faktura-PDF-er
├── generate_demo_contracts.py # Genererer eksempelkontrakter for opplastingstest
├── startup.sh                # Azure App Service startup (OCR-installasjon)
├── templates/                # Jinja2 HTML-maler
├── static/                   # CSS / assets (Atea-logo, farger)
├── kontrakt_filer/           # Lagrede kontrakt-PDF-er
├── demo_kontrakter/          # Demo-PDF-er for testing av AI-ekstraksjon
├── uploads/                  # Opplastede fakturaer
├── requirements.txt
└── README.md
```

---

## Anonymisering
Alle leverandørnavn i demodata er anonymisert til **Leverandør 1–12 AS**. Ingen reelle selskapsnavn brukes i seed-data eller genererte PDF-er.

## Status
Dette er en **Proof of Concept** laget for intern demo. Ikke ment for produksjon uten ytterligere sikkerhets-, skalerings- og feilhåndteringstiltak.
