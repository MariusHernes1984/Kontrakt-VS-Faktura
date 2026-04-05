"""
Genererer 48 realistiske faktura-PDF-er fordelt pa 13 kontrakter.
7 av 48 har avvik (feil timepris, for mange timer, utlopt kontrakt, etc.)
"""
import os
import json
import random
from fpdf import FPDF
from database import (
    init_db, hent_alle_kontrakter, hent_kontrakt,
    lagre_faktura_logg
)
from validator import valider_faktura_mot_kontrakt

INVOICES_DIR = os.path.join(os.path.dirname(__file__), "uploads")

# Fordeling: 48 fakturaer pa 13 kontrakter
# Kontrakter med mye aktivitet far flere fakturaer
FAKTURA_PLAN = [
    # (kontrakt_id, maneder_liste, avvik_maned_eller_None)
    # --- Bouvet ASA K-2025-101: 6 fakturaer (jan-jun 2025) ---
    (4, ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06"], "2025-04"),
    # --- Bouvet ASA K-2025-102: 4 fakturaer (mar-jun 2025) ---
    (5, ["2025-03", "2025-04", "2025-05", "2025-06"], None),
    # --- Nordic Consulting K-2024-001: 6 fakturaer (okt 2025 - mar 2026) ---
    (1, ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03"], "2026-01"),
    # --- TechPartner Norge K-2024-015: 3 fakturaer (okt-des 2025) - UTLOPT ---
    (2, ["2025-10", "2025-11", "2025-12"], None),
    # --- DataSikkerhet K-2023-088: 4 fakturaer (jan-apr 2026) ---
    (3, ["2026-01", "2026-02", "2026-03", "2026-04"], "2026-03"),
    # --- Sopra Steria K-2024-201: 5 fakturaer (nov 2025 - mar 2026) ---
    (6, ["2025-11", "2025-12", "2026-01", "2026-02", "2026-03"], None),
    # --- Capgemini K-2024-301: 4 fakturaer (des 2025 - mar 2026) ---
    (7, ["2025-12", "2026-01", "2026-02", "2026-03"], "2026-02"),
    # --- Capgemini K-2025-302: 3 fakturaer (jan-mar 2026) ---
    (8, ["2026-01", "2026-02", "2026-03"], None),
    # --- Knowit K-2024-401: 4 fakturaer (des 2025 - mar 2026) ---
    (9, ["2025-12", "2026-01", "2026-02", "2026-03"], "2026-03"),
    # --- Accenture K-2025-501: 3 fakturaer (jan-mar 2026) ---
    (10, ["2026-01", "2026-02", "2026-03"], None),
    # --- Visma Consulting K-2024-601: 3 fakturaer (jan-apr 2026) - avvik: apr er etter utlop ---
    (11, ["2026-01", "2026-02", "2026-04"], "2026-04"),
    # --- Visma Consulting K-2025-602: 2 fakturaer (feb-mar 2026) ---
    (12, ["2026-02", "2026-03"], None),
    # --- Itera K-2025-701: 1 faktura (apr 2026, forste maned) ---
    (13, ["2026-01"], "2026-01"),
]

# Avviks-typer for de 7 avvikene
AVVIK_TYPER = {
    # kontrakt_id: (type, beskrivelse)
    4:  ("hoy_timepris", "Timepris 150 kr over avtalt"),
    1:  ("for_mange_timer", "185 timer fakturert, maks 160"),
    3:  ("hoy_timepris", "Timepris 200 kr over avtalt"),
    7:  ("for_mange_timer", "132 timer fakturert, maks 100"),
    9:  ("bade_pris_og_timer", "Timepris 100 kr for hoy + 155 timer (maks 140)"),
    11: ("utlopt_kontrakt", "Fakturadato etter kontraktens utlopsdato"),
    13: ("hoy_timepris", "Timepris 320 kr over avtalt (1600 vs 1280)"),
}

NORSKE_MANEDER = {
    "01": "januar", "02": "februar", "03": "mars", "04": "april",
    "05": "mai", "06": "juni", "07": "juli", "08": "august",
    "09": "september", "10": "oktober", "11": "november", "12": "desember",
}

KONSULENT_NAVN = [
    "Erik Hansen", "Maria Johansen", "Thomas Berg", "Ingrid Larsen",
    "Kristian Olsen", "Silje Pedersen", "Anders Nilsen", "Hanne Kristiansen",
    "Lars Andersen", "Camilla Haugen", "Morten Dahl", "Ane Solberg",
    "Petter Moen", "Lise Henriksen", "Vegard Strand",
]

random.seed(42)  # Reproduserbar
faktura_teller = 1000


class FakturaPDF(FPDF):
    def __init__(self, kontrakt, faktura_nr):
        super().__init__()
        self.kontrakt = kontrakt
        self.faktura_nr = faktura_nr

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, f"Faktura {self.faktura_nr}", align="R")
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Side {self.page_no()}", align="C")


def dager_i_maned(year, month):
    import calendar
    return calendar.monthrange(year, month)[1]


def generer_faktura(kontrakt, maned_str, er_avvik, avvik_type=None):
    global faktura_teller
    faktura_teller += 1

    k = kontrakt
    ar, maned = maned_str.split("-")
    ar_int, maned_int = int(ar), int(maned)
    maned_navn = NORSKE_MANEDER[maned]
    siste_dag = dager_i_maned(ar_int, maned_int)

    faktura_nr = f"F-{ar}-{faktura_teller}"
    faktura_dato = f"{ar}-{maned}-{min(28, siste_dag):02d}"
    forfalls_dag = min(28, siste_dag)
    neste_maned = maned_int + 1
    neste_ar = ar_int
    if neste_maned > 12:
        neste_maned = 1
        neste_ar += 1
    forfallsdato = f"{neste_ar}-{neste_maned:02d}-{forfalls_dag:02d}"

    # Beregn timer og priser
    maks_timer = k["maks_timer_per_maaned"]
    normal_timer = random.randint(int(maks_timer * 0.6), int(maks_timer * 0.9))
    timepris = k["timepris"]
    rabatt = k.get("avtalt_rabatt_prosent", 0)

    # Avvik-justeringer
    if er_avvik and avvik_type:
        if avvik_type == "hoy_timepris":
            if k["id"] == 4:
                timepris = k["timepris"] + 150
            elif k["id"] == 3:
                timepris = k["timepris"] + 200
            elif k["id"] == 13:
                timepris = k["timepris"] + 320
        elif avvik_type == "for_mange_timer":
            if k["id"] == 1:
                normal_timer = 185
            elif k["id"] == 7:
                normal_timer = 132
        elif avvik_type == "bade_pris_og_timer":
            timepris = k["timepris"] + 100
            normal_timer = 155
        elif avvik_type == "utlopt_kontrakt":
            # Kontrakten utloper 2026-03-31, fakturaen er for april
            pass  # Dato er allerede riktig satt

    antall_timer = normal_timer

    # Velg 1-3 konsulenter
    antall_konsulenter = random.randint(1, min(3, max(1, antall_timer // 40)))
    konsulenter = random.sample(KONSULENT_NAVN, antall_konsulenter)
    timer_per_konsulent = []
    gjenstaaende = antall_timer
    for i in range(antall_konsulenter):
        if i == antall_konsulenter - 1:
            timer_per_konsulent.append(gjenstaaende)
        else:
            t = random.randint(int(gjenstaaende * 0.3), int(gjenstaaende * 0.6))
            timer_per_konsulent.append(t)
            gjenstaaende -= t

    # Beregn belop
    brutto = timepris * antall_timer
    rabatt_belop = brutto * (rabatt / 100)
    netto = brutto - rabatt_belop
    mva = netto * 0.25
    total = netto + mva

    # --- Generer PDF ---
    pdf = FakturaPDF(k, faktura_nr)
    pdf.add_page()

    # Leverandor-header
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 10, k["leverandor_navn"])
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, "Konsulenttjenester og IT-radgivning")
    pdf.ln(15)

    # FAKTURA tittel
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(26, 86, 219)
    pdf.cell(0, 12, "FAKTURA")
    pdf.ln(15)

    # Fakturadetaljer
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(45, 7, "Fakturanummer:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(60, 7, faktura_nr)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(35, 7, "Kundenavn:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, "Statens Innkjopssenter")
    pdf.ln(7)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(45, 7, "Fakturadato:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(60, 7, faktura_dato)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(35, 7, "Org.nr:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, "986 252 932")
    pdf.ln(7)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(45, 7, "Forfallsdato:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(60, 7, forfallsdato)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(35, 7, "Var ref:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, k["kontrakt_nummer"])
    pdf.ln(7)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(45, 7, "Prosjekt-ID:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(60, 7, k.get("prosjekt_id", ""))
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(35, 7, "Periode:")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, f"{maned_navn} {ar}")
    pdf.ln(15)

    # Linjebeskrivelse
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, f"Konsulenttjenester - {maned_navn} {ar}")
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Ref: {k['kontrakt_nummer']} / {k.get('prosjekt_id', '')}")
    pdf.ln(10)

    # Tabell-header
    pdf.set_text_color(30, 30, 30)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(240, 240, 245)
    pdf.cell(70, 8, "Beskrivelse", border=1, fill=True)
    pdf.cell(30, 8, "Konsulent", border=1, fill=True)
    pdf.cell(25, 8, "Timer", border=1, fill=True, align="R")
    pdf.cell(30, 8, "Timepris", border=1, fill=True, align="R")
    pdf.cell(35, 8, "Belop", border=1, fill=True, align="R")
    pdf.ln(8)

    # Linjer per konsulent
    pdf.set_font("Helvetica", "", 9)
    roller = [
        "Systemutvikling", "Arkitekturarbeid", "Teknisk radgivning",
        "Prosjektledelse", "Testledelse", "Kodegjennomgang",
        "Drift og forvaltning", "Integrasjonsarbeid",
    ]
    for i, (konsulent, timer) in enumerate(zip(konsulenter, timer_per_konsulent)):
        rolle = roller[i % len(roller)]
        belop = timer * timepris
        pdf.cell(70, 7, rolle, border=1)
        pdf.cell(30, 7, konsulent.split()[0], border=1)
        pdf.cell(25, 7, f"{timer:.1f}", border=1, align="R")
        pdf.cell(30, 7, f"{timepris:,.2f}", border=1, align="R")
        pdf.cell(35, 7, f"{belop:,.2f}", border=1, align="R")
        pdf.ln(7)

    pdf.ln(5)

    # Summering
    pdf.set_font("Helvetica", "", 10)
    x_label = 125
    x_val = 155
    w_val = 35

    pdf.set_x(x_label)
    pdf.cell(30, 7, "Sum timer:", align="R")
    pdf.cell(w_val, 7, f"{antall_timer:.1f}", align="R")
    pdf.ln(7)

    pdf.set_x(x_label)
    pdf.cell(30, 7, "Timepris:", align="R")
    pdf.cell(w_val, 7, f"{timepris:,.2f} NOK", align="R")
    pdf.ln(7)

    pdf.set_x(x_label)
    pdf.cell(30, 7, "Brutto:", align="R")
    pdf.cell(w_val, 7, f"{brutto:,.2f} NOK", align="R")
    pdf.ln(7)

    if rabatt > 0:
        pdf.set_x(x_label)
        pdf.cell(30, 7, f"Rabatt ({rabatt:.0f}%):", align="R")
        pdf.cell(w_val, 7, f"-{rabatt_belop:,.2f} NOK", align="R")
        pdf.ln(7)

    pdf.set_x(x_label)
    pdf.cell(30, 7, "Netto:", align="R")
    pdf.cell(w_val, 7, f"{netto:,.2f} NOK", align="R")
    pdf.ln(7)

    pdf.set_x(x_label)
    pdf.cell(30, 7, "MVA (25%):", align="R")
    pdf.cell(w_val, 7, f"{mva:,.2f} NOK", align="R")
    pdf.ln(7)

    pdf.set_font("Helvetica", "B", 11)
    pdf.set_x(x_label)
    pdf.cell(30, 8, "Totalt:", align="R")
    pdf.cell(w_val, 8, f"{total:,.2f} NOK", align="R")
    pdf.ln(15)

    # Betalingsinfo
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 8, "Betalingsinformasjon")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(35, 6, "Kontonummer:")
    pdf.cell(0, 6, f"1234 56 {random.randint(10000, 99999)}")
    pdf.ln(6)
    pdf.cell(35, 6, "KID-nummer:")
    pdf.cell(0, 6, f"{random.randint(100000, 999999)}")
    pdf.ln(6)
    pdf.cell(35, 6, "Betalingsfrist:")
    pdf.cell(0, 6, f"30 dager ({forfallsdato})")
    pdf.ln(6)
    pdf.cell(35, 6, "Org.nr:")
    pdf.cell(0, 6, f"9{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}")

    # Lagre PDF
    filnavn = f"{faktura_nr}.pdf"
    filbane = os.path.join(INVOICES_DIR, filnavn)
    pdf.output(filbane)

    # Returner data for database
    return {
        "filnavn": filnavn,
        "leverandor_navn": k["leverandor_navn"],
        "prosjekt_id": k.get("prosjekt_id", ""),
        "faktura_nummer": faktura_nr,
        "faktura_dato": faktura_dato,
        "forfallsdato": forfallsdato,
        "total_belop": total,
        "timepris": timepris,
        "antall_timer": antall_timer,
        "kontrakt_id": k["id"],
        "er_avvik": er_avvik,
        "avvik_type": avvik_type,
        "netto": netto,
        "mva": mva,
        "rabatt_belop": rabatt_belop,
    }


