"""Genererer avviksrapport i PDF-format for oppfolging."""
import os
import io
from datetime import datetime
from fpdf import FPDF


class AvviksRapportPDF(FPDF):
    def __init__(self, faktura, rapport):
        super().__init__()
        self.faktura = faktura
        self.rapport = rapport

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(150, 150, 150)
        self.cell(0, 6, "AVVIKSRAPPORT - KONTRAKTSKONTROLL", align="L")
        self.cell(0, 6, f"Generert: {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, "Kontraktskontroll - Automatisk avviksrapport", align="L")
        self.cell(0, 5, f"Side {self.page_no()}/{{nb}}", align="R")


def generer_avviksrapport(faktura, rapport):
    """Genererer en PDF-rapport for avvik/advarsler og returnerer bytes."""
    pdf = AvviksRapportPDF(faktura, rapport)
    pdf.alias_nb_pages()
    pdf.add_page()

    status = rapport.get("status", "UKJENT")

    # --- Tittel ---
    pdf.set_font("Helvetica", "B", 20)
    if status == "AVVIK FUNNET":
        pdf.set_text_color(220, 38, 38)
        tittel = "AVVIKSRAPPORT"
    elif status == "ADVARSEL":
        pdf.set_text_color(217, 119, 6)
        tittel = "ADVARSELSRAPPORT"
    else:
        pdf.set_text_color(5, 150, 105)
        tittel = "KONTROLLRAPPORT"

    pdf.cell(0, 12, tittel, align="C")
    pdf.ln(5)

    # Undertittel
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, f"Faktura {faktura.get('faktura_nummer', faktura.get('filnavn', '-'))}", align="C")
    pdf.ln(12)

    # --- Oppsummering ---
    opps = rapport.get("oppsummering", {})
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, "Oppsummering")
    pdf.ln(8)

    # Status-boks
    if status == "AVVIK FUNNET":
        pdf.set_fill_color(254, 242, 242)
        pdf.set_draw_color(220, 38, 38)
    elif status == "ADVARSEL":
        pdf.set_fill_color(255, 251, 235)
        pdf.set_draw_color(217, 119, 6)
    else:
        pdf.set_fill_color(236, 253, 245)
        pdf.set_draw_color(5, 150, 105)

    pdf.set_font("Helvetica", "B", 11)
    boks_y = pdf.get_y()
    pdf.rect(10, boks_y, 190, 22, style="DF")
    pdf.set_xy(15, boks_y + 3)
    pdf.cell(0, 8, f"Status: {status}")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_xy(15, boks_y + 11)
    pdf.cell(0, 8,
        f"{opps.get('antall_avvik', 0)} avvik  |  "
        f"{opps.get('antall_advarsler', 0)} advarsler  |  "
        f"{opps.get('antall_ok', 0)} godkjent  |  "
        f"Totalt {opps.get('totalt_sjekket', 0)} kontroller"
    )
    pdf.set_y(boks_y + 28)

    # --- Fakturadetaljer ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, "Fakturadetaljer")
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 10)
    detaljer = [
        ("Leverandor", faktura.get("leverandor_navn", "-")),
        ("Fakturanummer", faktura.get("faktura_nummer", "-")),
        ("Prosjekt-ID", faktura.get("prosjekt_id", "-")),
        ("Fakturadato", faktura.get("faktura_dato", "-")),
        ("Forfallsdato", faktura.get("forfallsdato", "-")),
        ("Timepris", f"{faktura.get('timepris', 0):,.2f} NOK" if faktura.get("timepris") else "-"),
        ("Antall timer", str(faktura.get("antall_timer", "-"))),
        ("Totalbelop", f"{faktura.get('total_belop', 0):,.2f} NOK" if faktura.get("total_belop") else "-"),
    ]

    pdf.set_fill_color(245, 245, 250)
    for i, (label, verdi) in enumerate(detaljer):
        fill = i % 2 == 0
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(55, 7, label, border=0, fill=fill)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(135, 7, str(verdi), border=0, fill=fill)
        pdf.ln(7)

    pdf.ln(5)

    # --- Kontrakt-referanse ---
    if rapport.get("kontrakt_nummer"):
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Kontraktreferanse")
        pdf.ln(8)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(55, 7, "Kontraktnummer:")
        pdf.cell(0, 7, rapport.get("kontrakt_nummer", "-"))
        pdf.ln(7)
        if faktura.get("kontrakt_leverandor"):
            pdf.cell(55, 7, "Kontraktsleverandor:")
            pdf.cell(0, 7, faktura.get("kontrakt_leverandor", "-"))
            pdf.ln(7)
        pdf.ln(5)

    # --- AVVIK ---
    avvik_liste = rapport.get("avvik", [])
    if avvik_liste:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(220, 38, 38)
        pdf.cell(0, 10, f"Avvik ({len(avvik_liste)})")
        pdf.ln(10)

        for i, avvik in enumerate(avvik_liste, 1):
            # Sjekk om vi trenger ny side
            if pdf.get_y() > 240:
                pdf.add_page()

            pdf.set_fill_color(254, 242, 242)
            pdf.set_draw_color(220, 38, 38)
            y_start = pdf.get_y()

            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(220, 38, 38)
            pdf.cell(0, 7, f"Avvik {i}: {avvik.get('felt', '-')}", fill=True)
            pdf.ln(8)

            pdf.set_text_color(50, 50, 50)
            pdf.set_font("Helvetica", "", 9)

            if avvik.get("faktura_verdi"):
                pdf.cell(40, 6, "  Faktura:")
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(0, 6, str(avvik["faktura_verdi"]))
                pdf.ln(6)
                pdf.set_font("Helvetica", "", 9)

            if avvik.get("kontrakt_verdi"):
                pdf.cell(40, 6, "  Kontrakt:")
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(0, 6, str(avvik["kontrakt_verdi"]))
                pdf.ln(6)
                pdf.set_font("Helvetica", "", 9)

            if avvik.get("differanse"):
                pdf.cell(40, 6, "  Differanse:")
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_text_color(220, 38, 38)
                pdf.cell(0, 6, str(avvik["differanse"]))
                pdf.ln(6)
                pdf.set_text_color(50, 50, 50)
                pdf.set_font("Helvetica", "", 9)

            if avvik.get("beskrivelse"):
                pdf.ln(2)
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(80, 80, 80)
                pdf.multi_cell(0, 5, f"  {avvik['beskrivelse']}")

            # Strek under avvik
            pdf.ln(3)
            pdf.set_draw_color(230, 230, 230)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

    # --- ADVARSLER ---
    advarsler_liste = rapport.get("advarsler", [])
    if advarsler_liste:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(217, 119, 6)
        pdf.cell(0, 10, f"Advarsler ({len(advarsler_liste)})")
        pdf.ln(10)

        for i, adv in enumerate(advarsler_liste, 1):
            if pdf.get_y() > 240:
                pdf.add_page()

            pdf.set_fill_color(255, 251, 235)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(217, 119, 6)
            pdf.cell(0, 7, f"Advarsel {i}: {adv.get('felt', '-')}", fill=True)
            pdf.ln(8)

            pdf.set_text_color(50, 50, 50)
            pdf.set_font("Helvetica", "", 9)

            if adv.get("faktura_verdi"):
                pdf.cell(40, 6, "  Faktura:")
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(0, 6, str(adv["faktura_verdi"]))
                pdf.ln(6)
                pdf.set_font("Helvetica", "", 9)

            if adv.get("kontrakt_verdi"):
                pdf.cell(40, 6, "  Kontrakt:")
                pdf.set_font("Helvetica", "B", 9)
                pdf.cell(0, 6, str(adv["kontrakt_verdi"]))
                pdf.ln(6)
                pdf.set_font("Helvetica", "", 9)

            if adv.get("beskrivelse"):
                pdf.ln(2)
                pdf.set_font("Helvetica", "I", 9)
                pdf.set_text_color(80, 80, 80)
                pdf.multi_cell(0, 5, f"  {adv['beskrivelse']}")

            pdf.ln(3)
            pdf.set_draw_color(230, 230, 230)
            pdf.line(10, pdf.get_y(), 200, pdf.get_y())
            pdf.ln(5)

    # --- Godkjente kontroller ---
    ok_liste = rapport.get("ok", [])
    if ok_liste:
        if pdf.get_y() > 220:
            pdf.add_page()

        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(5, 150, 105)
        pdf.cell(0, 10, f"Godkjente kontroller ({len(ok_liste)})")
        pdf.ln(10)

        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(50, 50, 50)
        pdf.set_fill_color(236, 253, 245)

        for item in ok_liste:
            if pdf.get_y() > 270:
                pdf.add_page()
            pdf.cell(5, 6, "", fill=True)
            pdf.cell(50, 6, item.get("felt", "-"), fill=True)
            pdf.cell(0, 6, item.get("beskrivelse", ""), fill=True)
            pdf.ln(7)

    # --- Signatur-seksjon ---
    if pdf.get_y() > 220:
        pdf.add_page()

    pdf.ln(15)
    pdf.set_draw_color(200, 200, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, "Oppfolging")
    pdf.ln(10)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)

    if avvik_liste:
        pdf.multi_cell(0, 6,
            "Denne fakturaen har avvik som ma behandles for betaling. "
            "Kontakt leverandoren for avklaring og be om korrigert faktura "
            "dersom avvikene ikke kan forklares."
        )
    elif advarsler_liste:
        pdf.multi_cell(0, 6,
            "Denne fakturaen har advarsler som bor sjekkes manuelt. "
            "Verifiser at informasjonen stemmer for betaling godkjennes."
        )

    pdf.ln(15)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)

    pdf.cell(90, 6, "Behandlet av:")
    pdf.cell(90, 6, "Godkjent av:")
    pdf.ln(20)
    pdf.cell(90, 0, "", border="T")
    pdf.cell(10)
    pdf.cell(80, 0, "", border="T")
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(90, 6, "Navn / Dato")
    pdf.cell(90, 6, "Navn / Dato")

    # Returner som bytes
    return bytes(pdf.output())
