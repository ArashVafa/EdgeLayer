from __future__ import annotations
"""
Understat scraper.
Uses the POST API endpoint that serves season-aggregate data for all EPL players.
Match logs are generated synthetically from season totals until a live match log
source is integrated (FBref with cookies, or a football data API).
"""
import asyncio
import logging
import random
from datetime import datetime, timedelta

import httpx

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import UNDERSTAT_BASE
import db

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://understat.com/",
}

CURRENT_SEASON = "2024"
SEASON_LABEL = "2024-2025"

PL_TEAMS = [
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Ipswich",
    "Leicester", "Liverpool", "Man City", "Man Utd", "Newcastle",
    "Nott'm Forest", "Southampton", "Spurs", "West Ham", "Wolves",
]


# ── API fetch ─────────────────────────────────────────────────────────────────

def fetch_all_players_sync() -> list[dict]:
    """Synchronous POST to understat.com/main/getPlayersStats/ — safe for use in threads.
    Retries up to 3 times with exponential backoff on connection errors.
    """
    import time
    url = f"{UNDERSTAT_BASE}/main/getPlayersStats/"
    for attempt in range(3):
        try:
            with httpx.Client(headers=HEADERS, timeout=45, follow_redirects=True) as client:
                resp = client.post(url, data={"league": "EPL", "season": CURRENT_SEASON})
                resp.raise_for_status()
            data = resp.json()
            if not data.get("success"):
                logger.error(f"Understat API error: {data}")
                return []
            return data.get("players", [])
        except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
            wait = 30 * (2 ** attempt)
            logger.warning(f"Understat attempt {attempt+1}/3 failed ({e}), retrying in {wait}s…")
            time.sleep(wait)
    raise RuntimeError("Understat unreachable after 3 attempts")


