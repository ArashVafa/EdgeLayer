from __future__ import annotations
"""
Odds scraper — The Odds API (the-odds-api.com)
Fetches h2h, totals, and player prop markets for PL fixtures.
"""
import logging

import httpx

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import ODDS_API_KEY, ODDS_API_BASE
import db

logger = logging.getLogger(__name__)

SPORT_KEY = "soccer_england_premier_league"
REGIONS = "uk,eu"
MARKETS = "h2h,totals"
ODDS_FORMAT = "decimal"


async def fetch_odds() -> list[dict]:
    """Fetch live PL odds from The Odds API."""
    if not ODDS_API_KEY:
        logger.warning("ODDS_API_KEY not set — skipping odds scrape")
        return []

    url = f"{ODDS_API_BASE}/sports/{SPORT_KEY}/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": REGIONS,
        "markets": MARKETS,
        "oddsFormat": ODDS_FORMAT,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params)
        if resp.status_code == 401:
            logger.error("Invalid Odds API key")
            return []
        if resp.status_code == 422:
            logger.warning("Odds API: no events available")
            return []
        resp.raise_for_status()

    data = resp.json()
    remaining = resp.headers.get("x-requests-remaining", "?")
    logger.info(f"Odds API requests remaining: {remaining}")

    return data if isinstance(data, list) else []


def _match_fixture(home_team: str, away_team: str) -> int | None:
    """Try to find a matching fixture_id in our DB."""
    # Fuzzy match — Odds API uses different team name format
    home_clean = _fuzzy_clean(home_team)
    away_clean = _fuzzy_clean(away_team)

    with db.db_conn() as conn:
        rows = conn.execute(
            "SELECT id, home_team, away_team FROM fixtures WHERE status='scheduled' ORDER BY date ASC"
        ).fetchall()

    for row in rows:
        if (home_clean in _fuzzy_clean(row["home_team"]) or
                _fuzzy_clean(row["home_team"]) in home_clean):
            if (away_clean in _fuzzy_clean(row["away_team"]) or
                    _fuzzy_clean(row["away_team"]) in away_clean):
                return row["id"]
    return None


def _fuzzy_clean(name: str) -> str:
    """Lowercase, strip common suffixes for fuzzy matching."""
    name = name.lower()
    for suffix in [" fc", " afc", " city", " united", " rovers", " town",
                   " wanderers", " hotspur", " palace"]:
        name = name.replace(suffix, "")
    return name.strip()


async def run_odds_scrape():
    """Entry point for scheduler."""
    logger.info("Starting odds scrape…")
    try:
        events = await fetch_odds()
        count = 0
        for event in events:
            home_team = event.get("home_team", "")
            away_team = event.get("away_team", "")
            fixture_id = _match_fixture(home_team, away_team)

            if not fixture_id:
                # Create a placeholder fixture if not in DB yet
                commence = event.get("commence_time", "")
                date = commence[:16].replace("T", " ") if commence else ""
                fixture_id = db.upsert_fixture(
                    home_team=home_team, away_team=away_team,
                    date=date, competition="Premier League",
                    status="scheduled"
                )

            for bookmaker in event.get("bookmakers", []):
                bk_name = bookmaker.get("title", "Unknown")
                for market in bookmaker.get("markets", []):
                    market_key = market.get("key", "")
                    for outcome in market.get("outcomes", []):
                        db.upsert_odds(
                            fixture_id=fixture_id,
                            market=market_key,
                            outcome=outcome.get("name", ""),
                            odds_val=float(outcome.get("price", 0)),
                            bookmaker=bk_name,
                        )
                        count += 1

        db.log_scrape("odds", "ok", f"{count} odds lines")
        logger.info(f"Odds scrape complete: {count} lines")

    except Exception as e:
        logger.error(f"Odds scrape failed: {e}")
        db.log_scrape("odds", "error", str(e))
