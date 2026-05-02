"""
Injury scraper — Fantasy Premier League bootstrap-static API (public, no auth).
Also stores FPL player IDs for use by the match history scraper.
"""
import logging

import httpx

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import db

logger = logging.getLogger(__name__)

FPL_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"

# FPL status codes → our canonical status
STATUS_MAP = {
    "a": None,        # available — not injured, skip
    "d": "Doubt",
    "i": "Out",
    "n": "Out",
    "s": "Suspended",
    "u": "Out",
}

# FPL team name → our short name
TEAM_MAP = {
    "Arsenal": "Arsenal",
    "Aston Villa": "Aston Villa",
    "Bournemouth": "Bournemouth",
    "Brentford": "Brentford",
    "Brighton": "Brighton",
    "Chelsea": "Chelsea",
    "Crystal Palace": "Crystal Palace",
    "Everton": "Everton",
    "Fulham": "Fulham",
    "Ipswich": "Ipswich",
    "Leicester": "Leicester",
    "Liverpool": "Liverpool",
    "Man City": "Man City",
    "Man Utd": "Man Utd",
    "Newcastle": "Newcastle",
    "Nott'm Forest": "Nott'm Forest",
    "Southampton": "Southampton",
    "Spurs": "Spurs",
    "West Ham": "West Ham",
    "Wolves": "Wolves",
}


async def scrape_injuries() -> tuple[list[dict], dict[int, int]]:
    """
    Fetch FPL bootstrap-static and return:
      - injuries: list of injury dicts for non-available players
      - fpl_id_map: {fpl_player_id: db_player_id} for match history scraper
    """
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(FPL_URL)
        resp.raise_for_status()

    data = resp.json()

    # Build team id → clean name map
    teams = {t["id"]: TEAM_MAP.get(t["name"], t["name"]) for t in data.get("teams", [])}

    injuries = []
    fpl_name_to_id = {}  # "Mohamed Salah" → fpl_player_id

    for p in data.get("elements", []):
        full_name = f"{p.get('first_name', '')} {p.get('second_name', '')}".strip()
        fpl_name_to_id[full_name.lower()] = p["id"]

        status_code = p.get("status", "a")
        status = STATUS_MAP.get(status_code)
        if status is None:
            continue  # player is available

        team = teams.get(p.get("team", 0), "Unknown")
        news = p.get("news", "") or ""
        chance = p.get("chance_of_playing_next_round")

        return_str = (
            f"{chance}% chance of playing"
            if chance is not None
            else "Unknown"
        )

        injuries.append({
            "team": team,
            "player_name": full_name,
            "injury_type": news[:150] if news else status_code.upper(),
            "status": status,
            "expected_return": return_str,
        })

    # Match FPL names to our DB player IDs
    fpl_id_map: dict[int, int] = {}  # fpl_player_id → db_player_id
    all_players = db.get_all_players_for_fpl_match()
    for db_player in all_players:
        db_name = db_player["name"].lower()
        fpl_pid = fpl_name_to_id.get(db_name)
        if fpl_pid:
            db.update_player_fpl_id(db_player["id"], fpl_pid)
            fpl_id_map[fpl_pid] = db_player["id"]

    logger.info(f"FPL: {len(injuries)} injuries, {len(fpl_id_map)} players matched to FPL IDs")
    return injuries, fpl_id_map


async def run_injury_scrape():
    """Entry point for scheduler."""
    logger.info("Starting FPL injury scrape…")
    try:
        injuries, _ = await scrape_injuries()
        if injuries:
            db.replace_injuries(injuries)
            db.log_scrape("injuries", "ok", f"{len(injuries)} records")
            logger.info(f"Injury scrape complete: {len(injuries)} records")
        else:
            logger.warning("No injuries scraped")
            db.log_scrape("injuries", "warning", "0 records")
    except Exception as e:
        logger.error(f"Injury scrape failed: {e}")
        db.log_scrape("injuries", "error", str(e))
