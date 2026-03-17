# db.py
import sqlite3
import sys
import os
from pathlib import Path

if getattr(sys, 'frozen', False):
    # Running as EXE
    BASE_DIR = Path(sys.executable).parent
else:
    # Running as script
    BASE_DIR = Path(__file__).parent

DB_PATH = BASE_DIR / "f1_stats.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS seasons (
        season_id INTEGER PRIMARY KEY AUTOINCREMENT,
        year INTEGER UNIQUE NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS circuits (
        circuit_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT,
        country TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS races (
        race_id INTEGER PRIMARY KEY AUTOINCREMENT,
        season_id INTEGER NOT NULL,
        round INTEGER NOT NULL,
        name TEXT NOT NULL,
        circuit_id TEXT NOT NULL,
        date TEXT,
        FOREIGN KEY (season_id) REFERENCES seasons(season_id),
        FOREIGN KEY (circuit_id) REFERENCES circuits(circuit_id),
        UNIQUE (season_id, round)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS drivers (
        driver_id TEXT PRIMARY KEY,
        code TEXT,
        first_name TEXT,
        last_name TEXT
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS constructors (
        constructor_id TEXT PRIMARY KEY,
        name TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS race_results (
        result_id INTEGER PRIMARY KEY AUTOINCREMENT,
        race_id INTEGER NOT NULL,
        driver_id TEXT NOT NULL,
        constructor_id TEXT NOT NULL,
        grid_position INTEGER,
        finish_position INTEGER,
        status TEXT,
        points REAL,
        laps_completed INTEGER,
        time_text TEXT,
        fastest_lap_rank INTEGER,
        fastest_lap_time TEXT,
        FOREIGN KEY (race_id) REFERENCES races(race_id),
        FOREIGN KEY (driver_id) REFERENCES drivers(driver_id),
        FOREIGN KEY (constructor_id) REFERENCES constructors(constructor_id)
    );
    """)

    conn.commit()
    conn.close()


def get_seasons():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM seasons ORDER BY year DESC").fetchall()
    conn.close()
    return rows


def get_races_for_season(season_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT * FROM races
        WHERE season_id = ?
        ORDER BY round
    """, (season_id,)).fetchall()
    conn.close()
    return rows


def get_results_for_race(race_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            rr.finish_position,
            rr.grid_position,
            d.code AS driver_code,
            d.first_name || ' ' || d.last_name AS driver_name,
            c.name AS constructor_name,
            rr.points,
            rr.status,
            rr.laps_completed,
            rr.time_text,
            rr.fastest_lap_rank,
            rr.fastest_lap_time
        FROM race_results rr
        JOIN drivers d ON rr.driver_id = d.driver_id
        JOIN constructors c ON rr.constructor_id = c.constructor_id
        WHERE rr.race_id = ?
        ORDER BY rr.finish_position
    """, (race_id,)).fetchall()
    conn.close()
    return rows