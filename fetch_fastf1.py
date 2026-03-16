# fetch_fastf1.py
import fastf1
import pandas as pd
from db import get_connection, init_db

fastf1.Cache.enable_cache('cache')


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


def import_season(year: int):
    print(f"=== Importing season {year} ===")

    init_db()
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("INSERT OR IGNORE INTO seasons (year) VALUES (?)", (year,))
    conn.commit()

    cur.execute("SELECT season_id FROM seasons WHERE year = ?", (year,))
    season_id = cur.fetchone()["season_id"]

    print("Loading event schedule...")
    schedule = fastf1.get_event_schedule(year)

    print(schedule[["RoundNumber", "EventName", "EventDate"]])
    print(f"Found {len(schedule)} events")

    for _, event in schedule.iterrows():
        if str(event["EventFormat"]).lower() == "testing":
            continue

        round_num = int(event["RoundNumber"])
        race_name = event["EventName"]
        circuit_name = event["Location"]
        country = event["Country"]
        date = str(event["EventDate"])

        circuit_id = f"{circuit_name.replace(' ', '_').lower()}_{country.lower()}"

        print(f"Inserting race: Round {round_num} - {race_name}")

        cur.execute("""
            INSERT OR IGNORE INTO circuits (circuit_id, name, location, country)
            VALUES (?, ?, ?, ?)
        """, (circuit_id, circuit_name, circuit_name, country))

        cur.execute("""
            INSERT OR IGNORE INTO races (season_id, round, name, circuit_id, date)
            VALUES (?, ?, ?, ?, ?)
        """, (season_id, round_num, race_name, circuit_id, date))

    conn.commit()

    cur.execute("SELECT race_id, round FROM races WHERE season_id = ? ORDER BY round", (season_id,))
    races = cur.fetchall()

    print(f"Loading results for {len(races)} races...")

    for race in races:
        race_id = race["race_id"]
        round_num = race["round"]

        print(f"Loading session for Round {round_num}...")
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

            if pd.isna(fl_rank):
                fl_rank = None
            if pd.isna(fl_time):
                fl_time = None

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
    print(f"=== Season {year} import complete ===")


if __name__ == "__main__":
    try:
        year = int(input("Enter season year to import: "))
        import_season(year)
    except ValueError:
        print("Invalid year. Please enter a number like 2023.")