async def fetch_all_players() -> list[dict]:
    """Async wrapper — calls the sync version via thread executor to avoid SSL issues in background threads."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fetch_all_players_sync)


def _normalize_position(pos: str) -> str:
    pos = pos.upper().strip()
    if "GK" in pos:
        return "Goalkeeper"
    if "F" in pos:
        return "Forward"
    if "AM" in pos or "M" in pos:
        return "Midfielder"
    if "D" in pos:
        return "Defender"
    return pos or "Unknown"


# ── Synthetic match log generator ─────────────────────────────────────────────

def _generate_match_logs(stats: dict, appearances: int, team: str) -> list[dict]:
    """
    Distribute season totals across match-level logs.
    This is synthetic data used until a real match log source is integrated.
    Distribution is realistic: players go on scoring runs, have blank patches.
    """
    if appearances <= 0:
        return []

    total_goals = stats.get("goals", 0)
    total_assists = stats.get("assists", 0)
    total_shots = stats.get("shots", 0)
    total_minutes = stats.get("minutes", 0)
    total_xg = stats.get("xG", 0.0)

    avg_mins = total_minutes / max(appearances, 1)
    avg_shots = total_shots / max(appearances, 1)
    avg_xg = total_xg / max(appearances, 1)

    # Distribute goals/assists using a weighted random approach
    goal_slots = _distribute_count(total_goals, appearances)
    assist_slots = _distribute_count(total_assists, appearances)
    shot_slots = _distribute_around(avg_shots, appearances)
    xg_slots = _distribute_around(avg_xg, appearances)
    mins_slots = _distribute_minutes(avg_mins, appearances)

    # Generate opponents + dates working backwards from today
    opponents = [t for t in PL_TEAMS if t.lower() != team.lower()]
    logs = []
    base_date = datetime.now() - timedelta(days=3)

    for i in range(appearances):
        match_date = base_date - timedelta(days=7 * i + random.randint(0, 2))
        opponent = opponents[i % len(opponents)]
        home_away = "H" if i % 2 == 0 else "A"
        g = goal_slots[i]
        a = assist_slots[i]
        s = shot_slots[i]
        xg = round(xg_slots[i], 2)
        mins = mins_slots[i]

        # Generate result (team wins more often when player scores)
        if g > 0:
            weights = [0.6, 0.2, 0.2]
        else:
            weights = [0.35, 0.25, 0.4]
        result_char = random.choices(["W", "D", "L"], weights=weights)[0]
        if result_char == "W":
            team_score = random.randint(1, 3)
            opp_score = random.randint(0, team_score - 1)
        elif result_char == "D":
            team_score = opp_score = random.randint(0, 2)
        else:
            opp_score = random.randint(1, 3)
            team_score = random.randint(0, opp_score - 1)

        score_str = f"{team_score}-{opp_score}"
        rating = _calc_rating(g, a, s)

        logs.append({
            "date": match_date.strftime("%Y-%m-%d"),
            "opponent": opponent,
            "home_away": home_away,
            "competition": "Premier League",
            "result": f"{score_str} {result_char}",
            "minutes": mins,
            "goals": g,
            "assists": a,
            "shots": s,
            "xG": xg,
            "rating": rating,
        })

    return logs


def _distribute_count(total: int, n: int) -> list[int]:
    """Distribute integer total across n slots, clustering for realism."""
    slots = [0] * n
    remaining = total
    while remaining > 0:
        # Cluster: pick a random slot and give it 1 goal; sometimes give 2
        idx = random.randint(0, n - 1)
        amount = 2 if (remaining >= 2 and random.random() < 0.2) else 1
        slots[idx] += amount
        remaining -= amount
    return slots


def _distribute_around(avg: float, n: int) -> list[float]:
    """Generate n values that sum close to avg*n with realistic variance."""
    values = [max(0, avg + random.gauss(0, avg * 0.5)) for _ in range(n)]
    # Scale to match target sum
    current_sum = sum(values)
    target = avg * n
    if current_sum > 0:
        values = [v * target / current_sum for v in values]
    return values


def _distribute_minutes(avg_mins: float, n: int) -> list[int]:
    """Most starts are ~85-90 min; some are 60-75 (sub off)."""
    mins = []
    for _ in range(n):
        r = random.random()
        if avg_mins >= 80:
            m = 90 if r < 0.7 else (random.randint(65, 85) if r < 0.9 else random.randint(45, 65))
        else:
            m = random.randint(int(avg_mins * 0.7), min(90, int(avg_mins * 1.2)))
        mins.append(max(1, m))
    return mins


def _calc_rating(goals: int, assists: int, shots: int) -> float:
    base = 6.2
    base += goals * 1.4 + assists * 0.7 + shots * 0.08
    base = min(10.0, base)
    return round(base, 1)


# ── Main scrape entry point ───────────────────────────────────────────────────

async def scrape_all_players():
    """Fetch all EPL players, store stats, and generate match logs."""
    logger.info("Starting Understat scrape…")
    try:
        players = await fetch_all_players()
        logger.info(f"Fetched {len(players)} EPL players from Understat API")

        for p in players:
            understat_id = int(p["id"])
            name = p["player_name"]
            team = p.get("team_title", "")
            position = _normalize_position(p.get("position", ""))
            apps = int(p.get("games", 0))
            minutes = int(p.get("time", 0))
            goals = int(p.get("goals", 0))
            assists = int(p.get("assists", 0))
            xg = float(p.get("xG", 0))
            xa = float(p.get("xA", 0))
            shots = int(p.get("shots", 0))
            key_passes = int(p.get("key_passes", 0))
            npxg = float(p.get("npxG", 0))
            yellows = int(p.get("yellow_cards", 0))
            reds = int(p.get("red_cards", 0))

            # Rough shots-on-target estimate (Understat doesn't give this on league page)
            sot = int(shots * 0.42) if shots > 0 else 0

            player_db_id = db.upsert_player(name, team, position, understat_id)

            stats = {
                "goals": goals, "assists": assists, "xG": xg, "xA": xa,
                "shots": shots, "shots_on_target": sot, "key_passes": key_passes,
                "minutes": minutes, "appearances": apps, "npxG": npxg,
                "yellow_cards": yellows, "red_cards": reds,
            }
            db.upsert_player_stats(player_db_id, SEASON_LABEL, stats)

            # Generate and store synthetic match logs (only if none exist)
            existing_logs = db.get_match_logs(player_db_id, limit=1)
            if not existing_logs and apps > 0:
                logs = _generate_match_logs(stats, min(apps, 15), team)
                for log in logs:
                    db.upsert_match_log(player_db_id, log)

        db.log_scrape("understat_players", "ok", f"{len(players)} players")
        logger.info(f"Understat scrape complete: {len(players)} players")

    except Exception as e:
        logger.error(f"Understat scrape failed: {e}")
        db.log_scrape("understat_players", "error", str(e))
        raise


def _persist_players(players: list[dict]):
    """Write a list of Understat player dicts to the DB (shared by sync and async paths)."""
    for p in players:
        understat_id = int(p["id"])
        name = p["player_name"]
        team = p.get("team_title", "")
        position = _normalize_position(p.get("position", ""))
        apps = int(p.get("games", 0))
        minutes = int(p.get("time", 0))
        goals = int(p.get("goals", 0))
        assists = int(p.get("assists", 0))
        xg = float(p.get("xG", 0))
        xa = float(p.get("xA", 0))
        shots = int(p.get("shots", 0))
        key_passes = int(p.get("key_passes", 0))
        npxg = float(p.get("npxG", 0))
        yellows = int(p.get("yellow_cards", 0))
        reds = int(p.get("red_cards", 0))
        sot = int(shots * 0.42) if shots > 0 else 0

        player_db_id = db.upsert_player(name, team, position, understat_id)
        stats = {
            "goals": goals, "assists": assists, "xG": xg, "xA": xa,
            "shots": shots, "shots_on_target": sot, "key_passes": key_passes,
            "minutes": minutes, "appearances": apps, "npxG": npxg,
            "yellow_cards": yellows, "red_cards": reds,
        }
        db.upsert_player_stats(player_db_id, SEASON_LABEL, stats)
        existing_logs = db.get_match_logs(player_db_id, limit=1)
        if not existing_logs and apps > 0:
            logs = _generate_match_logs(stats, min(apps, 15), team)
            for log in logs:
                db.upsert_match_log(player_db_id, log)


def scrape_all_players_sync_job():
    """Synchronous entry point called directly by APScheduler background thread."""
    logger.info("Starting Understat scrape (sync)…")
    try:
        players = fetch_all_players_sync()
        logger.info(f"Fetched {len(players)} EPL players")
        _persist_players(players)
        db.log_scrape("understat_players", "ok", f"{len(players)} players")
        logger.info(f"Understat scrape complete: {len(players)} players")
    except Exception as e:
        logger.error(f"Understat scrape failed: {e}")
        db.log_scrape("understat_players", "error", str(e))


async def scrape_all_players():
    """Async entry point — used when called from FastAPI endpoints."""
    logger.info("Starting Understat scrape (async)…")
    try:
        players = await fetch_all_players()
        logger.info(f"Fetched {len(players)} EPL players")
        _persist_players(players)
        db.log_scrape("understat_players", "ok", f"{len(players)} players")
        logger.info(f"Understat scrape complete: {len(players)} players")
    except Exception as e:
        logger.error(f"Understat scrape failed: {e}")
        db.log_scrape("understat_players", "error", str(e))
        raise
