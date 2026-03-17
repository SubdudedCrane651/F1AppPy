import os
import requests

#Red_Bull_Racing_logo.png
#Haas_F1_Team_logo.png

TEAMS = [
    "Red Bull",
    "AlphaTauri",
    "Alfa Romeo",
    "Ferrari",
    "Mercedes",
    "McLaren",
    "Aston Martin",
    "Alpine",
    "Williams",
    "RB",
    "Kick Sauber",
    "Haas"
]

RED_BULL_CANDIDATES = [
    "red-bull-racing-logo.png",
    "oracle-red-bull-racing-logo.png",
    "red-bull-logo.png",
    "red-bull.png",
    "red-bull-racing.png",
    "rbr-logo.png"
]

def slugify_team(team_name):
    return team_name.lower().replace(" ", "-")

def download_team_logos(season, output_dir="assets/team_logos"):
    os.makedirs(output_dir, exist_ok=True)

    for team in TEAMS:
        print(f"\nDownloading {team} logo…")

        if team == "Red Bull":
            # Try all known Red Bull filenames
            for candidate in RED_BULL_CANDIDATES:
                url = f"https://www.formula1.com/content/dam/fom-website/teams/{season}/{candidate}"
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    filename = f"{team.replace(' ', '_')}_logo.png"
                    path = os.path.join(output_dir, filename)
                    with open(path, "wb") as f:
                        f.write(response.content)
                    print(f"✔ Saved Red Bull logo using: {candidate}")
                    break
            else:
                print("❌ No Red Bull logo found for this season.")
            continue

        # Normal teams
        slug = slugify_team(team)
        url = f"https://www.formula1.com/content/dam/fom-website/teams/{season}/{slug}-logo.png"
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            print(f"❌ Failed ({response.status_code}) → {url}")
            continue

        filename = f"{team.replace(' ', '_')}_logo.png"
        path = os.path.join(output_dir, filename)

        with open(path, "wb") as f:
            f.write(response.content)

        print(f"✔ Saved: {path}")

    print("\nAll done!")

if __name__ == "__main__":
    download_team_logos(season=2024)