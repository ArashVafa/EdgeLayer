"""
FPL bootstrap scraper — pulls comprehensive player stats and team FDR from FPL API.
Also updates fpl_id mappings on player rows (same endpoint as injuries.py,
but stores the full data payload rather than just injury status).
"""
import json
import logging

import httpx

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import db
from scrapers.injuries import TEAM_MAP

logger = logging.getLogger(__name__)
FPL_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"

# element_type: 1=GKP, 2=DEF, 3=MID, 4=FWD
POSITION_MAP = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}


async def run_fpl_bootstrap_scrape():
    logger.info("Starting FPL bootstrap scrape…")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(FPL_URL)
            resp.raise_for_status()

        data = resp.json()

        # Team FDR
        for t in data.get("teams", []):
            team_name = TEAM_MAP.get(t["name"], t["name"])
            db.upsert_team_fdr(
                fpl_team_id=t["id"],
                team_name=team_name,
                strength=t.get("strength", 3),
                strength_overall_home=t.get("strength_overall_home", 1000),
                strength_overall_away=t.get("strength_overall_away", 1000),
                strength_attack_home=t.get("strength_attack_home", 1000),
                strength_attack_away=t.get("strength_attack_away", 1000),
                strength_defence_home=t.get("strength_defence_home", 1000),
                strength_defence_away=t.get("strength_defence_away", 1000),
            )

        # Build FPL-id → name lookup for event data (most_captained, etc.)
        fpl_id_to_name: dict[int, str] = {}
        for p in data.get("elements", []):
            fpl_id_to_name[p["id"]] = f"{p.get('first_name', '')} {p.get('second_name', '')}".strip()

        # Process GW events array — find current/next GW for captaincy data
        _process_events(data.get("events", []), fpl_id_to_name)

        # Match FPL player names to our DB player rows
        all_db_players = db.get_all_players_for_fpl_match()
        name_to_db = {p["name"].lower(): p["id"] for p in all_db_players}

        count = 0
        for p in data.get("elements", []):
            full_name = f"{p.get('first_name', '')} {p.get('second_name', '')}".strip()
            db_player_id = name_to_db.get(full_name.lower())
            if not db_player_id:
                continue

            fpl_id = p["id"]
            db.update_player_fpl_id(db_player_id, fpl_id)

            def _f(key, default=0.0):
                try:
                    return float(p.get(key) or default)
                except (ValueError, TypeError):
                    return float(default)

            db.upsert_fpl_stats(
                player_id=db_player_id,
                fpl_id=fpl_id,
                price=p.get("now_cost", 0) / 10.0,
                ownership_pct=_f("selected_by_percent"),
                transfers_in_event=p.get("transfers_in_event", 0),
                transfers_out_event=p.get("transfers_out_event", 0),
                transfers_in=p.get("transfers_in", 0),
                transfers_out=p.get("transfers_out", 0),
                total_points=p.get("total_points", 0),
                form=_f("form"),
                points_per_game=_f("points_per_game"),
                goals_scored=p.get("goals_scored", 0),
                assists=p.get("assists", 0),
                clean_sheets=p.get("clean_sheets", 0),
                goals_conceded=p.get("goals_conceded", 0),
                yellow_cards=p.get("yellow_cards", 0),
                red_cards=p.get("red_cards", 0),
                saves=p.get("saves", 0),
                bonus=p.get("bonus", 0),
                bps=p.get("bps", 0),
                minutes=p.get("minutes", 0),
                starts=p.get("starts", 0),
                expected_goals=_f("expected_goals"),
                expected_assists=_f("expected_assists"),
                expected_goal_involvements=_f("expected_goal_involvements"),
                influence=_f("influence"),
                creativity=_f("creativity"),
                threat=_f("threat"),
                ict_index=_f("ict_index"),
                chance_of_playing_next_round=p.get("chance_of_playing_next_round"),
                cost_change_start=p.get("cost_change_start", 0),
                element_type=p.get("element_type", 4),
                # Newly extracted fields
                value_form=_f("value_form"),
                value_season=_f("value_season"),
                ep_next=_f("ep_next"),
                news=p.get("news") or None,
                news_added=p.get("news_added") or None,
            )
            count += 1

        num_teams = len(data.get("teams", []))
        db.log_scrape("fpl_bootstrap", "ok", f"{count} players, {num_teams} teams")
        logger.info(f"FPL bootstrap complete: {count} players, {num_teams} teams")

    except Exception as e:
        logger.error(f"FPL bootstrap scrape failed: {e}")
        db.log_scrape("fpl_bootstrap", "error", str(e))


def _process_events(events: list, fpl_id_to_name: dict):
    """
    Extract captaincy and transfer data from the events array.
    Stores the current/upcoming GW in fpl_events for EO estimation.
    """
    if not events:
        return

    # Prefer the current GW; fall back to the next one
    target_event = None
    for ev in events:
        if ev.get("is_current"):
            target_event = ev
            break
    if not target_event:
        for ev in events:
            if ev.get("is_next"):
                target_event = ev
                break
    if not target_event and events:
        # Last event in the list (most recent)
        target_event = events[-1]

    if not target_event:
        return

    gw = target_event.get("id")
    most_captained_fpl_id = target_event.get("most_captained")
    most_transferred_in_fpl_id = target_event.get("most_transferred_in")
    top_element_fpl_id = target_event.get("top_element")
    average_entry_score = target_event.get("average_entry_score")
    chip_plays = target_event.get("chip_plays", [])

    db.upsert_fpl_event(
        gameweek=gw,
        most_captained_fpl_id=most_captained_fpl_id,
        most_captained_name=fpl_id_to_name.get(most_captained_fpl_id) if most_captained_fpl_id else None,
        most_transferred_in_fpl_id=most_transferred_in_fpl_id,
        most_transferred_in_name=fpl_id_to_name.get(most_transferred_in_fpl_id) if most_transferred_in_fpl_id else None,
        top_element_fpl_id=top_element_fpl_id,
        average_entry_score=average_entry_score,
        chip_plays_json=json.dumps(chip_plays) if chip_plays else None,
    )
    logger.info(f"FPL event GW{gw} stored: most_captained={fpl_id_to_name.get(most_captained_fpl_id, most_captained_fpl_id)}")
