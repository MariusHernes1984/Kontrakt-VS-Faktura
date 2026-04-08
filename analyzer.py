import os
import json
import base64
from openai import AzureOpenAI
from PyPDF2 import PdfReader
from dotenv import load_dotenv

load_dotenv()

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY er ikke satt. "
                "Opprett en .env-fil med din API-nokkel."
            )
        _client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=endpoint,
            api_version="2024-12-01-preview",
        )
    return _client

EXTRACTION_PROMPT = """Du er en ekspert på å analysere norske fakturaer.
Analyser denne fakturaen og ekstraher følgende informasjon i JSON-format:

{
    "leverandor_navn": "Navn på leverandør/avsender av faktura",
    "prosjekt_id": "Prosjekt-ID eller referansenummer hvis oppgitt",
    "faktura_nummer": "Fakturanummer",
    "faktura_dato": "Fakturadato (YYYY-MM-DD format)",
    "forfallsdato": "Forfallsdato (YYYY-MM-DD format)",
    "total_belop": 0.00,
    "timepris": 0.00,
    "antall_timer": 0.0,
    "valuta": "NOK",
    "linjer": [
        {
            "beskrivelse": "Beskrivelse av tjeneste/vare",
            "antall": 0,
            "enhetspris": 0.00,
            "belop": 0.00
        }
    ],
    "mva_belop": 0.00,
    "total_eks_mva": 0.00,
    "kundenavn": "Navn på kunde/mottaker",
    "notater": "Eventuelle relevante notater eller referanser"
}

Viktig:
- Returner KUN gyldig JSON, ingen annen tekst.
- Bruk 0 eller null for felt du ikke finner.
- Datoer skal være i YYYY-MM-DD format.
- Beløp skal være tall uten valutasymbol.
- Hvis timepris ikke er eksplisitt oppgitt, prøv å beregne den fra linjer (beløp / antall).
"""


def ekstraher_tekst_fra_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    tekst = ""
    for page in reader.pages:
        tekst += page.extract_text() or ""
    return tekst


def analyser_faktura(pdf_path):
    tekst = ekstraher_tekst_fra_pdf(pdf_path)

    if not tekst.strip():
        return {
            "feil": "Kunne ikke ekstrahere tekst fra PDF. "
                    "Filen kan være skannet/bildebasert."
        }

    try:
        response = _get_client().chat.completions.create(
            model="gpt-5.3-chat",
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": f"Analyser denne fakturaen:\n\n{tekst}"},
            ],
            response_format={"type": "json_object"},
        )

        resultat = json.loads(response.choices[0].message.content)
        return resultat

    except json.JSONDecodeError:
        return {"feil": "Kunne ikke tolke AI-responsen som JSON."}
    except Exception as e:
        return {"feil": f"Feil ved AI-analyse: {str(e)}"}


KONTRAKT_PROMPT = """Du er en ekspert på å analysere norske leverandørkontrakter.
Din oppgave er å ekstrahere strukturerte data fra kontraktsteksten.

VIKTIGE REGLER:
- Returner KUN det som EKSPLISITT står i kontrakten.
- Bruk null for felter du ikke finner — IKKE gjett, IKKE utled.
- Returner KUN gyldig JSON, ingen forklaringer eller tekst utenfor JSON.
- For hvert felt skal du oppgi en confidence-score mellom 0.0 og 1.0:
    1.0 = står helt eksplisitt og utvetydig
    0.7-0.9 = står tydelig, men trenger litt tolkning
    0.4-0.6 = usikker / flere mulige tolkninger
    0.0 = ikke funnet (verdien skal da være null)

JSON-skjema:
{
    "er_kontrakt": true,
    "felter": {
        "leverandor_navn":         {"verdi": "...", "confidence": 0.0},
        "kontrakt_nummer":         {"verdi": "...", "confidence": 0.0},
        "prosjekt_id":             {"verdi": "...", "confidence": 0.0},
        "timepris":                {"verdi": 0.00, "confidence": 0.0},
        "maks_timer_per_maaned":   {"verdi": 0,    "confidence": 0.0},
        "sla_responstid_timer":    {"verdi": 0,    "confidence": 0.0},
        "avtalt_rabatt_prosent":   {"verdi": 0.0,  "confidence": 0.0},
        "valuta":                  {"verdi": "NOK","confidence": 0.0},
        "startdato":               {"verdi": "YYYY-MM-DD", "confidence": 0.0},
        "sluttdato":               {"verdi": "YYYY-MM-DD", "confidence": 0.0},
        "beskrivelse":             {"verdi": "...", "confidence": 0.0}
    },
    "advarsler": ["liste med tekstlige advarsler hvis noe er uklart"]
}

Hvis dokumentet ikke ser ut som en kontrakt, sett "er_kontrakt": false og
returner tomme felter.
"""


def analyser_kontrakt_tekst(tekst: str):
    """Analyserer kontraktstekst og returnerer strukturerte felter med confidence."""
    if not tekst or not tekst.strip():
        return {"feil": "Tom kontraktstekst."}

    try:
        response = _get_client().chat.completions.create(
            model="gpt-5.3-chat",
            messages=[
                {"role": "system", "content": KONTRAKT_PROMPT},
                {"role": "user", "content": f"Analyser denne kontrakten:\n\n{tekst}"},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError:
        return {"feil": "Kunne ikke tolke AI-responsen som JSON."}
    except Exception as e:
        return {"feil": f"Feil ved AI-analyse: {str(e)}"}


def analyser_faktura_med_bilde(pdf_path):
    """Alternativ: send PDF-sider som bilder for bedre OCR-støtte."""
    tekst = ekstraher_tekst_fra_pdf(pdf_path)

    if not tekst.strip():
        return {
            "feil": "Kunne ikke ekstrahere tekst fra PDF. "
                    "Filen kan være skannet/bildebasert. "
                    "Vurder å bruke en OCR-tjeneste først."
        }

    return analyser_faktura(pdf_path)
