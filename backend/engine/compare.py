from __future__ import annotations
"""
Transfer comparison engine.

Projections use season-level fpl_stats averages + team FDR, NOT per-match logs
(which are synthetic). Season averages give a more reliable baseline for expected
FPL output per fixture.
"""

import db
from engine.fpl_points import calculate_xfpl, rotation_risk_label, form_index, estimate_eo

ROTATION_PENALTY = {"LOW": 1.0, "MEDIUM": 0.85, "HIGH": 0.6}

# NOTE: rotation_risk_label rarely returns HIGH with current data because gw is
# estimated from max(starts, minutes//90), which inflates avg_minutes for pure
# substitutes. MEDIUM correctly captures most rotation-risk players.


def _get_defence_range() -> tuple[int, int]:
    """
    Read actual min/max defence strength from team_fdr so the fixture modifier
    spans the full real range. Falls back to (1000, 1400) if table is empty.
    """
    with db.db_conn() as conn:
        row = conn.execute("""
            SELECT
                MIN(MIN(strength_defence_home, strength_defence_away)) AS min_s,
                MAX(MAX(strength_defence_home, strength_defence_away)) AS max_s
            FROM team_fdr
        """).fetchone()
    if row and row["min_s"] and row["max_s"] and row["max_s"] > row["min_s"]:
        return int(row["min_s"]), int(row["max_s"])
    return 1000, 1400


def _fixture_modifier(opp_strength: int, defence_min: int, defence_max: int) -> float:
    """
    Map opponent defence strength → scoring modifier in [0.7, 1.3].
    Anchored on actual DB min/max so Wolves (easiest) → 1.3, Man City away
    (hardest) → 0.7, average fixture → ~1.0.
    """
    rng = max(defence_max - defence_min, 1)
    modifier = 1.3 - (opp_strength - defence_min) / rng * 0.6
    return round(max(0.7, min(1.3, modifier)), 3)


def _fuzzy_team_match(a: str, b: str) -> bool:
    a, b = a.lower().strip(), b.lower().strip()
    return a == b or a in b or b in a or a[:4] == b[:4]


