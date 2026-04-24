"""
Fixtures scraper — football-data.org free API.
Fetches Premier League upcoming and completed fixtures.
"""
import logging
from datetime import datetime, timezone

import httpx

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import FOOTBALL_DATA_API_KEY, FOOTBALL_DATA_BASE
import db

logger = logging.getLogger(__name__)

PL_COMPETITION = "PL"

# Map football-data.org team names to clean short names
TEAM_NAME_MAP = {
    "Manchester City FC": "Man City",
    "Manchester United FC": "Man Utd",
    "Arsenal FC": "Arsenal",
    "Chelsea FC": "Chelsea",
    "Liverpool FC": "Liverpool",
    "Tottenham Hotspur FC": "Spurs",
    "Newcastle United FC": "Newcastle",
    "Aston Villa FC": "Aston Villa",
    "Brighton & Hove Albion FC": "Brighton",
    "West Ham United FC": "West Ham",
    "Brentford FC": "Brentford",
    "Fulham FC": "Fulham",
    "Crystal Palace FC": "Crystal Palace",
    "Everton FC": "Everton",
    "Nottingham Forest FC": "Nott'm Forest",
    "Wolverhampton Wanderers FC": "Wolves",
    "Bournemouth FC": "Bournemouth",
    "AFC Bournemouth": "Bournemouth",
    "Ipswich Town FC": "Ipswich",
    "Leicester City FC": "Leicester",
    "Southampton FC": "Southampton",
    "Luton Town FC": "Luton",
}


def _clean_team(name: str) -> str:
    return TEAM_NAME_MAP.get(name, name)


def _parse_date(date_str: str) -> str:
    """Return ISO date string (YYYY-MM-DD HH:MM)."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return date_str[:16]


async def fetch_fixtures(matchday_from: int = None, matchday_to: int = None) -> list[dict]:
    """Fetch PL fixtures from football-data.org."""
    if not FOOTBALL_DATA_API_KEY:
        logger.warning("FOOTBALL_DATA_API_KEY not set — skipping fixtures scrape")
        return []

    params = {"competitions": PL_COMPETITION}
    if matchday_from:
        params["matchday"] = matchday_from
    # Fetch scheduled + finished
    params["status"] = "SCHEDULED,FINISHED"

    url = f"{FOOTBALL_DATA_BASE}/competitions/{PL_COMPETITION}/matches"
    headers = {"X-Auth-Token": FOOTBALL_DATA_API_KEY}

    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        resp = await client.get(url, params=params)
        if resp.status_code == 429:
            logger.warning("football-data.org rate limit hit")
            return []
        resp.raise_for_status()

    data = resp.json()
    matches = data.get("matches", [])

    fixtures = []
    for match in matches:
        home = _clean_team(match["homeTeam"]["name"])
        away = _clean_team(match["awayTeam"]["name"])
        date = _parse_date(match.get("utcDate", ""))
        status_raw = match.get("status", "SCHEDULED")
        status = "scheduled" if status_raw in ("SCHEDULED", "TIMED") else "completed"

        score = None
        if status == "completed":
            ft = match.get("score", {}).get("fullTime", {})
            if ft.get("home") is not None and ft.get("away") is not None:
                score = f"{ft['home']}-{ft['away']}"

        fixtures.append({
            "home_team": home,
            "away_team": away,
            "date": date,
            "competition": "Premier League",
            "status": status,
            "score": score,
            "matchday": match.get("matchday"),
        })

    return fixtures


async def run_fixtures_scrape():
    """Entry point for scheduler."""
    logger.info("Starting fixtures scrape…")
    try:
        fixtures = await fetch_fixtures()
        count = 0
        for f in fixtures:
            db.upsert_fixture(
                home_team=f["home_team"],
                away_team=f["away_team"],
                date=f["date"],
                competition=f["competition"],
                status=f["status"],
                score=f.get("score"),
            )
            count += 1

        db.log_scrape("fixtures", "ok", f"{count} fixtures")
        logger.info(f"Fixtures scrape complete: {count} fixtures")

    except Exception as e:
        logger.error(f"Fixtures scrape failed: {e}")
        db.log_scrape("fixtures", "error", str(e))
        raise
