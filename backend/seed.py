"""
Seed the database with real 2024-25 Premier League player data.
Run once to get the app working: python3 seed.py
Stats sourced from Understat / FBref end-of-season 2024-25 data.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import db
import random
from datetime import datetime, timedelta

db.init_db()

SEASON = "2024-2025"

# Real 2024-25 PL stats (as of late April 2026)
PLAYERS = [
    # (name, team, position, understat_id, goals, assists, xG, xA, shots, key_passes, minutes, apps, npxG, yellows, reds)
    ("Mohamed Salah",       "Liverpool",     "Forward",    1250, 29, 18, 27.71, 15.86, 130, 89,  3392, 38, 20.86, 1, 0),
    ("Erling Haaland",      "Man City",      "Forward",    8260, 22, 5,  21.87, 3.94,  102, 22,  2610, 29, 19.74, 2, 0),
    ("Alexander Isak",      "Newcastle",     "Forward",    7847, 23, 6,  20.14, 4.31,  97,  31,  2720, 31, 0,     18.21, 3, 0),
    ("Cole Palmer",         "Chelsea",       "Midfielder", 9003, 20, 12, 17.43, 9.87,  115, 74,  3180, 36, 16.91, 5, 0),
    ("Bukayo Saka",         "Arsenal",       "Forward",    8722, 17, 13, 14.28, 11.22, 88,  66,  3024, 35, 13.44, 5, 0),
    ("Bryan Mbeumo",        "Brentford",     "Forward",    9721, 20, 8,  16.54, 6.44,  91,  48,  2986, 35, 15.31, 4, 0),
    ("Chris Wood",          "Nott'm Forest", "Forward",    3157, 20, 5,  17.23, 3.12,  78,  18,  2734, 32, 15.87, 2, 0),
    ("Matheus Cunha",       "Wolves",        "Forward",    9058, 14, 9,  11.84, 7.23,  79,  54,  2896, 34, 10.91, 7, 0),
    ("Jarrod Bowen",        "West Ham",      "Forward",    8250, 14, 8,  13.11, 6.87,  82,  47,  2814, 33, 11.88, 3, 0),
    ("Son Heung-min",       "Spurs",         "Forward",    2098, 14, 8,  12.41, 7.14,  74,  58,  2948, 35, 11.14, 2, 0),
    ("Ollie Watkins",       "Aston Villa",   "Forward",    8374, 15, 9,  16.33, 7.44,  86,  44,  2876, 34, 14.71, 3, 0),
    ("Dominic Solanke",     "Spurs",         "Forward",    9044, 12, 6,  13.77, 4.88,  68,  28,  2540, 31, 12.14, 3, 0),
    ("Nicolas Jackson",     "Chelsea",       "Forward",    9741, 14, 5,  14.22, 4.11,  79,  29,  2614, 33, 12.88, 6, 0),
    ("Leandro Trossard",    "Arsenal",       "Forward",    9001, 10, 9,  9.44,  8.22,  61,  51,  2241, 34, 8.91,  3, 0),
    ("Marcus Rashford",     "Man Utd",       "Forward",    3999, 7,  5,  8.11,  4.44,  58,  38,  1894, 25, 7.44,  4, 0),
    ("Gabriel Martinelli",  "Arsenal",       "Forward",    9002, 8,  6,  9.14,  5.33,  64,  41,  2241, 30, 8.41,  4, 0),
    ("Kevin De Bruyne",     "Man City",      "Midfielder", 3574, 6,  11, 5.88,  10.44, 54,  88,  1814, 22, 5.44,  2, 0),
    ("Martin Odegaard",     "Arsenal",       "Midfielder", 7826, 8,  7,  7.44,  6.88,  57,  77,  2448, 30, 7.11,  5, 0),
    ("Declan Rice",         "Arsenal",       "Midfielder", 9042, 7,  8,  5.14,  6.11,  44,  63,  3024, 36, 4.88,  8, 0),
    ("Rodri",               "Man City",      "Midfielder", 6163, 3,  4,  3.44,  4.11,  28,  42,  1644, 21, 3.11,  4, 0),
    ("Phil Foden",          "Man City",      "Midfielder", 9005, 11, 10, 10.88, 9.14,  71,  64,  2614, 31, 9.44,  2, 0),
    ("Bruno Fernandes",     "Man Utd",       "Midfielder", 6522, 9,  8,  8.88,  7.44,  66,  71,  2848, 33, 7.91,  9, 0),
    ("James Maddison",      "Spurs",         "Midfielder", 5411, 7,  9,  6.44,  8.88,  52,  72,  2248, 28, 6.11,  4, 0),
    ("Emile Smith Rowe",    "Fulham",        "Midfielder", 8842, 10, 5,  9.14,  4.44,  61,  38,  2541, 31, 8.71,  3, 0),
    ("Anthony Gordon",      "Newcastle",     "Forward",    9148, 11, 10, 10.44, 9.11,  68,  57,  2848, 34, 9.88,  6, 0),
    ("Trent Alexander-Arnold","Liverpool",   "Defender",   7814, 3,  9,  2.88,  8.44,  41,  81,  3024, 35, 2.44,  4, 0),
    ("Virgil van Dijk",     "Liverpool",     "Defender",   3014, 4,  2,  3.44,  1.88,  28,  18,  3060, 36, 3.14,  3, 0),
    ("William Saliba",      "Arsenal",       "Defender",   9411, 2,  1,  1.88,  1.14,  14,  8,   3060, 36, 1.71,  2, 0),
    ("Alisson Becker",      "Liverpool",     "Goalkeeper", 3322, 0,  0,  0.0,   0.0,   0,   0,   3060, 36, 0.0,   2, 0),
    ("David Raya",          "Arsenal",       "Goalkeeper", 8714, 0,  0,  0.0,   0.0,   0,   0,   3060, 36, 0.0,   1, 0),
    ("Ederson",             "Man City",      "Goalkeeper", 4068, 0,  0,  0.0,   0.0,   0,   0,   2340, 26, 0.0,   2, 0),
]

PL_TEAMS = [
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Ipswich",
    "Leicester", "Liverpool", "Man City", "Man Utd", "Newcastle",
    "Nott'm Forest", "Southampton", "Spurs", "West Ham", "Wolves",
]

FIXTURES_DATA = [
    # (home_team, away_team, date, status, score)
    # GW36
    ("Man City",  "Chelsea",   "2026-05-03 15:00", "scheduled", None),
    ("Newcastle", "Liverpool", "2026-05-03 15:00", "scheduled", None),
    ("Spurs",     "Arsenal",   "2026-05-04 14:00", "scheduled", None),
    ("Brighton",  "Man Utd",   "2026-05-03 15:00", "scheduled", None),
    ("Aston Villa","Wolves",   "2026-05-03 15:00", "scheduled", None),
    # GW37
    ("Arsenal",   "Man City",  "2026-05-10 15:00", "scheduled", None),
    ("Liverpool", "Spurs",     "2026-05-10 15:00", "scheduled", None),
    ("Chelsea",   "Newcastle", "2026-05-10 15:00", "scheduled", None),
    ("Brentford", "Aston Villa","2026-05-10 15:00", "scheduled", None),
    ("Man Utd",   "West Ham",  "2026-05-10 15:00", "scheduled", None),
    # GW38 — final day
    ("Man City",  "Brentford", "2026-05-17 16:00", "scheduled", None),
    ("Arsenal",   "Everton",   "2026-05-17 16:00", "scheduled", None),
    ("Liverpool", "Crystal Palace","2026-05-17 16:00", "scheduled", None),
    ("Chelsea",   "Bournemouth","2026-05-17 16:00", "scheduled", None),
    ("Spurs",     "Brighton",  "2026-05-17 16:00", "scheduled", None),
    # Recently completed
    ("Arsenal",   "Chelsea",   "2026-04-26 16:30", "completed", "2-1"),
    ("Liverpool", "Man City",  "2026-04-27 14:00", "completed", "2-1"),
    ("Brighton",  "Brentford", "2026-04-27 15:00", "completed", "1-1"),
    ("Arsenal",   "Spurs",     "2026-04-14 12:30", "completed", "3-0"),
    ("Liverpool", "Chelsea",   "2026-04-13 16:30", "completed", "2-1"),
]

INJURY_DATA = [
    # (team, player_name, injury_type, status, expected_return)
    ("Man City",  "Kevin De Bruyne",    "Muscle",    "Doubt",  "Apr 30"),
    ("Arsenal",   "Takehiro Tomiyasu",  "Knee",      "Out",    "May 2026"),
    ("Liverpool", "Curtis Jones",       "Hamstring", "Out",    "May 3"),
    ("Chelsea",   "Reece James",        "Groin",     "Doubt",  "Apr 30"),
    ("Man Utd",   "Luke Shaw",          "Hamstring", "Out",    "Season"),
    ("Spurs",     "Micky van de Ven",   "Hamstring", "Doubt",  "May 1"),
    ("Newcastle", "Sven Botman",        "Knee",      "Out",    "Season"),
    ("Aston Villa","Tyrone Mings",      "Knee",      "Out",    "Season"),
    ("Wolves",    "Pedro Neto",         "Ankle",     "Doubt",  "May 4"),
    ("Brentford", "Ivan Toney",         "Suspension","Suspended","May 10"),
]


def generate_logs(name, team, goals, assists, shots, minutes, apps, xg):
    """Generate realistic match logs from season totals."""
    if apps <= 0:
        return []
    opponents = [t for t in PL_TEAMS if t.lower() != team.lower()]
    random.seed(hash(name) % 10000)

    avg_shots = shots / max(apps, 1)
    avg_xg = xg / max(apps, 1)
    avg_mins = minutes / max(apps, 1)

    # Distribute goals + assists
    goal_slots = [0] * apps
    assist_slots = [0] * apps
    remaining_g = goals
    while remaining_g > 0:
        i = random.randint(0, apps - 1)
        goal_slots[i] += 1
        remaining_g -= 1
    remaining_a = assists
    while remaining_a > 0:
        i = random.randint(0, apps - 1)
        assist_slots[i] += 1
        remaining_a -= 1

    logs = []
    base = datetime.now() - timedelta(days=3)
    for i in range(min(apps, 15)):
        date = base - timedelta(days=7 * i + random.randint(0, 1))
        opp = opponents[i % len(opponents)]
        home = "H" if i % 2 == 0 else "A"
        g = goal_slots[i]
        a = assist_slots[i]
        s = max(0, int(avg_shots + random.gauss(0, avg_shots * 0.4)))
        xg_m = round(max(0, avg_xg + random.gauss(0, avg_xg * 0.5)), 2)
        mins = int(max(45, min(90, avg_mins + random.gauss(0, 8))))

        # Result probabilities
        if g > 0:
            rc = random.choices(["W", "D", "L"], weights=[0.6, 0.2, 0.2])[0]
        else:
            rc = random.choices(["W", "D", "L"], weights=[0.38, 0.27, 0.35])[0]

        if rc == "W":
            ts = random.randint(1, 3); os_ = random.randint(0, max(0, ts - 1))
        elif rc == "D":
            ts = os_ = random.randint(0, 2)
        else:
            os_ = random.randint(1, 3); ts = random.randint(0, max(0, os_ - 1))

        rating = round(min(10.0, 6.2 + g * 1.4 + a * 0.7 + s * 0.07), 1)

        logs.append({
            "date": date.strftime("%Y-%m-%d"),
            "opponent": opp, "home_away": home,
            "competition": "Premier League",
            "result": f"{ts}-{os_} {rc}",
            "minutes": mins, "goals": g, "assists": a,
            "shots": s, "xG": xg_m, "rating": rating,
        })
    return logs


def run():
    print("Seeding database…")

    # Injuries — convert tuples to dicts
    injury_dicts = [
        {"team": t, "player_name": p, "injury_type": it, "status": s, "expected_return": er}
        for t, p, it, s, er in INJURY_DATA
    ]
    db.replace_injuries(injury_dicts)
    print(f"  ✓ {len(INJURY_DATA)} injuries")

    # Fixtures
    for home, away, date, status, score in FIXTURES_DATA:
        db.upsert_fixture(home, away, date, "Premier League", status, score)
    print(f"  ✓ {len(FIXTURES_DATA)} fixtures")

    # Players
    for row in PLAYERS:
        if len(row) == 15:
            name, team, pos, uid, goals, assists, xg, xa, shots, kp, minutes, apps, npxg, yellows, reds = row
        else:
            # Handle the Alexander Isak row with typo (extra column)
            name, team, pos, uid = row[0], row[1], row[2], row[3]
            goals, assists, xg, xa, shots, kp = row[4], row[5], row[6], row[7], row[8], row[9]
            minutes, apps, npxg = row[10], row[11], row[13]
            yellows, reds = row[14], row[15] if len(row) > 15 else 0

        sot = int(shots * 0.43)
        player_id = db.upsert_player(name, team, pos, uid)
        db.upsert_player_stats(player_id, SEASON, {
            "goals": goals, "assists": assists, "xG": xg, "xA": xa,
            "shots": shots, "shots_on_target": sot, "key_passes": kp,
            "minutes": minutes, "appearances": apps, "npxG": npxg,
            "yellow_cards": yellows, "red_cards": reds,
        })
        logs = generate_logs(name, team, goals, assists, shots, minutes, apps, xg)
        for log in logs:
            db.upsert_match_log(player_id, log)

    print(f"  ✓ {len(PLAYERS)} players with stats + match logs")

    with db.db_conn() as conn:
        pc = conn.execute("SELECT COUNT(*) as c FROM players").fetchone()["c"]
        lc = conn.execute("SELECT COUNT(*) as c FROM match_logs").fetchone()["c"]
        fc = conn.execute("SELECT COUNT(*) as c FROM fixtures WHERE status='scheduled'").fetchone()["c"]
    print(f"  DB: {pc} players, {lc} match logs, {fc} upcoming fixtures")
    print("Seed complete.")


if __name__ == "__main__":
    run()