def _project_player(
    player_id: int,
    gws: int,
    defence_min: int,
    defence_max: int,
    most_captained_fpl_id: int | None = None,
) -> dict | None:
    """
    Build the projection block for a single player.
    Returns None if the player or their fpl_stats row doesn't exist.
    """
    player = db.get_player(player_id)
    if not player:
        return None

    fpl = db.get_fpl_stats(player_id)
    if not fpl:
        return None

    # ── Season averages ────────────────────────────────────────────────────────
    starts   = fpl.get("starts", 0) or 0
    minutes  = fpl.get("minutes", 0) or 0
    gw_count = max(max(starts, minutes // 90), 1)
    start_rate = starts / gw_count
    avg_mins   = minutes / gw_count

    xfpl_per_game = calculate_xfpl(
        element_type=fpl.get("element_type", 4) or 4,
        xg=fpl.get("expected_goals", 0) or 0,
        xa=fpl.get("expected_assists", 0) or 0,
        minutes=minutes,
        starts=starts,
        total_gw_played=gw_count,
        clean_sheets=fpl.get("clean_sheets", 0) or 0,
        goals_conceded=fpl.get("goals_conceded", 0) or 0,
        yellow_cards=fpl.get("yellow_cards", 0) or 0,
        red_cards=fpl.get("red_cards", 0) or 0,
        saves=fpl.get("saves", 0) or 0,
        bonus=fpl.get("bonus", 0) or 0,
    )

    # ── Minutes factor (start rate → expected minutes per game) ───────────────
    predicted_minutes = round(start_rate * 87 + (1 - start_rate) * 0.35 * 22)
    minutes_factor = predicted_minutes / 90

    # Rotation risk hard penalty — the most important correctness lever.
    # A HIGH-risk player gets ×0.6 regardless of their season xFPL average.
    rot_risk = rotation_risk_label(starts, gw_count, avg_mins)
    rotation_multiplier = ROTATION_PENALTY[rot_risk]
    minutes_factor_adj = minutes_factor * rotation_multiplier

    # Availability discount for doubtful/injured players
    avail = (fpl.get("chance_of_playing_next_round") or 100) / 100
    minutes_factor_adj *= avail

    # ── Upcoming fixtures ─────────────────────────────────────────────────────
    team = player.get("team", "")
    fixtures = db.get_upcoming_fixtures(team=team, limit=gws)
    # Only use up to the requested number; missing fixtures = blank GWs (0 pts)

    # ── Form index for surface stats ──────────────────────────────────────────
    stats_list = db.get_player_stats(player_id)
    stats = (stats_list[0] if isinstance(stats_list, list) else stats_list) or {}
    fi = form_index(
        xg=stats.get("xG", fpl.get("expected_goals", 0) or 0) or 0,
        xa=stats.get("xA", fpl.get("expected_assists", 0) or 0) or 0,
        sot=stats.get("shots_on_target", 0) or 0,
        key_passes=stats.get("key_passes", 0) or 0,
        minutes=stats.get("minutes", minutes) or minutes,
        appearances=stats.get("appearances", gw_count) or gw_count,
    )

    # ── Per-GW projections ────────────────────────────────────────────────────
    gw_projections = []
    total_projected = 0.0
    total_low = 0.0
    total_high = 0.0

    for i in range(gws):
        if i >= len(fixtures):
            # Blank gameweek — no fixture, contributes 0 pts
            gw_projections.append({
                "label": f"GW+{i+1}",
                "opponent": None,
                "home_away": None,
                "opp_strength": None,
                "fixture_modifier": None,
                "proj_pts": 0.0,
                "low": 0.0,
                "high": 0.0,
                "blank": True,
            })
            continue

        fix = fixtures[i]
        home_away = "H" if _fuzzy_team_match(team, fix.get("home_team", "")) else "A"
        opponent = fix["away_team"] if home_away == "H" else fix["home_team"]

        # When player is at home, they attack the opponent's away defence; when
        # away, they face the opponent's home defence.
        strength_key = "strength_defence_away" if home_away == "H" else "strength_defence_home"
        opp_fdr = db.get_team_fdr(opponent)
        opp_strength = (opp_fdr.get(strength_key, 1200) if opp_fdr else 1200)

        fix_mod = _fixture_modifier(opp_strength, defence_min, defence_max)
        proj_pts = round(xfpl_per_game * minutes_factor_adj * fix_mod, 2)

        # TODO: scale uncertainty band by rotation_risk + form variance;
        # flat ±25% is a placeholder until per-GW variance data is available.
        low  = round(proj_pts * 0.75, 2)
        high = round(proj_pts * 1.25, 2)

        # Extract a short date label from the fixture date field
        date_str = fix.get("date", "")
        label = date_str[:10] if date_str else f"GW+{i+1}"

        gw_projections.append({
            "label": label,
            "opponent": opponent,
            "home_away": home_away,
            "opp_strength": opp_strength,
            "fixture_modifier": fix_mod,
            "proj_pts": proj_pts,
            "low": low,
            "high": high,
            "blank": False,
        })

        total_projected += proj_pts
        total_low  += low
        total_high += high

    ownership_pct = round(fpl.get("ownership_pct", 0) or 0, 1)
    price = round(fpl.get("price", 0) or 0, 1)
    element_type = fpl.get("element_type", 4) or 4
    is_most_captained = (
        most_captained_fpl_id is not None
        and fpl.get("fpl_id") == most_captained_fpl_id
    )
    eo = estimate_eo(ownership_pct, element_type, price, is_most_captained)

    return {
        "id": player["id"],
        "name": player["name"],
        "team": team,
        "position": player.get("position", ""),
        "element_type": element_type,
        "xfpl_per_game": round(xfpl_per_game, 2),
        "minutes_factor": round(minutes_factor_adj, 3),
        "predicted_minutes": predicted_minutes,
        "rotation_risk": rot_risk,
        "ownership_pct": ownership_pct,
        "estimated_eo": eo,
        "is_most_captained": is_most_captained,
        "price": price,
        "form_index": fi,
        "fixture_adjusted_form": round(fpl.get("fixture_adjusted_form", fi) or fi, 1),
        "ep_next": round(fpl.get("ep_next", 0) or 0, 1),
        "news": fpl.get("news"),
        "gw_projections": gw_projections,
        "total_projected": round(total_projected, 2),
        "total_low":  round(total_low,  2),
        "total_high": round(total_high, 2),
    }


def _verdict(p_out: dict, p_in: dict, hit: int) -> dict:
    """Compute transfer verdict for exactly 2 players (out → in)."""
    points_delta     = round(p_in["total_projected"] - p_out["total_projected"], 2)
    delta_low        = round(p_in["total_low"]  - p_out["total_high"], 2)
    delta_high       = round(p_in["total_high"] - p_out["total_low"],  2)
    delta_minus_hit  = round(points_delta - hit, 2)

    if delta_minus_hit > 3:
        recommendation = "TRANSFER"
        hit_str = f"after −{hit} hit " if hit else ""
        text = (
            f"+{points_delta:.1f} pts (range {delta_low:+.1f} to {delta_high:+.1f}) "
            f"{hit_str}— worth it"
        )
    elif delta_minus_hit > 0:
        recommendation = "MARGINAL"
        hit_str = f"after −{hit} hit " if hit else ""
        text = (
            f"+{points_delta:.1f} pts (range {delta_low:+.1f} to {delta_high:+.1f}) "
            f"{hit_str}— slim margin, consider carefully"
        )
    else:
        recommendation = "HOLD"
        hit_str = f"after −{hit} hit " if hit else ""
        text = (
            f"{points_delta:+.1f} pts (range {delta_low:+.1f} to {delta_high:+.1f}) "
            f"{hit_str}— hold"
        )

    # Template vs differential ownership note (decision-relevant context)
    in_ownership = p_in.get("ownership_pct", 0) or 0
    in_eo = p_in.get("estimated_eo", in_ownership)
    eo_note = None
    if in_ownership < 12:
        eo_note = (
            f"Differential: {p_in['name']} owned by {in_ownership}% (EO ~{in_eo}%) — "
            f"a big haul beats most rivals"
        )
    elif in_eo > 40:
        eo_note = (
            f"Template asset: {p_in['name']} has ~{in_eo}% effective ownership — "
            f"not owning risks falling behind the pack"
        )

    return {
        "points_delta":     points_delta,
        "points_delta_low": delta_low,
        "points_delta_high": delta_high,
        "delta_minus_hit":  delta_minus_hit,
        "recommendation":   recommendation,
        "recommendation_text": text,
        "eo_note": eo_note,
    }


def compare_players(player_ids: list[int], gws: int = 3, hit: int = 0) -> dict:
    """
    Main entry point called from the API endpoint.
    Returns projections for all requested players, plus a verdict if exactly 2.
    """
    defence_min, defence_max = _get_defence_range()
    most_captained_fpl_id = db.get_current_most_captained()

    results = []
    errors = []
    for pid in player_ids:
        proj = _project_player(pid, gws, defence_min, defence_max, most_captained_fpl_id)
        if proj:
            results.append(proj)
        else:
            errors.append(pid)

    out = {"players": results, "verdict": None, "errors": errors}

    if len(results) == 2:
        out["verdict"] = _verdict(results[0], results[1], hit)

    return out
