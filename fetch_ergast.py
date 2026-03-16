# fetch_ergast.py
import requests
from db import get_connection, init_db

ERGAST_BASE = "https://ergast.com/api/f1"


def _get_json(url: str):
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()


def import_season(year: int):
    """
    Imports:
      - season row
      - circuits
      - races
      - drivers, constructors, race_results for each race
    """
    init_db()
    conn = get_connection()
    cur = conn.cursor()

    # Insert season
    cur.execute("INSERT OR IGNORE INTO seasons (year) VALUES (?);", (year,))
    conn.commit()

    cur.execute("SELECT season_id FROM seasons WHERE year = ?;", (year,))
    season_id = cur.fetchone()["season_id"]

    # Get all races for the season
    url = f"{ERGAST_BASE}/{year}.json?limit=100"
    data = _get_json(url)
    races = data["MRData"]["RaceTable"]["Races"]

    for race in races:
        circuit = race["Circuit"]
        circuit_id = circuit["circuitId"]
        circuit_name = circuit["circuitName"]
        location = circuit["Location"]["locality"]
        country = circuit["Location"]["country"]

        # Insert circuit
        cur.execute("""
            INSERT OR IGNORE INTO circuits (circuit_id, name, location, country)
            VALUES (?, ?, ?, ?);
        """, (circuit_id, circuit_name, location, country))

        # Insert race
        round_num = int(race["round"])
        race_name = race["raceName"]
        date = race.get("date")
        time = race.get("time")

        cur.execute("""
            INSERT OR IGNORE INTO races (season_id, round, name, circuit_id, date, time)
            VALUES (?, ?, ?, ?, ?, ?);
        """, (season_id, round_num, race_name, circuit_id, date, time))

    conn.commit()

    # Now fetch results for each race
    cur.execute("SELECT race_id, round FROM races WHERE season_id = ?;", (season_id,))
    race_rows = cur.fetchall()

    for race_row in race_rows:
        race_id = race_row["race_id"]
        round_num = race_row["round"]

        print(f"Importing results for {year} round {round_num}...")
        url = f"{ERGAST_BASE}/{year}/{round_num}/results.json?limit=100"
        data = _get_json(url)
        races_data = data["MRData"]["RaceTable"]["Races"]
        if not races_data:
            continue
        race_data = races_data[0]
        results = race_data["Results"]

        for res in results:
            driver = res["Driver"]
            constructor = res["Constructor"]

            driver_id = driver["driverId"]
            code = driver.get("code")
            first_name = driver["givenName"]
            last_name = driver["familyName"]
            dob = driver.get("dateOfBirth")
            nationality = driver.get("nationality")

            # Insert driver
            cur.execute("""
                INSERT OR IGNORE INTO drivers (driver_id, code, first_name, last_name, dob, nationality)
                VALUES (?, ?, ?, ?, ?, ?);
            """, (driver_id, code, first_name, last_name, dob, nationality))

            constructor_id = constructor["constructorId"]
            constructor_name = constructor["name"]
            constructor_nat = constructor.get("nationality")

            # Insert constructor
            cur.execute("""
                INSERT OR IGNORE INTO constructors (constructor_id, name, nationality)
                VALUES (?, ?, ?);
            """, (constructor_id, constructor_name, constructor_nat))

            grid = int(res.get("grid", 0) or 0)
            position_text = res.get("positionText")
            try:
                finish_position = int(res.get("position", 0) or 0)
            except ValueError:
                finish_position = None

            status = res.get("status")
            points = float(res.get("points", 0.0) or 0.0)
            laps = int(res.get("laps", 0) or 0)
            time_info = res.get("Time")
            time_text = time_info["time"] if time_info else None

            fastest_lap = res.get("FastestLap")
            if fastest_lap:
                fl_rank = int(fastest_lap.get("rank", 0) or 0)
                fl_time = fastest_lap["Time"]["time"]
            else:
                fl_rank = None
                fl_time = None

            cur.execute("""
                INSERT OR REPLACE INTO race_results (
                    race_id, driver_id, constructor_id,
                    grid_position, finish_position, status,
                    points, laps_completed, time_text,
                    fastest_lap_rank, fastest_lap_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                race_id, driver_id, constructor_id,
                grid, finish_position, status,
                points, laps, time_text,
                fl_rank, fl_time
            ))

    conn.commit()
    conn.close()
    print(f"Season {year} imported.")


if __name__ == "__main__":
    # Example: import 2023 season
    import_season(2023)