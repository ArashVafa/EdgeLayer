"""
FPL match history scraper — real per-game stats for every player.
Uses Fantasy Premier League element-summary API (public, no auth).
Runs after injuries scraper has populated fpl_id on player rows.
"""
import asyncio
import logging
from datetime import datetime

import httpx

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import db

logger = logging.getLogger(__name__)

FPL_ELEMENT_URL = "https://fantasy.premierleague.com/api/element-summary/{}/"
FPL_BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
CONCURRENCY = 10   # max simultaneous requests
SEASON = "2024-2025"


async def _fetch_bootstrap_teams() -> dict[int, str]:
    """Return fpl_team_id → short name mapping."""
    from scrapers.injuries import TEAM_MAP
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(FPL_BOOTSTRAP_URL)
        resp.raise_for_status()
    teams = resp.json().get("teams", [])
    return {t["id"]: TEAM_MAP.get(t["name"], t["name"]) for t in teams}


async def _fetch_player_history(
    client: httpx.AsyncClient,
    fpl_id: int,
    db_player_id: int,
    team_names: dict[int, str],
    semaphore: asyncio.Semaphore,
    player_team: str,
) -> int:
    """Fetch and store match history for one player. Returns number of logs written."""
    async with semaphore:
        try:
            resp = await client.get(FPL_ELEMENT_URL.format(fpl_id))
            resp.raise_for_status()
        except Exception as e:
            logger.debug(f"History fetch failed for fpl_id={fpl_id}: {e}")
            return 0

    history = resp.json().get("history", [])
    count = 0

    for match in history:
        minutes = match.get("minutes", 0)
        if minutes == 0:
            continue  # didn't play

        kickoff = match.get("kickoff_time", "")
        try:
            date_str = datetime.fromisoformat(kickoff.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except Exception:
            continue

        was_home = match.get("was_home", True)
        opp_team_id = match.get("opponent_team", 0)
        opponent = team_names.get(opp_team_id, f"Team {opp_team_id}")

        goals = match.get("goals_scored", 0)
        assists = match.get("assists", 0)
        home_score = match.get("team_h_score")
        away_score = match.get("team_a_score")

        if home_score is not None and away_score is not None:
            our_score = home_score if was_home else away_score
            their_score = away_score if was_home else home_score
            if our_score > their_score:
                result_code = "W"
            elif our_score == their_score:
                result_code = "D"
            else:
                result_code = "L"
            result = f"{our_score}-{their_score} {result_code}"
        else:
            result = "?"

        xg_raw = match.get("expected_goals", "0") or "0"
        try:
            xg = round(float(xg_raw), 2)
        except (ValueError, TypeError):
            xg = 0.0

        shots = match.get("saves", 0)  # FPL doesn't give shots for outfield in free tier

        db.upsert_match_log(db_player_id, {
            "date": date_str,
            "opponent": opponent,
            "home_away": "H" if was_home else "A",
            "competition": "Premier League",
            "result": result,
            "minutes": minutes,
            "goals": goals,
            "assists": assists,
            "shots": shots,
            "xG": xg,
            "rating": None,
        })
        count += 1

    return count


async def run_fpl_history_scrape():
    """Fetch real match logs for all players with an fpl_id in our DB."""
    logger.info("Starting FPL match history scrape…")
    try:
        team_names = await _fetch_bootstrap_teams()
        players = db.get_players_with_fpl_id()

        if not players:
            logger.warning("No players have fpl_id set — run injury scrape first")
            db.log_scrape("fpl_history", "warning", "no fpl_ids found")
            return

        semaphore = asyncio.Semaphore(CONCURRENCY)
        total = 0

        async with httpx.AsyncClient(timeout=20) as client:
            tasks = [
                _fetch_player_history(
                    client, p["fpl_id"], p["id"], team_names, semaphore, p["team"]
                )
                for p in players
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, int):
                total += r

        db.log_scrape("fpl_history", "ok", f"{total} match logs for {len(players)} players")
        logger.info(f"FPL history complete: {total} match logs, {len(players)} players")

    except Exception as e:
        logger.error(f"FPL history scrape failed: {e}")
        db.log_scrape("fpl_history", "error", str(e))
