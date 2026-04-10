"""Genererer to demo-kontrakter for Kontraktskontroll:
  1) kontrakt_komplett.pdf  — alle felter tydelig angitt (høy konfidens forventet)
  2) kontrakt_mangelfull.pdf — noen felter mangler / er uklare (krever manuell justering)
"""
import os
from fpdf import FPDF

OUT_DIR = os.path.join(os.path.dirname(__file__), "demo_kontrakter")
os.makedirs(OUT_DIR, exist_ok=True)


class KontraktPDF(FPDF):
    def __init__(self, tittel):
        super().__init__()
        self._tittel = tittel

    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(120, 120, 120)
        self.cell(0, 6, self._tittel, align="R")
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Side {self.page_no()}", align="C")


def h1(pdf, tekst):
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(20, 40, 80)
    pdf.cell(0, 10, tekst, ln=1)
    pdf.ln(2)


def h2(pdf, tekst):
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(20, 40, 80)
    pdf.cell(0, 8, tekst, ln=1)


def _san(t):
    return (t.replace("\u2013", "-").replace("\u2014", "-")
             .replace("\u2018", "'").replace("\u2019", "'")
             .replace("\u201c", '"').replace("\u201d", '"'))

def para(pdf, tekst):
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 5.5, _san(tekst))
    pdf.ln(1)


def kv(pdf, key, value):
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(55, 6, f"{key}:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, value, ln=1)


# ----------------------------------------------------------------------------
# 1) KOMPLETT KONTRAKT — alle felter tydelig angitt
# ----------------------------------------------------------------------------
def generer_komplett():
    pdf = KontraktPDF("Konsulentavtale K-2026-0471")
    pdf.add_page()

    h1(pdf, "KONSULENTAVTALE")
    para(pdf,
        "Denne avtalen er inngått mellom Kunde AS (heretter Kunden) og "
        "Leverandor 11 AS, org.nr. 918 472 103 (heretter Leverandøren), "
        "og regulerer levering av IT-konsulenttjenester under prosjekt PRJ-2026-NCG.")
    pdf.ln(2)

    h2(pdf, "1. Partene")
    kv(pdf, "Leverandør", "Leverandor 11 AS")
    kv(pdf, "Organisasjonsnummer", "918 472 103")
    kv(pdf, "Adresse", "Drammensveien 145, 0277 Oslo")
    kv(pdf, "Kontaktperson", "Kontaktperson A")
    pdf.ln(2)

    h2(pdf, "2. Kontraktsopplysninger")
    kv(pdf, "Kontraktsnummer", "K-2026-0471")
    kv(pdf, "Prosjekt-ID", "PRJ-2026-NCG")
    kv(pdf, "Valuta", "NOK")
    pdf.ln(2)

    h2(pdf, "3. Varighet")
    para(pdf,
        "Avtalen trer i kraft 01.03.2026 og løper frem til og med 28.02.2027. "
        "Startdato: 2026-03-01. Sluttdato: 2027-02-28.")
    pdf.ln(1)

    h2(pdf, "4. Økonomiske vilkår")
    kv(pdf, "Avtalt timepris", "1 450,00 NOK eks. mva")
    kv(pdf, "Maksimalt antall timer per måned", "160 timer")
    kv(pdf, "Avtalt rabatt", "12 % på alle ordinære timer")
    para(pdf,
        "Fakturering skjer månedlig etterskuddsvis. Overskridelse av maksimalt "
        "antall timer per måned krever skriftlig forhåndsgodkjenning fra Kunden.")
    pdf.ln(1)

    h2(pdf, "5. Servicenivå (SLA)")
    kv(pdf, "SLA responstid", "4 timer innenfor arbeidstid")
    para(pdf,
        "Leverandøren garanterer responstid på maksimalt 4 timer ved henvendelser "
        "i arbeidstid (08:00–16:00, mandag–fredag).")
    pdf.ln(1)

    h2(pdf, "6. Beskrivelse av leveransen")
    para(pdf,
        "Leverandøren skal levere seniorkonsulenter innenfor skyarkitektur, "
        "DevOps og applikasjonsmodernisering til Kundens interne prosjekter "
        "under prosjekt PRJ-2026-NCG. Omfanget inkluderer rådgivning, "
        "implementasjon og dokumentasjon.")

    pdf.ln(6)
    h2(pdf, "7. Signaturer")
    para(pdf, "For Kunden: __________________________   Dato: 2026-02-15")
    para(pdf, "For Leverandøren: _____________________   Dato: 2026-02-15")

    filbane = os.path.join(OUT_DIR, "kontrakt_komplett.pdf")
    pdf.output(filbane)
    return filbane


# ----------------------------------------------------------------------------
# 2) MANGELFULL KONTRAKT — felter mangler / er uklare
# ----------------------------------------------------------------------------
def generer_mangelfull():
    pdf = KontraktPDF("Rammeavtale - Utkast")
    pdf.add_page()

    h1(pdf, "RAMMEAVTALE FOR KONSULENTTJENESTER")
    para(pdf,
        "Denne rammeavtalen inngås mellom Kunde AS og Leverandor 12 AS "
        "og regulerer løpende levering av IT-tjenester i henhold til behov.")
    pdf.ln(2)

    h2(pdf, "1. Partene")
    kv(pdf, "Leverandør", "Leverandor 12 AS")
    kv(pdf, "Adresse", "Strandgaten 22, 5004 Bergen")
    # Bevisst mangler: kontraktsnummer, prosjekt-ID, org.nr
    pdf.ln(2)

    h2(pdf, "2. Økonomiske vilkår")
    para(pdf,
        "Timeprisen er basert på en rabattert sats for seniorkonsulenter. "
        "Normal listepris er 1 650 NOK per time, men partene har avtalt en "
        "rabattert sats for dette oppdraget. Endelig timepris avtales per "
        "oppdrag, men skal ligge mellom 1 250 og 1 400 NOK eks. mva.")
    # Bevisst uklart: ingen eksakt timepris, rabatt-prosent ikke tallfestet
    pdf.ln(1)

    para(pdf,
        "Det er ikke satt et hardt tak på antall timer per måned. Leveransen "
        "tilpasses etter Kundens behov innenfor rimelige grenser.")
    # Bevisst mangler: maks_timer_per_maaned
    pdf.ln(1)

    h2(pdf, "3. Varighet")
    para(pdf,
        "Avtalen starter så snart begge parter har signert, og løper i "
        "utgangspunktet i 12 måneder med mulighet for forlengelse.")
    # Bevisst uklart: ingen eksakte datoer
    pdf.ln(1)

    h2(pdf, "4. Servicenivå")
    para(pdf,
        "Leverandøren skal svare på henvendelser innen rimelig tid. "
        "Responstid avtales nærmere i egen SLA-bilag (ikke vedlagt).")
    # Bevisst mangler: SLA responstid i timer
    pdf.ln(1)

    h2(pdf, "5. Beskrivelse")
    para(pdf,
        "Leverandor 12 AS skal bistå Kunden med generelle IT-oppgaver, "
        "herunder support, rådgivning og mindre utviklingsoppdrag.")

    pdf.ln(6)
    h2(pdf, "6. Signaturer")
    para(pdf, "For Kunden: __________________________   Dato: __________")
    para(pdf, "For Leverandøren: _____________________   Dato: __________")

    filbane = os.path.join(OUT_DIR, "kontrakt_mangelfull.pdf")
    pdf.output(filbane)
    return filbane


if __name__ == "__main__":
    f1 = generer_komplett()
    f2 = generer_mangelfull()
    print(f"Generert: {f1}")
    print(f"Generert: {f2}")
