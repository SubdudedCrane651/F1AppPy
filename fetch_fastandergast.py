import sqlite3
import fastf1
from fastf1.ergast import Ergast

# Enable FastF1 cache
fastf1.Cache.enable_cache("cache")

ergast = Ergast()


# ============================================================
#  DATABASE SETUP
# ============================================================

def init_db(db_path="f1data.db"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS race_results (
            year INTEGER,
            round INTEGER,
            position INTEGER,
            driver TEXT,
            constructor TEXT,
            time TEXT,
            status TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS driver_standings (
            year INTEGER,
            position INTEGER,
            driver TEXT,
            points REAL,
            wins INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS constructor_standings (
            year INTEGER,
            position INTEGER,
            constructor TEXT,
            points REAL,
            wins INTEGER
        )
    """)

    conn.commit()
    conn.close()


# ============================================================
#  YEAR ROUTING LOGIC
# ============================================================

def use_ergast(year: int) -> bool:
    return year <= 2022


# ============================================================
#  FETCH FUNCTIONS
# ============================================================

def get_driver_standings(year: int):
    result = ergast.get_driver_standings(season=year)
    return result.content[0].driver_standings


def get_constructor_standings(year: int):
    result = ergast.get_constructor_standings(season=year)
    return result.content[0].constructor_standings


def get_race_results(year: int, round_number: int):
    if use_ergast(year):
        result = ergast.get_race_results(season=year, round=round_number)
        return result.content[0].results
    else:
        session = fastf1.get_session(year, round_number, "R")
        session.load()
        return session.results


# ============================================================
#  INSERT INTO DATABASE
# ============================================================

def insert_driver_standings(year: int, db_path="f1data.db"):
    standings = get_driver_standings(year)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    for entry in standings:
        cur.execute("""
            INSERT INTO driver_standings (year, position, driver, points, wins)
            VALUES (?, ?, ?, ?, ?)
        """, (
            year,
            entry.position,
            f"{entry.driver.given_name} {entry.driver.family_name}",
            entry.points,
            entry.wins
        ))

    conn.commit()
    conn.close()


def insert_constructor_standings(year: int, db_path="f1data.db"):
    standings = get_constructor_standings(year)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    for entry in standings:
        cur.execute("""
            INSERT INTO constructor_standings (year, position, constructor, points, wins)
            VALUES (?, ?, ?, ?, ?)
        """, (
            year,
            entry.position,
            entry.constructor.name,
            entry.points,
            entry.wins
        ))

    conn.commit()
    conn.close()


def insert_race_results(year: int, round_number: int, db_path="f1data.db"):
    results = get_race_results(year, round_number)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    for entry in results:
        cur.execute("""
            INSERT INTO race_results (year, round, position, driver, constructor, time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            year,
            round_number,
            entry.position,
            f"{entry.driver.given_name} {entry.driver.family_name}",
            entry.constructor.name,
            getattr(entry, "time", None),
            entry.status
        ))

    conn.commit()
    conn.close()