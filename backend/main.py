"""
EdgeLayer — FastAPI backend
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

import db
from config import FRONTEND_URL, REPORT_CACHE_TTL
from engine.scorer import build_report
from engine.narrative import generate_narratives

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("EdgeLayer starting…")
    db.init_db()
    logger.info("Database initialized")

    # Auto-seed on first deploy when DB is empty
    with db.db_conn() as conn:
        player_count = conn.execute("SELECT COUNT(*) as c FROM players").fetchone()["c"]
    if player_count == 0:
        logger.info("Empty database detected — seeding with initial data…")
        try:
            from seed import run as seed_run
            seed_run()
            logger.info("Database seeded successfully")
        except Exception as e:
            logger.warning(f"Seed failed: {e}")

    # Start background scrape scheduler
    try:
        from scheduler import start_scheduler
        start_scheduler()
        logger.info("Scheduler started")
    except Exception as e:
        logger.warning(f"Scheduler failed to start: {e}")

    yield

    # Shutdown
    logger.info("EdgeLayer shutting down")


app = FastAPI(
    title="EdgeLayer API",
    description="Pre-bet intelligence platform for Premier League",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Search ────────────────────────────────────────────────────────────────────

@app.get("/api/search")
async def search_players(q: str = Query(..., min_length=1)):
    """Search players by name. Returns matches with id, name, team, position."""
    if len(q.strip()) < 1:
        return {"players": []}
    results = db.search_players(q.strip(), limit=15)
    return {"players": results, "count": len(results)}


# ── Player Profile ────────────────────────────────────────────────────────────

@app.get("/api/player/{player_id}")
async def get_player(player_id: int):
    """Full player profile with season stats and recent match log."""
    player = db.get_player(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    stats = db.get_player_stats(player_id)
    match_logs = db.get_match_logs(player_id, limit=10)
    injuries = db.get_injuries()
    player_injury = next(
        (i for i in injuries if i.get("player_name", "").lower() == player["name"].lower()),
        None
    )

    return {
        "player": player,
        "stats": stats,
        "match_logs": match_logs,
        "injury_status": player_injury,
    }


# ── Report ────────────────────────────────────────────────────────────────────

@app.get("/api/report/{player_id}")
async def get_report(player_id: int, refresh: bool = False):
    """
    Full EdgeLayer report for the player's next fixture.
    Cached for 2 hours. Use ?refresh=true or POST /refresh to bust the cache.
    """
    player = db.get_player(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Check cache
    if not refresh:
        cached = db.get_cached_report(player_id, max_age_seconds=REPORT_CACHE_TTL)
        if cached:
            logger.info(f"Cache hit for player {player_id}")
            return _format_cached_report(cached, player)

    # Find next fixture for player's team
    team = player.get("team", "")
    fixtures = db.get_upcoming_fixtures(team=team, limit=1)
    fixture_id = fixtures[0]["id"] if fixtures else None

    # Build report
    try:
        report = build_report(player_id, fixture_id=fixture_id)
    except Exception as e:
        logger.error(f"Report build failed for player {player_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

    # Generate Claude narratives
    narratives = await generate_narratives(report)

    # Cache the result
    db.save_report_cache(
        player_id=player_id,
        fixture_id=fixture_id or 0,
        edge_score=report["edge_score"],
        confidence=report["confidence"],
        risk_level=report["risk_level"],
        dimensions=report["dimensions"],
        narrative_avg=narratives["average"],
        narrative_agg=narratives["aggressive"],
        narrative_con=narratives["conservative"],
    )

    # Merge narratives into report
    report["narratives"] = narratives
    return report


@app.post("/api/report/{player_id}/refresh")
async def refresh_report(player_id: int, background_tasks: BackgroundTasks):
    """Force regenerate report (bust cache). Returns immediately, regenerates in background."""
    player = db.get_player(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    background_tasks.add_task(_regenerate_report, player_id)
    return {"message": "Report regeneration queued", "player_id": player_id}


async def _regenerate_report(player_id: int):
    """Background task to regenerate a report."""
    try:
        player = db.get_player(player_id)
        team = player.get("team", "")
        fixtures = db.get_upcoming_fixtures(team=team, limit=1)
        fixture_id = fixtures[0]["id"] if fixtures else None

        report = build_report(player_id, fixture_id=fixture_id)
        narratives = await generate_narratives(report)

        db.save_report_cache(
            player_id=player_id,
            fixture_id=fixture_id or 0,
            edge_score=report["edge_score"],
            confidence=report["confidence"],
            risk_level=report["risk_level"],
            dimensions=report["dimensions"],
            narrative_avg=narratives["average"],
            narrative_agg=narratives["aggressive"],
            narrative_con=narratives["conservative"],
        )
        logger.info(f"Report regenerated for player {player_id}")
    except Exception as e:
        logger.error(f"Background report regen failed for {player_id}: {e}")


def _format_cached_report(cached: dict, player: dict) -> dict:
    """Re-hydrate a cached report for the API response."""
    fixture = None
    if cached.get("fixture_id"):
        fixture = db.get_fixture_by_id(cached["fixture_id"])

    return {
        "player": player,
        "stats": db.get_player_stats(player["id"]),
        "fixture": fixture,
        "edge_score": cached["edge_score"],
        "confidence": cached["confidence"],
        "risk_level": cached["risk_level"],
        "dimensions": cached.get("dimensions", {}),
        "match_logs": db.get_match_logs(player["id"], limit=10),
        "narratives": {
            "average": cached.get("narrative_avg", ""),
            "aggressive": cached.get("narrative_agg", ""),
            "conservative": cached.get("narrative_con", ""),
        },
        "cached_at": cached.get("created_at"),
        "from_cache": True,
    }


# ── Fixtures ──────────────────────────────────────────────────────────────────

@app.get("/api/fixtures")
async def get_fixtures(team: str = None, limit: int = 20):
    """Upcoming PL fixtures, optionally filtered by team."""
    fixtures = db.get_upcoming_fixtures(team=team, limit=limit)
    return {"fixtures": fixtures, "count": len(fixtures)}


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    """Health check with last scrape timestamps and DB stats."""
    with db.db_conn() as conn:
        player_count = conn.execute("SELECT COUNT(*) as c FROM players").fetchone()["c"]
        fixture_count = conn.execute(
            "SELECT COUNT(*) as c FROM fixtures WHERE status='scheduled'"
        ).fetchone()["c"]
        injury_count = conn.execute("SELECT COUNT(*) as c FROM injuries").fetchone()["c"]

    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db": {
            "players": player_count,
            "upcoming_fixtures": fixture_count,
            "injuries": injury_count,
        },
        "last_scrapes": {
            "understat": db.get_last_scrape("understat_players"),
            "injuries": db.get_last_scrape("injuries"),
            "fixtures": db.get_last_scrape("fixtures"),
            "odds": db.get_last_scrape("odds"),
        },
    }


# ── Admin: Trigger manual scrapes ─────────────────────────────────────────────

@app.post("/api/admin/scrape/{source}")
async def trigger_scrape(source: str, background_tasks: BackgroundTasks):
    """Manually trigger a scrape. Sources: understat, injuries, fixtures, odds."""
    valid = {"understat", "injuries", "fixtures", "odds"}
    if source not in valid:
        raise HTTPException(status_code=400, detail=f"Unknown source. Valid: {valid}")

    background_tasks.add_task(_run_scrape, source)
    return {"message": f"Scrape triggered for {source}"}


async def _run_scrape(source: str):
    if source == "understat":
        from scrapers.understat import scrape_all_players
        await scrape_all_players()
    elif source == "injuries":
        from scrapers.injuries import run_injury_scrape
        await run_injury_scrape()
    elif source == "fixtures":
        from scrapers.fixtures import run_fixtures_scrape
        await run_fixtures_scrape()
    elif source == "odds":
        from scrapers.odds import run_odds_scrape
        await run_odds_scrape()


# ── Run directly ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
