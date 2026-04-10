"""Fyller databasen med eksempelkontrakter for demo."""
from database import init_db, opprett_kontrakt

EKSEMPEL_KONTRAKTER = [
    {
        "leverandor_navn": "Leverandor 1 AS",
        "prosjekt_id": "PRJ-2024-001",
        "kontrakt_nummer": "K-2024-001",
        "timepris": 1250.00,
        "maks_timer_per_maaned": 160,
        "sla_responstid_timer": 4,
        "avtalt_rabatt_prosent": 0,
        "valuta": "NOK",
        "startdato": "2024-01-01",
        "sluttdato": "2026-12-31",
        "beskrivelse": "Rammeavtale for IT-konsulenttjenester, systemutvikling og drift.",
    },
    {
        "leverandor_navn": "Leverandor 2 AS",
        "prosjekt_id": "PRJ-2024-042",
        "kontrakt_nummer": "K-2024-015",
        "timepris": 1450.00,
        "maks_timer_per_maaned": 80,
        "sla_responstid_timer": 2,
        "avtalt_rabatt_prosent": 5,
        "valuta": "NOK",
        "startdato": "2024-03-01",
        "sluttdato": "2025-12-31",
        "beskrivelse": "Spesialistkonsulenter for skymigrering og DevOps.",
    },
    {
        "leverandor_navn": "Leverandor 3 AS",
        "prosjekt_id": "PRJ-SEC-100",
        "kontrakt_nummer": "K-2023-088",
        "timepris": 1600.00,
        "maks_timer_per_maaned": 40,
        "sla_responstid_timer": 1,
        "avtalt_rabatt_prosent": 0,
        "valuta": "NOK",
        "startdato": "2023-06-01",
        "sluttdato": "2026-06-30",
        "beskrivelse": "Sikkerhetstesting, penetrasjonstesting og sikkerhetsradgivning.",
    },
]


def seed():
    init_db()
    for kontrakt in EKSEMPEL_KONTRAKTER:
        try:
            opprett_kontrakt(kontrakt)
            print(f"Opprettet: {kontrakt['leverandor_navn']} ({kontrakt['kontrakt_nummer']})")
        except Exception as e:
            print(f"Finnes allerede eller feil: {kontrakt['kontrakt_nummer']} - {e}")
    print("\nFerdig! Eksempeldata er lagt inn.")


if __name__ == "__main__":
    seed()
