"""
EdgeLayer — FastAPI backend
"""
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

    # fpl_analytics is not stored in cache — compute fresh every time
    # (ownership/price/transfers change each gameweek)
    from engine.scorer import _build_fpl_analytics
    from engine.fpl_points import calculate_xfpl, captaincy_score, differential_score
    fpl_stats = db.get_fpl_stats(player["id"])
    _match_logs = db.get_match_logs(player["id"], limit=10)
    _stats_list = db.get_player_stats(player["id"])
    _stats = (_stats_list[0] if isinstance(_stats_list, list) else _stats_list) or {}
    # Determine opponent for fixture-adjusted form
    _opponent, _ha = "", "H"
    if fixture:
        from engine.scorer import _fuzzy_team_match
        _ha = "H" if _fuzzy_team_match(player.get("team", ""), fixture.get("home_team", "")) else "A"
        _opponent = fixture["away_team"] if _ha == "H" else fixture["home_team"]
    fpl_analytics = _build_fpl_analytics(
        fpl_stats, calculate_xfpl, captaincy_score, differential_score,
        stats=_stats, match_logs=_match_logs,
        opponent_team=_opponent, home_away=_ha,
    )

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
        "fpl_analytics": fpl_analytics,
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
    valid = {"understat", "injuries", "fixtures", "odds", "fpl_history", "fpl_bootstrap"}
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
    elif source == "fpl_history":
        from scrapers.fpl_history import run_fpl_history_scrape
        await run_fpl_history_scrape()
    elif source == "fpl_bootstrap":
        from scrapers.fpl_bootstrap import run_fpl_bootstrap_scrape
        await run_fpl_bootstrap_scrape()


@app.post("/api/admin/reseed-fixtures")
async def reseed_fixtures():
    """Replace fixtures with fresh seed data (use when no API key is set)."""
    from seed import run as seed_run
    seed_run()
    return {"message": "Fixtures re-seeded"}


# ── Gameweek Planner ─────────────────────────────────────────────────────────

_POS_FILTER_MAP = {"GK": 1, "DEF": 2, "MID": 3, "FWD": 4}
_ELEM_TO_POS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}