def generer_alle():
    os.makedirs(INVOICES_DIR, exist_ok=True)
    init_db()

    alle_kontrakter = {k["id"]: k for k in hent_alle_kontrakter()}
    resultater = []
    total = 0

    print("Genererer 48 fakturaer...\n")

    for kontrakt_id, maneder, avvik_maned in FAKTURA_PLAN:
        k = alle_kontrakter[kontrakt_id]
        avvik_info = AVVIK_TYPER.get(kontrakt_id)

        for maned_str in maneder:
            er_avvik = (avvik_maned is not None and maned_str == avvik_maned)
            avvik_type = avvik_info[0] if er_avvik and avvik_info else None

            data = generer_faktura(k, maned_str, er_avvik, avvik_type)
            resultater.append(data)
            total += 1

            # Valider mot kontrakt
            faktura_data = {
                "leverandor_navn": data["leverandor_navn"],
                "prosjekt_id": data["prosjekt_id"],
                "faktura_nummer": data["faktura_nummer"],
                "faktura_dato": data["faktura_dato"],
                "forfallsdato": data["forfallsdato"],
                "total_belop": data["netto"],  # eks mva for sammenligning
                "total_eks_mva": data["netto"],
                "timepris": data["timepris"],
                "antall_timer": data["antall_timer"],
            }
            valresultat = valider_faktura_mot_kontrakt(faktura_data, k)

            status = valresultat["status"]

            logg_data = {
                "filnavn": data["filnavn"],
                "leverandor_navn": data["leverandor_navn"],
                "prosjekt_id": data["prosjekt_id"],
                "faktura_nummer": data["faktura_nummer"],
                "faktura_dato": data["faktura_dato"],
                "forfallsdato": data["forfallsdato"],
                "total_belop": data["total_belop"],
                "timepris": data["timepris"],
                "antall_timer": data["antall_timer"],
                "kontrakt_id": kontrakt_id,
                "status": status,
                "avvik_rapport": json.dumps(valresultat, ensure_ascii=False, default=str),
            }
            lagre_faktura_logg(logg_data)

            avvik_flag = " ** AVVIK **" if er_avvik else ""
            print(f"  {data['faktura_nummer']} | {k['leverandor_navn']:<25} | {maned_str} | "
                  f"{data['antall_timer']:.0f}t x {data['timepris']:.0f} kr | "
                  f"Total: {data['total_belop']:>12,.2f} NOK | "
                  f"Status: {status}{avvik_flag}")

    antall_avvik = sum(1 for r in resultater if r["er_avvik"])
    print(f"\nFerdig! {total} fakturaer generert ({antall_avvik} med avvik)")
    print(f"PDF-er lagret i: {INVOICES_DIR}/")


if __name__ == "__main__":
    generer_alle()
