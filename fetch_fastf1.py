# fetch_fastf1.py
import shutil
import os
from pathlib import Path

# ============================================================
#  FORCE DELETE ALL POSSIBLE CORRUPTED CACHES BEFORE ANYTHING
# ============================================================

LOCAL = Path(os.getenv("LOCALAPPDATA"))

POSSIBLE_CACHES = [
    LOCAL / "requests_cache",
    LOCAL / "F1StatsExplorer" / "cache",
]

for cache_path in POSSIBLE_CACHES:
    if cache_path.exists():
        try:
            shutil.rmtree(cache_path)
            print(f"[CACHE CLEAN] Deleted: {cache_path}")
        except Exception as e:
            print(f"[CACHE CLEAN] Could not delete {cache_path}: {e}")

# ============================================================
#  NOW IMPORT FASTF1 SAFELY
# ============================================================

import fastf1
import pandas as pd
from fastf1.ergast import Ergast
from db import get_connection, init_db

# Recreate clean cache folder
CACHE_DIR = LOCAL / "F1StatsExplorer" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

fastf1.Cache.enable_cache(str(CACHE_DIR))
ergast = Ergast()


# ============================================================
#  HELPERS
# ============================================================

def safe_int(value):
    try:
        if value is None or pd.isna(value):
            return None
        return int(value)
    except:
        return None

def safe_str(value):
    try:
        if value is None or pd.isna(value):
            return None
        return str(value)
    except:
        return None


# ============================================================
#  YEAR ROUTING
# ============================================================

def use_ergast(year: int) -> bool:
    return year <= 2022


# ============================================================
#  MAIN IMPORT FUNCTION
# ============================================================