@app.get("/api/gameweek-planner")
async def gameweek_planner(
    show_all: bool = Query(False),
    position: str = Query(None, description="GK / DEF / MID / FWD"),
    max_price: float = Query(None),
    min_ownership: float = Query(None),
    max_ownership: float = Query(None),
):
    """
    Ranked table of players for the upcoming gameweek.
    Single bulk DB load — no per-player queries. Top 100 by default.
    """
    from engine.fpl_points import (
        calculate_xfpl, rotation_risk_label, form_index,
        fixture_adjusted_form, estimate_eo,
    )
    from engine.compare import _fixture_modifier, _fuzzy_team_match, _get_defence_range

    # ── Bulk data load (4 queries total) ──────────────────────────────────
    players = db.get_all_players_with_fpl_stats()
    all_fixtures = db.get_upcoming_fixtures(limit=500)
    team_fdr_list = db.get_all_team_fdr_list()
    most_captained_fpl_id = db.get_current_most_captained()
    defence_min, defence_max = _get_defence_range()

    # Team FDR lookup (fuzzy)
    team_fdr_by_name = {t["team_name"]: t for t in team_fdr_list}

    def _get_opp_fdr(opponent: str):
        for tn, fdr in team_fdr_by_name.items():
            if _fuzzy_team_match(opponent, tn):
                return fdr
        return None

    # Build team → next fixture map (fixtures already sorted ASC by date)
    team_next_fixture: dict[str, dict] = {}
    for fix in all_fixtures:
        for t in (fix["home_team"], fix["away_team"]):
            if t not in team_next_fixture:
                team_next_fixture[t] = fix

    results = []
    for p in players:
        # ── Position filter ───────────────────────────────────────────────
        elem = p.get("element_type", 4) or 4
        if position:
            if _POS_FILTER_MAP.get(position.upper(), 0) != elem:
                continue

        price = p.get("price") or 0
        ownership = p.get("ownership_pct") or 0

        if max_price is not None and price > max_price:
            continue
        if min_ownership is not None and ownership < min_ownership:
            continue
        if max_ownership is not None and ownership > max_ownership:
            continue

        # ── Season-average calculations ───────────────────────────────────
        starts = p.get("starts", 0) or 0
        minutes = p.get("minutes", 0) or 0
        gw_count = max(max(starts, minutes // 90), 1)
        start_rate = starts / gw_count
        avg_mins = minutes / gw_count

        xfpl = calculate_xfpl(
            element_type=elem,
            xg=p.get("expected_goals", 0) or 0,
            xa=p.get("expected_assists", 0) or 0,
            minutes=minutes, starts=starts, total_gw_played=gw_count,
            clean_sheets=p.get("clean_sheets", 0) or 0,
            goals_conceded=p.get("goals_conceded", 0) or 0,
            yellow_cards=p.get("yellow_cards", 0) or 0,
            red_cards=p.get("red_cards", 0) or 0,
            saves=p.get("saves", 0) or 0,
            bonus=p.get("bonus", 0) or 0,
        )

        predicted_mins = round(start_rate * 87 + (1 - start_rate) * 0.35 * 22)
        rot_risk = rotation_risk_label(starts, gw_count, avg_mins)
        rot_mult = {"LOW": 1.0, "MEDIUM": 0.85, "HIGH": 0.6}[rot_risk]
        avail = (p.get("chance_of_playing_next_round") or 100) / 100
        mins_factor_adj = (predicted_mins / 90) * rot_mult * avail

        fi = form_index(
            xg=p.get("expected_goals", 0) or 0,
            xa=p.get("expected_assists", 0) or 0,
            sot=p.get("shots_on_target", 0) or 0,
            key_passes=p.get("key_passes", 0) or 0,
            minutes=minutes,
            appearances=gw_count,
        )

        # ── Next fixture ──────────────────────────────────────────────────
        team = p.get("team") or ""
        next_fix = None
        for t, fix in team_next_fixture.items():
            if _fuzzy_team_match(team, t):
                next_fix = fix
                break

        next_opponent = None
        next_home_away = None
        next_opp_strength = None
        proj_pts = 0.0
        faf = fi

        if next_fix:
            ha = "H" if _fuzzy_team_match(team, next_fix.get("home_team", "")) else "A"
            opponent = next_fix["away_team"] if ha == "H" else next_fix["home_team"]
            next_home_away = ha
            next_opponent = opponent

            opp_fdr = _get_opp_fdr(opponent)
            strength_key = "strength_defence_away" if ha == "H" else "strength_defence_home"
            opp_strength = opp_fdr.get(strength_key, 1200) if opp_fdr else 1200
            next_opp_strength = opp_strength

            fix_mod = _fixture_modifier(opp_strength, defence_min, defence_max)
            proj_pts = round(xfpl * mins_factor_adj * fix_mod, 2)
            faf = fixture_adjusted_form(fi, opp_strength, ha)

        # ── Effective Ownership ───────────────────────────────────────────
        is_mc = (most_captained_fpl_id is not None and p.get("fpl_id") == most_captained_fpl_id)
        eo = estimate_eo(ownership, elem, price, is_mc)

        results.append({
            "id": p["id"],
            "name": p["name"],
            "team": team,
            "position": _ELEM_TO_POS.get(elem, "FWD"),
            "element_type": elem,
            "price": round(price, 1),
            "ownership_pct": round(ownership, 1),
            "estimated_eo": eo,
            "is_most_captained": is_mc,
            "ep_next": round(p.get("ep_next", 0) or 0, 1),
            "xfpl_per_game": round(xfpl, 2),
            "form_index": fi,
            "fixture_adjusted_form": faf,
            "next_opponent": next_opponent,
            "next_home_away": next_home_away,
            "next_opp_strength": next_opp_strength,
            "rotation_risk": rot_risk,
            "proj_pts": proj_pts,
            "predicted_minutes": predicted_mins,
            "news": p.get("news"),
            "chance_of_playing": p.get("chance_of_playing_next_round"),
        })

    results.sort(key=lambda x: x["proj_pts"], reverse=True)
    total = len(results)
    if not show_all:
        results = results[:100]

    return {"players": results, "count": len(results), "total": total}


# ── Transfer Comparison ──────────────────────────────────────────────────────

@app.get("/api/compare")
async def compare_players(
    players: str = Query(..., description="Comma-separated player IDs, e.g. 123,456"),
    gws: int = Query(3, ge=1, le=10, description="Gameweek horizon"),
    hit: int = Query(0, description="Transfer hit cost (0 or 4)"),
):
    """
    Project FPL points for 2+ players over the next N fixtures.
    If exactly 2 players are given, also returns a transfer verdict.
    """
    try:
        player_ids = [int(x.strip()) for x in players.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="players must be comma-separated integers")

    if len(player_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 player IDs required")

    if hit not in (0, 4):
        raise HTTPException(status_code=400, detail="hit must be 0 or 4")

    from engine.compare import compare_players as do_compare
    return do_compare(player_ids, gws=gws, hit=hit)


# ── Chatbot ───────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []

@app.post("/api/chat/{player_id}")
async def chat(player_id: int, body: ChatRequest):
    """Player-specific chatbot powered by Claude. Stateless — caller manages history."""
    player = db.get_player(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    from engine.chatbot import chat as do_chat
    history = [{"role": m.role, "content": m.content} for m in body.history]
    reply = await do_chat(player_id, body.message, history)
    return {"reply": reply}


# ── Run directly ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
