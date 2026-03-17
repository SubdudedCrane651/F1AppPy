from db import get_seasons, get_races_for_season

seasons = get_seasons()
print("Seasons in DB:")
for s in seasons:
    print("  ", s["year"])

print("\nRaces:")
for s in seasons:
    print(f"\nSeason {s['year']}:")
    races = get_races_for_season(s["season_id"])
    for r in races:
        print(f"  R{r['round']:02d} - {r['name']}")