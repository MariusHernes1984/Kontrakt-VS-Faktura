"""Sender avviksvarsling via Azure Communication Services Email."""
import os
import base64
import logging
from azure.communication.email import EmailClient

ACS_CONNECTION_STRING = os.getenv("ACS_CONNECTION_STRING", "")
ACS_SENDER_EMAIL = os.getenv("ACS_SENDER_EMAIL", "DoNotReply@3e6e33cf-4734-454a-b2af-1f01b3fd4272.azurecomm.net")

logger = logging.getLogger(__name__)


def _bygg_html_innhold(faktura: dict, rapport: dict) -> str:
    """Bygger HTML-innhold for e-postvarsling."""
    status = rapport.get("status", "UKJENT")
    faktura_nr = faktura.get("faktura_nummer", "-")
    leverandor = faktura.get("leverandor_navn", "-")
    antall_avvik = rapport.get("oppsummering", {}).get("antall_avvik", 0)
    antall_advarsler = rapport.get("oppsummering", {}).get("antall_advarsler", 0)

    avvik_rader = ""
    for avvik in rapport.get("avvik", []):
        avvik_rader += f"""
        <tr>
            <td style="padding: 8px; border: 1px solid #e5e7eb;">{avvik.get('felt', '-')}</td>
            <td style="padding: 8px; border: 1px solid #e5e7eb;">{avvik.get('faktura_verdi', '-')}</td>
            <td style="padding: 8px; border: 1px solid #e5e7eb;">{avvik.get('kontrakt_verdi', '-')}</td>
            <td style="padding: 8px; border: 1px solid #e5e7eb; color: #dc2626; font-weight: bold;">{avvik.get('differanse', '-')}</td>
        </tr>"""

    avvik_seksjon = ""
    if avvik_rader:
        avvik_seksjon = f"""
        <div style="background: #fef2f2; padding: 20px; border: 1px solid #fecaca;">
            <h2 style="font-size: 16px; color: #dc2626; margin-top: 0;">Avvik ({antall_avvik})</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: #fee2e2;">
                    <th style="padding: 8px; border: 1px solid #e5e7eb; text-align: left;">Felt</th>
                    <th style="padding: 8px; border: 1px solid #e5e7eb; text-align: left;">Faktura</th>
                    <th style="padding: 8px; border: 1px solid #e5e7eb; text-align: left;">Kontrakt</th>
                    <th style="padding: 8px; border: 1px solid #e5e7eb; text-align: left;">Differanse</th>
                </tr>
                {avvik_rader}
            </table>
        </div>"""

    advarsler_rader = ""
    for adv in rapport.get("advarsler", []):
        advarsler_rader += f"""
        <tr>
            <td style="padding: 8px; border: 1px solid #e5e7eb;">{adv.get('felt', '-')}</td>
            <td style="padding: 8px; border: 1px solid #e5e7eb;">{adv.get('beskrivelse', '-')}</td>
        </tr>"""

    advarsler_seksjon = ""
    if advarsler_rader:
        advarsler_seksjon = f"""
        <div style="background: #fffbeb; padding: 20px; border: 1px solid #fde68a;">
            <h2 style="font-size: 16px; color: #d97706; margin-top: 0;">Advarsler ({antall_advarsler})</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="background: #fef3c7;">
                    <th style="padding: 8px; border: 1px solid #e5e7eb; text-align: left;">Felt</th>
                    <th style="padding: 8px; border: 1px solid #e5e7eb; text-align: left;">Beskrivelse</th>
                </tr>
                {advarsler_rader}
            </table>
        </div>"""

    header_bg = "#dc2626" if status == "AVVIK FUNNET" else "#d97706"
    header_tittel = "Avvik funnet" if status == "AVVIK FUNNET" else "Advarsel"

    return f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: {header_bg}; color: white; padding: 20px; border-radius: 8px 8px 0 0;">
            <h1 style="margin: 0; font-size: 22px;">{header_tittel}</h1>
            <p style="margin: 5px 0 0; opacity: 0.9;">Kontraktskontroll - Automatisk varsling</p>
        </div>

        <div style="background: #f9fafb; padding: 20px; border: 1px solid #e5e7eb;">
            <h2 style="font-size: 16px; color: #374151; margin-top: 0;">Fakturadetaljer</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 6px 0; color: #6b7280; width: 140px;">Leverandor:</td>
                    <td style="padding: 6px 0; font-weight: 600;">{leverandor}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #6b7280;">Fakturanummer:</td>
                    <td style="padding: 6px 0; font-weight: 600;">{faktura_nr}</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #6b7280;">Totalbelop:</td>
                    <td style="padding: 6px 0; font-weight: 600;">{faktura.get('total_belop', '-')} NOK</td>
                </tr>
                <tr>
                    <td style="padding: 6px 0; color: #6b7280;">Kontrakt:</td>
                    <td style="padding: 6px 0; font-weight: 600;">{rapport.get('kontrakt_nummer', '-')}</td>
                </tr>
            </table>
        </div>

        {avvik_seksjon}
        {advarsler_seksjon}

        <div style="padding: 20px; background: #f3f4f6; border-radius: 0 0 8px 8px; border: 1px solid #e5e7eb; border-top: none;">
            <p style="color: #6b7280; font-size: 14px; margin: 0;">
                Se fullstendig avviksrapport i vedlegget. Logg inn pa
                <a href="https://kontraktskontroll-poc.azurewebsites.net">Kontraktskontroll</a>
                for mer informasjon.
            </p>
        </div>
    </div>
    """


def send_avviksvarsling(mottaker_epost: str, faktura: dict, rapport: dict, pdf_bytes: bytes) -> dict:
    """
    Sender avviksvarsling via Azure Communication Services Email.

    Args:
        mottaker_epost: E-postadressen til mottaker
        faktura: Faktura-data dict
        rapport: Avviksrapport dict
        pdf_bytes: Avviksrapport PDF som bytes

    Returns:
        dict med 'success' (bool) og 'melding' (str)
    """
    if not ACS_CONNECTION_STRING:
        logger.warning("ACS_CONNECTION_STRING er ikke satt - hopper over e-postvarsling")
        return {"success": False, "melding": "E-postvarsling er ikke konfigurert (mangler ACS_CONNECTION_STRING)"}

    if not mottaker_epost:
        return {"success": False, "melding": "Ingen mottaker-e-post oppgitt"}

    faktura_nr = faktura.get("faktura_nummer", "-")
    leverandor = faktura.get("leverandor_navn", "-")
    emne = f"Avvik funnet - Faktura {faktura_nr} fra {leverandor}"

    html_innhold = _bygg_html_innhold(faktura, rapport)

    vedlegg_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    fnr = faktura_nr.replace("/", "-")

    message = {
        "senderAddress": ACS_SENDER_EMAIL,
        "recipients": {
            "to": [{"address": mottaker_epost}],
        },
        "content": {
            "subject": emne,
            "html": html_innhold,
        },
        "attachments": [
            {
                "name": f"Avviksrapport_{fnr}.pdf",
                "contentType": "application/pdf",
                "contentInBase64": vedlegg_base64,
            }
        ],
    }

    try:
        client = EmailClient.from_connection_string(ACS_CONNECTION_STRING)
        poller = client.begin_send(message)
        result = poller.result()

        if result["status"] == "Succeeded":
            logger.info(f"Avviksvarsling sendt til {mottaker_epost} via Azure Communication Services")
            return {"success": True, "melding": f"E-postvarsling sendt til {mottaker_epost}"}
        else:
            logger.error(f"ACS e-post feilet: {result}")
            return {"success": False, "melding": f"E-post feilet med status: {result.get('status', 'ukjent')}"}

    except Exception as e:
        logger.exception("Feil ved sending av avviksvarsling via ACS")
        return {"success": False, "melding": f"Feil ved sending: {str(e)}"}
