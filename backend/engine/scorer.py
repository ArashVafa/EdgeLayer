from __future__ import annotations
"""
Aggregates all 13 dimension scores into the final Edge Score.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import db
from engine.dimensions import (
    dim_player_form, dim_team_context, dim_opponent,
    dim_schedule_fatigue, dim_injuries_lineup,
    dim_manager_tactical, dim_market_intelligence,
    dim_role_usage, dim_psychological,
    dim_external_conditions, dim_change_detection,
    dim_risk_indicators, dim_output_metrics,
)

WEIGHTS = {
    "player_form":        0.15,
    "team_context":       0.10,
    "opponent":           0.12,
    "schedule_fatigue":   0.08,
    "injuries_lineup":    0.10,
    "manager_tactical":   0.05,
    "market_intelligence":0.10,
    "role_usage":         0.05,
    "psychological":      0.05,
    "external_conditions":0.03,
    "change_detection":   0.07,
    "risk_indicators":    0.05,
    "output_metrics":     0.05,
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 0.001, "Weights must sum to 1.0"


def build_report(player_id: int, fixture_id: int | None = None) -> dict:
    """
    Assemble all 13 dimensions and compute the final Edge Score.
    Returns a full report dict ready for the API response.
    """
    from engine.fpl_points import calculate_xfpl, captaincy_score, differential_score

    player = db.get_player(player_id)
    if not player:
        raise ValueError(f"Player {player_id} not found")

    stats_list = db.get_player_stats(player_id)
    stats = stats_list[0] if stats_list else {}

    match_logs = db.get_match_logs(player_id, limit=20)
    all_injuries = db.get_injuries()
    fpl_stats = db.get_fpl_stats(player_id)
    team_injuries = [i for i in all_injuries if i.get("team", "").lower() == player.get("team", "").lower()]

    # Determine opponent from fixture
    opponent_team = ""
    fixture = None
    if fixture_id:
        fixture = db.get_fixture_by_id(fixture_id)
        if fixture:
            player_team = player.get("team", "")
            if _fuzzy_team_match(player_team, fixture.get("home_team", "")):
                opponent_team = fixture["away_team"]
            else:
                opponent_team = fixture["home_team"]

    opponent_injuries = [i for i in all_injuries
                         if i.get("team", "").lower() == opponent_team.lower()]

    # Model probability for goal scoring (xG-based if FPL data available, else naive)
    if fpl_stats and fpl_stats.get("expected_goals", 0):
        xg_season = fpl_stats.get("expected_goals", 0) or 0
        fpl_minutes = fpl_stats.get("minutes", 1) or 1
        model_goal_prob = min(0.9, (xg_season / fpl_minutes) * 90 * 0.8)
    else:
        minutes = stats.get("minutes", 1)
        goals = stats.get("goals", 0)
        model_goal_prob = min(0.9, (goals / max(minutes, 1)) * 90 * 0.7)

    # ── Run all 13 dimensions ──────────────────────────────────────────────
    dims = {}

    dims["player_form"] = dim_player_form(stats, match_logs, fpl_stats)
    dims["team_context"] = dim_team_context(player, team_injuries)
    dims["opponent"] = dim_opponent(opponent_team, match_logs, opponent_injuries)
    dims["schedule_fatigue"] = dim_schedule_fatigue(match_logs)
    dims["injuries_lineup"] = dim_injuries_lineup(player, all_injuries)
    dims["manager_tactical"] = dim_manager_tactical()
    dims["market_intelligence"] = dim_market_intelligence(fixture_id, player, model_goal_prob, fpl_stats)
    dims["role_usage"] = dim_role_usage()
    dims["psychological"] = dim_psychological(match_logs)
    dims["external_conditions"] = dim_external_conditions()
    dims["change_detection"] = dim_change_detection(match_logs, all_injuries, player)
    dims["risk_indicators"] = dim_risk_indicators(match_logs, all_injuries, player, fpl_stats)

    # Pre-compute weighted score for output_metrics
    raw_weighted = sum(
        dims[k]["score"] * WEIGHTS[k]
        for k in WEIGHTS
        if k != "output_metrics"
    ) / (1 - WEIGHTS["output_metrics"])

    dims["output_metrics"] = dim_output_metrics(
        [d["score"] for d in dims.values()],
        raw_weighted
    )

    # Final weighted edge score
    edge_score = int(round(sum(dims[k]["score"] * WEIGHTS[k] for k in WEIGHTS)))

    # Confidence and risk
    confidence = "HIGH" if edge_score >= 75 else ("MEDIUM" if edge_score >= 55 else "LOW")
    all_flags = [f for d in dims.values() for f in d.get("flags", [])]
    risk_flag_count = dims["risk_indicators"]["data"].get("risk_flag_count", 0)
    risk_level = "LOW" if risk_flag_count == 0 else ("MEDIUM" if risk_flag_count <= 2 else "HIGH")

    shot_profile = _build_shot_profile(match_logs, stats)
    form_dots = _build_form_dots(match_logs[:5])

    # ── FPL analytics block ────────────────────────────────────────────────
    fpl_analytics = _build_fpl_analytics(
        fpl_stats, calculate_xfpl, captaincy_score, differential_score
    )

    report = {
        "player": player,
        "stats": stats,
        "fixture": fixture,
        "opponent": opponent_team,
        "edge_score": edge_score,
        "confidence": confidence,
        "risk_level": risk_level,
        "all_flags": all_flags,
        "dimensions": {
            k: {
                "name": _dim_display_name(k),
                "weight": WEIGHTS[k],
                "score": d["score"],
                "analysis": d["analysis"],
                "flags": d.get("flags", []),
                "data": d.get("data", {}),
            }
            for k, d in dims.items()
        },
        "shot_profile": shot_profile,
        "form_dots": form_dots,
        "match_logs": match_logs[:10],
        "risk_summary": dims["risk_indicators"]["data"],
        "market_data": dims["market_intelligence"]["data"],
        "fpl_analytics": fpl_analytics,
    }

    return report


def _fuzzy_team_match(a: str, b: str) -> bool:
    a, b = a.lower(), b.lower()
    return a in b or b in a or a[:4] == b[:4]


def _build_shot_profile(match_logs: list, stats: dict) -> dict:
    """Derive shot profile percentages from available data."""
    total = max(stats.get("shots", 1), 1)
    sot = stats.get("shots_on_target", 0)
    # In-box is estimated (Understat league page doesn't give shot zones per player)
    return {
        "total_shots": total,
        "shots_on_target": sot,
        "sot_pct": round(sot / total * 100) if total > 0 else 0,
        "goals": stats.get("goals", 0),
        # These are estimated from position / typical patterns
        "left_foot_pct": 50,
        "right_foot_pct": 35,
        "header_pct": 15,
        "in_box_pct": 75,
    }


def _build_form_dots(recent_logs: list) -> list:
    dots = []
    for m in recent_logs:
        goals = m.get("goals", 0)
        assists = m.get("assists", 0)
        if goals > 0:
            dots.append({"type": "goal", "label": f"{goals}G", "match": m})
        elif assists > 0:
            dots.append({"type": "assist", "label": f"{assists}A", "match": m})
        else:
            dots.append({"type": "blank", "label": "–", "match": m})
    return dots


def _build_fpl_analytics(fpl_stats, calculate_xfpl, captaincy_score, differential_score) -> dict:
    """Build the FPL-specific analytics block from fpl_stats row."""
    if not fpl_stats:
        return {}

    element_type = fpl_stats.get("element_type", 4)
    xg = fpl_stats.get("expected_goals", 0) or 0
    xa = fpl_stats.get("expected_assists", 0) or 0
    minutes = fpl_stats.get("minutes", 0) or 0
    starts = fpl_stats.get("starts", 0) or 0
    gw = max(max(starts, minutes // 90), 1)  # games played: prefer starts, fallback to mins/90

    xfpl_per_game = calculate_xfpl(
        element_type=element_type,
        xg=xg,
        xa=xa,
        minutes=minutes,
        starts=starts,
        total_gw_played=gw,
        clean_sheets=fpl_stats.get("clean_sheets", 0) or 0,
        goals_conceded=fpl_stats.get("goals_conceded", 0) or 0,
        yellow_cards=fpl_stats.get("yellow_cards", 0) or 0,
        red_cards=fpl_stats.get("red_cards", 0) or 0,
        saves=fpl_stats.get("saves", 0) or 0,
        bonus=fpl_stats.get("bonus", 0) or 0,
    )

    cap_score = captaincy_score(
        element_type=element_type,
        xg=xg,
        xa=xa,
        minutes=minutes,
        starts=starts,
        total_gw_played=gw,
        clean_sheets=fpl_stats.get("clean_sheets", 0) or 0,
    )

    diff_score = differential_score(
        ownership_pct=fpl_stats.get("ownership_pct", 0) or 0,
        xfpl_per_game=xfpl_per_game,
        form=fpl_stats.get("form", 0) or 0,
    )

    from engine.fpl_points import rotation_risk_label, GOAL_PTS, CS_PTS
    avg_mins = minutes / gw if gw else 0
    rot_risk = rotation_risk_label(starts, gw, avg_mins)

    return {
        "xfpl_per_game": xfpl_per_game,
        "captaincy_score": cap_score,
        "differential_score": diff_score,
        "rotation_risk": rot_risk,
        "ownership_pct": round(fpl_stats.get("ownership_pct", 0) or 0, 1),
        "price": round(fpl_stats.get("price", 0) or 0, 1),
        "form": round(fpl_stats.get("form", 0) or 0, 1),
        "points_per_game": round(fpl_stats.get("points_per_game", 0) or 0, 1),
        "total_points": fpl_stats.get("total_points", 0) or 0,
        "ict_index": round(fpl_stats.get("ict_index", 0) or 0, 1),
        "influence": round(fpl_stats.get("influence", 0) or 0, 1),
        "creativity": round(fpl_stats.get("creativity", 0) or 0, 1),
        "threat": round(fpl_stats.get("threat", 0) or 0, 1),
        "xGI": round(fpl_stats.get("expected_goal_involvements", 0) or 0, 2),
        "starts": starts,
        "goal_pts_value": GOAL_PTS.get(element_type, 4),
        "cs_pts_value": CS_PTS.get(element_type, 0),
        "transfers_in_event": fpl_stats.get("transfers_in_event", 0) or 0,
        "transfers_out_event": fpl_stats.get("transfers_out_event", 0) or 0,
    }


def _dim_display_name(key: str) -> str:
    names = {
        "player_form": "Player Performance & Form",
        "team_context": "Team Context & Support",
        "opponent": "Opponent Analysis",
        "schedule_fatigue": "Schedule & Fatigue",
        "injuries_lineup": "Injuries & Lineup",
        "manager_tactical": "Manager & Tactical Signals",
        "market_intelligence": "Market Intelligence",
        "role_usage": "Role & Usage Changes",
        "psychological": "Psychological & Narrative",
        "external_conditions": "External Conditions",
        "change_detection": "Change Detection",
        "risk_indicators": "Risk Indicators",
        "output_metrics": "Output Metrics",
    }
    return names.get(key, key.replace("_", " ").title())
