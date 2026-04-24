"""
Injury scraper — premierinjuries.com
Scrapes the injury table and stores results in the injuries table.
"""
import logging

import httpx
from bs4 import BeautifulSoup

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import PREMIER_INJURIES_URL
import db

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

# Map known status strings to canonical values
STATUS_MAP = {
    "out": "Out",
    "doubtful": "Doubt",
    "doubt": "Doubt",
    "suspended": "Suspended",
    "il": "Out",
    "injured": "Out",
    "knock": "Doubt",
    "illness": "Doubt",
}


def _normalize_status(raw: str) -> str:
    lower = raw.lower().strip()
    for key, val in STATUS_MAP.items():
        if key in lower:
            return val
    return raw.strip().title()


async def scrape_injuries() -> list[dict]:
    """Fetch and parse the injury table from premierinjuries.com."""
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=30, follow_redirects=True) as client:
            resp = await client.get(PREMIER_INJURIES_URL)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch injury page: {e}")
        db.log_scrape("injuries", "error", str(e))
        return []

    soup = BeautifulSoup(resp.text, "html.parser")

    # The main injury table — try multiple selectors for resilience
    table = (
        soup.find("table", {"id": "injurytable"})
        or soup.find("table", class_=lambda c: c and "injury" in c.lower())
        or soup.find("table")
    )

    if not table:
        # Try parsing divs as a fallback if table layout changed
        logger.warning("Injury table not found — trying div-based fallback")
        return _parse_div_layout(soup)

    injuries = []
    rows = table.find_all("tr")
    for row in rows[1:]:  # skip header
        cells = row.find_all(["td", "th"])
        if len(cells) < 4:
            continue

        texts = [c.get_text(strip=True) for c in cells]

        # Layout varies; try to detect column order
        # Common: Team | Player | Injury | Status | Return
        team = texts[0] if len(texts) > 0 else ""
        player_name = texts[1] if len(texts) > 1 else ""
        injury_type = texts[2] if len(texts) > 2 else ""
        status_raw = texts[3] if len(texts) > 3 else ""
        expected_return = texts[4] if len(texts) > 4 else ""

        if not player_name or not team:
            continue

        injuries.append({
            "team": team.strip(),
            "player_name": player_name.strip(),
            "injury_type": injury_type.strip(),
            "status": _normalize_status(status_raw),
            "expected_return": expected_return.strip(),
        })

    logger.info(f"Scraped {len(injuries)} injury records")
    return injuries


def _parse_div_layout(soup: BeautifulSoup) -> list[dict]:
    """Fallback: parse injury data from div-based layout."""
    injuries = []
    # Look for divs with player/injury class patterns
    cards = soup.find_all("div", class_=lambda c: c and any(
        kw in c.lower() for kw in ["player", "injury", "card"]
    ))
    for card in cards:
        text = card.get_text(separator=" ", strip=True)
        if len(text) < 10:
            continue
        # Minimal parse — just capture what we can
        injuries.append({
            "team": "",
            "player_name": text[:50],
            "injury_type": "Unknown",
            "status": "Out",
            "expected_return": "",
        })
    return injuries


async def run_injury_scrape():
    """Entry point for scheduler."""
    logger.info("Starting injury scrape…")
    try:
        injuries = await scrape_injuries()
        if injuries:
            db.replace_injuries(injuries)
            db.log_scrape("injuries", "ok", f"{len(injuries)} records")
            logger.info(f"Injury scrape complete: {len(injuries)} records")
        else:
            logger.warning("No injuries scraped — keeping stale data")
            db.log_scrape("injuries", "warning", "0 records scraped")
    except Exception as e:
        logger.error(f"Injury scrape failed: {e}")
        db.log_scrape("injuries", "error", str(e))
