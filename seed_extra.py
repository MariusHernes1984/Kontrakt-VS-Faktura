"""Legger til 10 nye kontrakter fra 7 forskjellige selskaper."""
from database import init_db, opprett_kontrakt

NYE_KONTRAKTER = [
    {
        "leverandor_navn": "Bouvet ASA",
        "prosjekt_id": "PRJ-BOUV-301",
        "kontrakt_nummer": "K-2025-101",
        "timepris": 1350.00,
        "maks_timer_per_maaned": 200,
        "sla_responstid_timer": 4,
        "avtalt_rabatt_prosent": 3,
        "valuta": "NOK",
        "startdato": "2025-01-01",
        "sluttdato": "2027-12-31",
        "beskrivelse": "Systemutvikling Java/.NET for kjernesystemer.",
    },
    {
        "leverandor_navn": "Bouvet ASA",
        "prosjekt_id": "PRJ-BOUV-302",
        "kontrakt_nummer": "K-2025-102",
        "timepris": 1200.00,
        "maks_timer_per_maaned": 120,
        "sla_responstid_timer": 8,
        "avtalt_rabatt_prosent": 0,
        "valuta": "NOK",
        "startdato": "2025-03-01",
        "sluttdato": "2026-12-31",
        "beskrivelse": "Testledelse og kvalitetssikring.",
    },
    {
        "leverandor_navn": "Sopra Steria AS",
        "prosjekt_id": "PRJ-SOPRA-010",
        "kontrakt_nummer": "K-2024-201",
        "timepris": 1500.00,
        "maks_timer_per_maaned": 160,
        "sla_responstid_timer": 2,
        "avtalt_rabatt_prosent": 5,
        "valuta": "NOK",
        "startdato": "2024-06-01",
        "sluttdato": "2027-05-31",
        "beskrivelse": "Rammeavtale skymigrering og infrastruktur Azure.",
    },
    {
        "leverandor_navn": "Capgemini Norge AS",
        "prosjekt_id": "PRJ-CAP-055",
        "kontrakt_nummer": "K-2024-301",
        "timepris": 1400.00,
        "maks_timer_per_maaned": 100,
        "sla_responstid_timer": 4,
        "avtalt_rabatt_prosent": 8,
        "valuta": "NOK",
        "startdato": "2024-09-01",
        "sluttdato": "2026-08-31",
        "beskrivelse": "SAP-konsulenttjenester, moduler FI/CO og MM.",
    },
    {
        "leverandor_navn": "Capgemini Norge AS",
        "prosjekt_id": "PRJ-CAP-060",
        "kontrakt_nummer": "K-2025-302",
        "timepris": 1550.00,
        "maks_timer_per_maaned": 80,
        "sla_responstid_timer": 2,
        "avtalt_rabatt_prosent": 0,
        "valuta": "NOK",
        "startdato": "2025-02-01",
        "sluttdato": "2026-07-31",
        "beskrivelse": "AI/ML-radgivning og modellutvikling.",
    },
    {
        "leverandor_navn": "Knowit AS",
        "prosjekt_id": "PRJ-KNO-200",
        "kontrakt_nummer": "K-2024-401",
        "timepris": 1300.00,
        "maks_timer_per_maaned": 140,
        "sla_responstid_timer": 4,
        "avtalt_rabatt_prosent": 2,
        "valuta": "NOK",
        "startdato": "2024-01-15",
        "sluttdato": "2026-12-31",
        "beskrivelse": "Frontend-utvikling React/TypeScript, designsystem.",
    },
    {
        "leverandor_navn": "Accenture Norway AS",
        "prosjekt_id": "PRJ-ACC-777",
        "kontrakt_nummer": "K-2025-501",
        "timepris": 1750.00,
        "maks_timer_per_maaned": 60,
        "sla_responstid_timer": 1,
        "avtalt_rabatt_prosent": 0,
        "valuta": "NOK",
        "startdato": "2025-01-01",
        "sluttdato": "2027-06-30",
        "beskrivelse": "Strategisk IT-radgivning og virksomhetsarkitektur.",
    },
    {
        "leverandor_navn": "Visma Consulting AS",
        "prosjekt_id": "PRJ-VIS-090",
        "kontrakt_nummer": "K-2024-601",
        "timepris": 1150.00,
        "maks_timer_per_maaned": 180,
        "sla_responstid_timer": 4,
        "avtalt_rabatt_prosent": 10,
        "valuta": "NOK",
        "startdato": "2024-04-01",
        "sluttdato": "2026-03-31",
        "beskrivelse": "Drift og forvaltning av fagsystemer, 2. og 3. linje support.",
    },
    {
        "leverandor_navn": "Visma Consulting AS",
        "prosjekt_id": "PRJ-VIS-091",
        "kontrakt_nummer": "K-2025-602",
        "timepris": 1250.00,
        "maks_timer_per_maaned": 100,
        "sla_responstid_timer": 2,
        "avtalt_rabatt_prosent": 5,
        "valuta": "NOK",
        "startdato": "2025-01-01",
        "sluttdato": "2027-12-31",
        "beskrivelse": "Integrasjonsplattform og API-utvikling.",
    },
    {
        "leverandor_navn": "Itera ASA",
        "prosjekt_id": "PRJ-ITE-150",
        "kontrakt_nummer": "K-2025-701",
        "timepris": 1280.00,
        "maks_timer_per_maaned": 120,
        "sla_responstid_timer": 4,
        "avtalt_rabatt_prosent": 0,
        "valuta": "NOK",
        "startdato": "2025-04-01",
        "sluttdato": "2027-03-31",
        "beskrivelse": "UX-design og tjenestedesign, brukerinnsikt og prototyping.",
    },
]


def seed():
    init_db()
    for kontrakt in NYE_KONTRAKTER:
        try:
            opprett_kontrakt(kontrakt)
            print(f"Opprettet: {kontrakt['leverandor_navn']} ({kontrakt['kontrakt_nummer']})")
        except Exception as e:
            print(f"Finnes allerede eller feil: {kontrakt['kontrakt_nummer']} - {e}")
    print(f"\nFerdig! {len(NYE_KONTRAKTER)} kontrakter forsøkt lagt inn.")


if __name__ == "__main__":
    seed()