def import_season(year: int):
    print(f"=== Importing season {year} ===")

    init_db()
    conn = get_connection()
    cur = conn.cursor()

    # Insert season
    cur.execute("INSERT OR IGNORE INTO seasons (year) VALUES (?)", (year,))
    conn.commit()

    cur.execute("SELECT season_id FROM seasons WHERE year = ?", (year,))
    season_id = cur.fetchone()["season_id"]

    # ============================================================
    #  MODE 1: ERGAST (<=2022)
    # ============================================================

    if use_ergast(year):
        print("Using ERGAST mode for this season")

        # ------------------------------------------------------------
        # 1. Load schedule (DataFrame)
        # ------------------------------------------------------------
        schedule = ergast.get_race_schedule(season=year)
        print("ERGAST SCHEDULE COLUMNS:", list(schedule.columns))

        # Insert schedule into DB
        for _, event in schedule.iterrows():
            round_num = int(event["round"])
            race_name = event["raceName"]
            circuit_name = event["circuitName"]
            country = event["country"]
            date = event["raceDate"]

            circuit_id = f"{circuit_name.replace(' ', '_').lower()}_{country.lower()}"

            cur.execute("""
                INSERT OR IGNORE INTO circuits (circuit_id, name, location, country)
                VALUES (?, ?, ?, ?)
            """, (circuit_id, circuit_name, circuit_name, country))

            cur.execute("""
                INSERT OR IGNORE INTO races (season_id, round, name, circuit_id, date)
                VALUES (?, ?, ?, ?, ?)
            """, (season_id, round_num, race_name, circuit_id, str(date)))

        conn.commit()

        # ------------------------------------------------------------
        # 2. Fetch results PER ROUND
        # ------------------------------------------------------------
        for _, event in schedule.iterrows():
            round_num = int(event["round"])
            race_name = event["raceName"]

            print(f"Fetching results for round {round_num}: {race_name}")

            # Fetch results for this round
            response = ergast.get_race_results(season=year, round=round_num)

            # Your version returns a list of ErgastResultFrame in .content
            df = response.content[0]

            print("RESULT COLUMNS:", list(df.columns))
            print("FULL RESULT ROW:", df.iloc[0])

            # Get race_id from DB
            cur.execute(
                "SELECT race_id FROM races WHERE season_id = ? AND round = ?",
                (season_id, round_num),
            )
            race_id = cur.fetchone()["race_id"]

            # ------------------------------------------------------------
            # 3. Insert results (ALL SAFE — NO DIRECT INDEXING)
            # ------------------------------------------------------------
            for _, r in df.iterrows():

                # Driver fields (flat)
                driver_id = r.get("driverId")
                code = r.get("driverCode")
                first_name = r.get("givenName")
                last_name = r.get("familyName")

                # Constructor fields (flat)
                constructor_id = r.get("constructorId")
                constructor_name = r.get("constructorName")

                # Insert driver
                cur.execute("""
                    INSERT OR IGNORE INTO drivers (driver_id, code, first_name, last_name)
                    VALUES (?, ?, ?, ?)
                """, (driver_id, code, first_name, last_name))

                # Insert constructor
                cur.execute("""
                    INSERT OR IGNORE INTO constructors (constructor_id, name)
                    VALUES (?, ?)
                """, (constructor_id, constructor_name))

                # Insert race result (ALL fields safe)
                cur.execute("""
                    INSERT OR REPLACE INTO race_results (
                        race_id, driver_id, constructor_id,
                        grid_position, finish_position, status,
                        points, laps_completed, time_text,
                        fastest_lap_rank, fastest_lap_time
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    race_id,
                    driver_id,
                    constructor_id,
                    safe_int(r.get("grid")),
                    safe_int(r.get("position")),
                    safe_str(r.get("status")),
                    float(r.get("points", 0)),
                    safe_int(r.get("laps")),
                    safe_str(r.get("totalRaceTime")),
                    safe_int(r.get("fastestLapRank")),   # SAFE
                    safe_str(r.get("fastestLapTime")),   # SAFE
                ))

        conn.commit()
        conn.close()
        print(f"=== Season {year} import complete (ERGAST) ===")
        return
    
    # ============================================================
    #  MODE 2: FASTF1 (>=2023)
    # ============================================================

    print("Using FASTF1 mode for this season")

    schedule = fastf1.get_event_schedule(year)

    for _, event in schedule.iterrows():
        if str(event["EventFormat"]).lower() == "testing":
            continue

        round_num = int(event["RoundNumber"])
        race_name = event["EventName"]
        circuit_name = event["Location"]
        country = event["Country"]
        date = str(event["EventDate"])

        circuit_id = f"{circuit_name.replace(' ', '_').lower()}_{country.lower()}"

        cur.execute("""
            INSERT OR IGNORE INTO circuits (circuit_id, name, location, country)
            VALUES (?, ?, ?, ?)
        """, (circuit_id, circuit_name, circuit_name, country))

        cur.execute("""
            INSERT OR IGNORE INTO races (season_id, round, name, circuit_id, date)
            VALUES (?, ?, ?, ?, ?)
        """, (season_id, round_num, race_name, circuit_id, date))

    conn.commit()

    # Load race results
    cur.execute("SELECT race_id, round FROM races WHERE season_id = ? ORDER BY round", (season_id,))
    races = cur.fetchall()

    for race in races:
        race_id = race["race_id"]
        round_num = race["round"]

        session = fastf1.get_session(year, round_num, 'R')
        session.load()

        results = session.results

        for _, r in results.iterrows():
            driver_id = str(r["DriverNumber"])
            code = r["Abbreviation"]
            first_name = r["FirstName"]
            last_name = r["LastName"]
            constructor_name = r["TeamName"]
            constructor_id = constructor_name.replace(" ", "_").lower()

            cur.execute("""
                INSERT OR IGNORE INTO drivers (driver_id, code, first_name, last_name)
                VALUES (?, ?, ?, ?)
            """, (driver_id, code, first_name, last_name))

            cur.execute("""
                INSERT OR IGNORE INTO constructors (constructor_id, name)
                VALUES (?, ?)
            """, (constructor_id, constructor_name))

            fl_rank = r.get("FastestLapRank", None)
            fl_time = r.get("FastestLapTime", None)

            if pd.isna(fl_rank): fl_rank = None
            if pd.isna(fl_time): fl_time = None

            cur.execute("""
                INSERT OR REPLACE INTO race_results (
                    race_id, driver_id, constructor_id,
                    grid_position, finish_position, status,
                    points, laps_completed, time_text,
                    fastest_lap_rank, fastest_lap_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                race_id,
                driver_id,
                constructor_id,
                safe_int(r["GridPosition"]),
                safe_int(r["Position"]),
                safe_str(r["Status"]),
                float(r["Points"]),
                safe_int(r["Laps"]),
                safe_str(r["Time"]),
                fl_rank,
                fl_time
            ))

    conn.commit()
    conn.close()
    print(f"=== Season {year} import complete (FASTF1) ===")


# ============================================================
#  INPUT (same as your original code)
# ============================================================

if __name__ == "__main__":
    try:
        year = int(input("Enter season year to import: "))
        import_season(year)
    except ValueError:
        print("Invalid year. Please enter a number like 2023.")