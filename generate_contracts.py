"""Genererer realistiske PDF-kontrakter for alle kontrakter i databasen."""
import os
from fpdf import FPDF
from database import init_db, hent_alle_kontrakter, oppdater_kontrakt_fil

CONTRACTS_DIR = os.path.join(os.path.dirname(__file__), "kontrakt_filer")


class KontraktPDF(FPDF):
    def __init__(self, kontrakt):
        super().__init__()
        self.kontrakt = kontrakt

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, f"Kontrakt {self.kontrakt['kontrakt_nummer']}", align="R")
        self.ln(12)

    def footer(self):
        self.set_y(-20)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Side {self.page_no()}/{{nb}}", align="C")


def generer_kontrakt_pdf(kontrakt):
    pdf = KontraktPDF(kontrakt)
    pdf.alias_nb_pages()
    pdf.add_page()
    k = kontrakt

    # --- Tittel ---
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(26, 86, 219)
    pdf.cell(0, 15, "TJENESTEAVTALE", align="C")
    pdf.ln(20)

    # --- Kontraktnummer ---
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, f"Kontraktnummer: {k['kontrakt_nummer']}", align="C")
    pdf.ln(15)

    # --- Parter ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, "1. AVTALEPARTER")
    pdf.ln(10)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(90, 7, "Oppdragsgiver:")
    pdf.cell(90, 7, "Leverandor:")
    pdf.ln(7)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(90, 6, "Statens Innkjopssenter")
    pdf.cell(90, 6, k["leverandor_navn"])
    pdf.ln(6)
    pdf.cell(90, 6, "Org.nr: 986 252 932")
    pdf.cell(90, 6, f"Prosjekt-ID: {k.get('prosjekt_id', '-')}")
    pdf.ln(6)
    pdf.cell(90, 6, "Postboks 8142 Dep, 0033 Oslo")
    pdf.cell(90, 6, "")
    pdf.ln(15)

    # --- Avtalens omfang ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "2. AVTALENS OMFANG OG FORMAL")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6,
        f"Denne avtalen regulerer levering av konsulenttjenester fra "
        f"{k['leverandor_navn']} til Oppdragsgiver.\n\n"
        f"Beskrivelse: {k.get('beskrivelse', '-')}\n\n"
        f"Avtalen omfatter levering av kvalifisert personell for gjennomforing "
        f"av oppgaver innenfor det definerte tjenesteomradet, inkludert "
        f"planlegging, utvikling, testing, implementering og dokumentasjon."
    )
    pdf.ln(10)

    # --- Kontraktsperiode ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "3. KONTRAKTSPERIODE")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(50, 7, "Startdato:")
    pdf.cell(0, 7, k.get("startdato", "-"))
    pdf.ln(7)
    pdf.cell(50, 7, "Sluttdato:")
    pdf.cell(0, 7, k.get("sluttdato", "-"))
    pdf.ln(7)
    pdf.multi_cell(0, 6,
        "Avtalen kan forlenges med inntil 1+1 ar etter gjensidig skriftlig "
        "avtale mellom partene, med minimum 3 maneders varsel for utlopsdato."
    )
    pdf.ln(10)

    # --- Priser og betingelser ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "4. PRISER OG BETALINGSBETINGELSER")
    pdf.ln(10)

    # Pristabell
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(240, 240, 245)
    pdf.cell(90, 8, "Betingelse", border=1, fill=True)
    pdf.cell(90, 8, "Verdi", border=1, fill=True)
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 10)
    rader = [
        ("Timepris", f"{k.get('timepris', 0):,.2f} {k.get('valuta', 'NOK')}"),
        ("Maks timer per maned", f"{k.get('maks_timer_per_maaned', 0)} timer"),
        ("Avtalt rabatt", f"{k.get('avtalt_rabatt_prosent', 0)}%"),
        ("Valuta", k.get("valuta", "NOK")),
    ]
    for label, val in rader:
        pdf.cell(90, 7, label, border=1)
        pdf.cell(90, 7, val, border=1)
        pdf.ln(7)

    pdf.ln(5)
    pdf.multi_cell(0, 6,
        "Alle priser er eksklusive merverdiavgift (MVA). "
        "Fakturering skjer manedlig etterskuddsvis med 30 dagers betalingsfrist. "
        "Fakturaer skal inneholde kontraktnummer, prosjekt-ID, antall timer, "
        "timepris og periode."
    )
    pdf.ln(10)

    # --- SLA ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "5. TJENESTENIVA (SLA)")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 10)

    sla_timer = k.get("sla_responstid_timer", 0)
    pdf.multi_cell(0, 6,
        f"Leverandor forplikter seg til folgende tjenesteniva:\n\n"
        f"  - Responstid ved henvendelser: {sla_timer} timer i normal arbeidstid\n"
        f"  - Tilgjengelighet: Mandag-fredag 08:00-16:00\n"
        f"  - Eskaleringstid ved kritiske feil: {max(1, sla_timer // 2)} timer\n"
        f"  - Rapportering: Manedlig statusrapport med timeforbruk og fremdrift\n\n"
        f"Ved brudd pa SLA-krav kan Oppdragsgiver kreve prisavslag tilsvarende "
        f"5% av manedlig fakturabelop per palopte brudd, begrenset oppad til "
        f"20% av manedlig fakturabelop."
    )
    pdf.ln(10)

    # --- Ny side for resterende ---
    pdf.add_page()

    # --- Immaterielle rettigheter ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "6. IMMATERIELLE RETTIGHETER")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6,
        "Alt arbeid utfort under denne avtalen, inkludert kildekode, "
        "dokumentasjon, design og annet materiale, tilfaller Oppdragsgiver "
        "som fullt og helt enerettsinnehaver fra det tidspunkt materialet "
        "er levert og akseptert.\n\n"
        "Leverandor beholder rett til a benytte generell kompetanse og "
        "erfaring opparbeidet gjennom oppdraget."
    )
    pdf.ln(10)

    # --- Konfidensialitet ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "7. KONFIDENSIALITET")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6,
        "Begge parter forplikter seg til a behandle all informasjon mottatt "
        "fra den andre parten som konfidensiell. Taushetsplikten gjelder "
        "ogsa etter avtalens opphor, uten tidsbegrensning for forretnings"
        "hemmeligheter og i 5 ar for ovrig konfidensiell informasjon."
    )
    pdf.ln(10)

    # --- Mislighold ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "8. MISLIGHOLD OG HEVING")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6,
        "Ved vesentlig mislighold av avtalen kan den ikke-misligholdende "
        "part heve avtalen med 30 dagers skriftlig varsel dersom forholdet "
        "ikke er rettet innen varslingsperiodens utlop.\n\n"
        "Som vesentlig mislighold regnes blant annet:\n"
        "  - Gjentatte brudd pa SLA-krav\n"
        "  - Fakturering i strid med avtalte betingelser\n"
        "  - Brudd pa konfidensialitetsbestemmelser\n"
        "  - Manglende levering uten gyldig grunn"
    )
    pdf.ln(10)

    # --- Tvister ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "9. LOVVALG OG TVISTER")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6,
        "Denne avtalen er underlagt norsk rett. Tvister som oppstar i "
        "forbindelse med avtalen skal forst forsokes lost gjennom "
        "forhandlinger. Dersom forhandlinger ikke forer frem innen 30 "
        "dager, kan tvisten bringes inn for Oslo tingrett som rett verneting."
    )
    pdf.ln(15)

    # --- Signaturer ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "10. SIGNATURER")
    pdf.ln(15)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(90, 6, "For Oppdragsgiver:")
    pdf.cell(90, 6, "For Leverandor:")
    pdf.ln(20)

    pdf.cell(90, 0, "", border="T")
    pdf.cell(10)
    pdf.cell(80, 0, "", border="T")
    pdf.ln(5)

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(90, 6, "Kari Nordmann, Innkjopsdirektor")
    pdf.cell(90, 6, f"Kontaktperson, {k['leverandor_navn']}")
    pdf.ln(6)
    pdf.cell(90, 6, f"Dato: {k.get('startdato', '________')}")
    pdf.cell(90, 6, f"Dato: {k.get('startdato', '________')}")

    return pdf


def generer_alle():
    os.makedirs(CONTRACTS_DIR, exist_ok=True)
    init_db()

    kontrakter = hent_alle_kontrakter()
    print(f"Genererer PDF-er for {len(kontrakter)} kontrakter...\n")

    for k in kontrakter:
        filnavn = f"{k['kontrakt_nummer']}.pdf".replace("/", "-")
        filbane = os.path.join(CONTRACTS_DIR, filnavn)

        pdf = generer_kontrakt_pdf(k)
        pdf.output(filbane)
        oppdater_kontrakt_fil(k["id"], filnavn)
        print(f"  Generert: {filnavn} ({k['leverandor_navn']})")

    print(f"\nFerdig! {len(kontrakter)} kontrakt-PDF-er lagret i {CONTRACTS_DIR}/")


if __name__ == "__main__":
    generer_alle()
