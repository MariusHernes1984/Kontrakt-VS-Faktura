"""Sender avviksvarsling via SMTP (Outlook/M365)."""
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_BRUKERNAVN = os.getenv("SMTP_BRUKERNAVN", "")
SMTP_PASSORD = os.getenv("SMTP_PASSORD", "")

logger = logging.getLogger(__name__)


def _bygg_html_innhold(faktura: dict, rapport: dict) -> str:
    """Bygger HTML-innhold for e-postvarsling."""
    status = rapport.get("status", "UKJENT")
    faktura_nr = faktura.get("faktura_nummer", "-")
    leverandor = faktura.get("leverandor_navn", "-")
    antall_avvik = rapport.get("oppsummering", {}).get("antall_avvik", 0)
    antall_advarsler = rapport.get("oppsummering", {}).get("antall_advarsler", 0)

    # Avvik-tabell
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

    # Advarsler-tabell
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
    Sender avviksvarsling via SMTP (Outlook/M365).

    Args:
        mottaker_epost: E-postadressen til mottaker
        faktura: Faktura-data dict
        rapport: Avviksrapport dict
        pdf_bytes: Avviksrapport PDF som bytes

    Returns:
        dict med 'success' (bool) og 'melding' (str)
    """
    if not SMTP_BRUKERNAVN or not SMTP_PASSORD:
        logger.warning("SMTP-innstillinger ikke konfigurert - hopper over e-postvarsling")
        return {"success": False, "melding": "E-postvarsling er ikke konfigurert (mangler SMTP-innstillinger)"}

    if not mottaker_epost:
        logger.warning("Ingen mottaker-e-post - hopper over varsling")
        return {"success": False, "melding": "Ingen mottaker-e-post konfigurert"}

    faktura_nr = faktura.get("faktura_nummer", "-")
    leverandor = faktura.get("leverandor_navn", "-")
    emne = f"Avvik funnet - Faktura {faktura_nr} fra {leverandor}"

    try:
        # Bygg e-post
        msg = MIMEMultipart()
        msg["From"] = SMTP_BRUKERNAVN
        msg["To"] = mottaker_epost
        msg["Subject"] = emne

        # HTML-innhold
        html_innhold = _bygg_html_innhold(faktura, rapport)
        msg.attach(MIMEText(html_innhold, "html", "utf-8"))

        # PDF-vedlegg
        fnr = faktura_nr.replace("/", "-")
        vedlegg_filnavn = f"Avviksrapport_{fnr}.pdf"
        vedlegg = MIMEApplication(pdf_bytes, _subtype="pdf")
        vedlegg.add_header("Content-Disposition", "attachment", filename=vedlegg_filnavn)
        msg.attach(vedlegg)

        # Send via SMTP
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_BRUKERNAVN, SMTP_PASSORD)
            server.send_message(msg)

        logger.info(f"Avviksvarsling sendt til {mottaker_epost}")
        return {"success": True, "melding": f"E-postvarsling sendt til {mottaker_epost}"}

    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP-autentisering feilet - sjekk brukernavn/passord")
        return {"success": False, "melding": "E-post autentisering feilet. Sjekk SMTP-innstillinger."}
    except smtplib.SMTPException as e:
        logger.error(f"SMTP-feil: {e}")
        return {"success": False, "melding": f"Feil ved sending av e-post: {str(e)}"}
    except Exception as e:
        logger.exception("Uventet feil ved sending av avviksvarsling")
        return {"success": False, "melding": f"Uventet feil: {str(e)}"}
