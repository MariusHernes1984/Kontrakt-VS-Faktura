import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "kontrakter.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate_db(conn):
    """Legg til nye kolonner hvis de mangler."""
    cursor = conn.execute("PRAGMA table_info(kontrakter)")
    columns = {row[1] for row in cursor.fetchall()}
    for col, coltype, default in [
        ("kontakt_person", "TEXT", "''"),
        ("kontakt_epost", "TEXT", "''"),
        ("fil_path", "TEXT", "NULL"),
    ]:
        if col not in columns:
            conn.execute(
                f"ALTER TABLE kontrakter ADD COLUMN {col} {coltype} DEFAULT {default}"
            )
    conn.commit()


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS kontrakter (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            leverandor_navn TEXT NOT NULL,
            prosjekt_id TEXT,
            kontrakt_nummer TEXT UNIQUE,
            timepris REAL,
            maks_timer_per_maaned INTEGER,
            sla_responstid_timer INTEGER,
            avtalt_rabatt_prosent REAL DEFAULT 0,
            valuta TEXT DEFAULT 'NOK',
            startdato TEXT,
            sluttdato TEXT,
            beskrivelse TEXT,
            kontakt_person TEXT,
            kontakt_epost TEXT,
            fil_path TEXT,
            opprettet TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS faktura_logg (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filnavn TEXT NOT NULL,
            leverandor_navn TEXT,
            prosjekt_id TEXT,
            faktura_nummer TEXT,
            faktura_dato TEXT,
            forfallsdato TEXT,
            total_belop REAL,
            timepris REAL,
            antall_timer REAL,
            kontrakt_id INTEGER,
            status TEXT DEFAULT 'behandles',
            avvik_rapport TEXT,
            analysert TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kontrakt_id) REFERENCES kontrakter(id)
        );
    """)
    _migrate_db(conn)
    conn.commit()
    conn.close()


def oppdater_kontrakt_fil(kontrakt_id, fil_path):
    conn = get_db()
    conn.execute("UPDATE kontrakter SET fil_path = ? WHERE id = ?", (fil_path, kontrakt_id))
    conn.commit()
    conn.close()


def opprett_kontrakt(data):
    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO kontrakter
        (leverandor_navn, prosjekt_id, kontrakt_nummer, timepris,
         maks_timer_per_maaned, sla_responstid_timer, avtalt_rabatt_prosent,
         valuta, startdato, sluttdato, beskrivelse)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["leverandor_navn"],
        data.get("prosjekt_id", ""),
        data.get("kontrakt_nummer", ""),
        data.get("timepris", 0),
        data.get("maks_timer_per_maaned", 0),
        data.get("sla_responstid_timer", 0),
        data.get("avtalt_rabatt_prosent", 0),
        data.get("valuta", "NOK"),
        data.get("startdato", ""),
        data.get("sluttdato", ""),
        data.get("beskrivelse", ""),
    ))
    conn.commit()
    kontrakt_id = cursor.lastrowid
    conn.close()
    return kontrakt_id


def hent_alle_kontrakter():
    conn = get_db()
    rows = conn.execute("SELECT * FROM kontrakter ORDER BY leverandor_navn").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def hent_kontrakt(kontrakt_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM kontrakter WHERE id = ?", (kontrakt_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def slett_kontrakt(kontrakt_id):
    conn = get_db()
    conn.execute("DELETE FROM kontrakter WHERE id = ?", (kontrakt_id,))
    conn.commit()
    conn.close()


def sok_kontrakt(leverandor_navn=None, prosjekt_id=None):
    conn = get_db()
    query = "SELECT * FROM kontrakter WHERE 1=1"
    params = []

    if leverandor_navn:
        query += " AND LOWER(leverandor_navn) LIKE LOWER(?)"
        params.append(f"%{leverandor_navn}%")

    if prosjekt_id:
        query += " AND LOWER(prosjekt_id) LIKE LOWER(?)"
        params.append(f"%{prosjekt_id}%")

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def lagre_faktura_logg(data):
    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO faktura_logg
        (filnavn, leverandor_navn, prosjekt_id, faktura_nummer, faktura_dato,
         forfallsdato, total_belop, timepris, antall_timer, kontrakt_id,
         status, avvik_rapport)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["filnavn"],
        data.get("leverandor_navn", ""),
        data.get("prosjekt_id", ""),
        data.get("faktura_nummer", ""),
        data.get("faktura_dato", ""),
        data.get("forfallsdato", ""),
        data.get("total_belop", 0),
        data.get("timepris", 0),
        data.get("antall_timer", 0),
        data.get("kontrakt_id"),
        data.get("status", "behandles"),
        data.get("avvik_rapport", ""),
    ))
    conn.commit()
    logg_id = cursor.lastrowid
    conn.close()
    return logg_id


def hent_faktura_logg():
    conn = get_db()
    rows = conn.execute("""
        SELECT f.*, k.kontrakt_nummer, k.leverandor_navn as kontrakt_leverandor
        FROM faktura_logg f
        LEFT JOIN kontrakter k ON f.kontrakt_id = k.id
        ORDER BY f.analysert DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def hent_faktura(faktura_id):
    conn = get_db()
    row = conn.execute("""
        SELECT f.*, k.kontrakt_nummer, k.leverandor_navn as kontrakt_leverandor
        FROM faktura_logg f
        LEFT JOIN kontrakter k ON f.kontrakt_id = k.id
        WHERE f.id = ?
    """, (faktura_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
