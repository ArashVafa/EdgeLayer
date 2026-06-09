from __future__ import annotations
"""
13-Dimension scoring engine.

Each dimension function returns:
    {"score": int(0-100), "analysis": str, "flags": list[str]}

Dimensions 6, 8, 9, 10 are stubbed with defaults for MVP.
"""


# ── Utility helpers ───────────────────────────────────────────────────────────

def _clamp(val: float, lo: float = 0, hi: float = 100) -> int:
    return int(max(lo, min(hi, val)))


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return a / b if b != 0 else default


def _percentile_score(val: float, p25: float, p50: float, p75: float, p90: float) -> float:
    """Map a value to 0-100 using rough percentile breakpoints."""
    if val >= p90:
        return 90 + 10 * min(1, (val - p90) / max(p90 * 0.2, 0.01))
    if val >= p75:
        return 75 + 15 * (val - p75) / (p90 - p75)
    if val >= p50:
        return 50 + 25 * (val - p50) / (p75 - p50)
    if val >= p25:
        return 25 + 25 * (val - p25) / (p50 - p25)
    return 25 * val / p25 if p25 > 0 else 0


# ── Dimension 1: Player Performance & Form (weight 15%) ──────────────────────

def dim_player_form(stats: dict, match_logs: list[dict], fpl_stats: dict | None = None) -> dict:
    """Season stats + recent form analysis, enhanced with FPL ICT index and form."""
    flags = []
    score_parts = []

    apps = stats.get("appearances", 0)
    goals = stats.get("goals", 0)
    xg = stats.get("xG", 0.0)
    shots = stats.get("shots", 0)
    minutes = stats.get("minutes", 0)
    npxg = stats.get("npxG", 0.0)

    # Goals/90
    goals_90 = _safe_div(goals * 90, minutes)
    goals_90_score = _percentile_score(goals_90, 0.1, 0.3, 0.5, 0.7)
    score_parts.append(goals_90_score * 0.25)

    # xG quality (how close to expectation)
    xg_delta = goals - xg
    if abs(xg_delta) < 2:
        xg_quality = 75
    elif xg_delta > 2:
        xg_quality = 85
        flags.append("outperforming_xG")
    else:
        xg_quality = 50
        flags.append("underperforming_xG")
    score_parts.append(xg_quality * 0.10)

    # Rolling windows from match logs
    recent_3 = match_logs[:3]
    recent_5 = match_logs[:5]
    recent_10 = match_logs[:10]

    goals_last3 = sum(m.get("goals", 0) for m in recent_3)
    goals_last5 = sum(m.get("goals", 0) for m in recent_5)
    assists_last3 = sum(m.get("assists", 0) for m in recent_3)
    assists_last5 = sum(m.get("assists", 0) for m in recent_5)
    shots_last5 = sum(m.get("shots", 0) for m in recent_5)
    xg_last3 = sum(m.get("xG", 0) for m in recent_3)
    xg_last5 = sum(m.get("xG", 0) for m in recent_5)
    xg_last10 = sum(m.get("xG", 0) for m in recent_10)
    # xGI proxy = goals + assists per match (real xA not stored per-match)
    xgi_last5 = goals_last5 + assists_last5

    form_score = 50
    form_score += goals_last3 * 10
    form_score += goals_last5 * 5
    form_score += assists_last5 * 3
    form_score = min(form_score, 100)
    score_parts.append(form_score * 0.30)

    if goals_last3 >= 2:
        flags.append("hot_streak")
    if goals_last3 == 0 and goals_last5 == 0:
        flags.append("goal_drought")

    # Shots/90
    shots_90 = _safe_div(shots * 90, minutes)
    shots_score = _percentile_score(shots_90, 0.5, 1.5, 2.5, 3.5)
    score_parts.append(shots_score * 0.12)

    # npxG/90 (penalty-independent quality)
    npxg_90 = _safe_div(npxg * 90, minutes)
    npxg_score = _percentile_score(npxg_90, 0.1, 0.25, 0.45, 0.65)
    score_parts.append(npxg_score * 0.08)

    # FPL ICT index & form (bonus 15% weight if available)
    ict_data = {}
    if fpl_stats:
        ict = fpl_stats.get("ict_index", 0) or 0
        fpl_form = fpl_stats.get("form", 0) or 0
        ppg = fpl_stats.get("points_per_game", 0) or 0
        xgi = fpl_stats.get("expected_goal_involvements", 0) or 0

        # ICT index: ~100 = elite, ~50 = solid, <20 = low
        ict_score = _percentile_score(ict, 20, 50, 80, 120)
        score_parts.append(ict_score * 0.10)

        # FPL form (last 4 GW average points): 10+ = excellent, 6+ = good
        fpl_form_score = _percentile_score(fpl_form, 2, 5, 7, 10)
        score_parts.append(fpl_form_score * 0.05)

        if ict >= 100:
            flags.append("elite_ict")
        if fpl_form >= 8:
            flags.append("in_form_fpl")

        ict_data = {
            "ict_index": round(ict, 1),
            "fpl_form": round(fpl_form, 1),
            "points_per_game": round(ppg, 1),
            "xGI": round(xgi, 2),
        }
    else:
        score_parts.append(60 * 0.15)  # neutral fill

    final = _clamp(sum(score_parts))

    analysis_parts = [
        f"Season: {goals}G {stats.get('assists',0)}A in {apps} apps.",
        f"Goals/90: {goals_90:.2f}. xG: {xg:.1f} (delta: {xg_delta:+.1f}).",
        f"Last 3: {goals_last3}G {assists_last3}A ({xg_last3:.2f} xG). Last 5: {goals_last5}G {assists_last5}A xGI:{xgi_last5} ({xg_last5:.2f} xG). Last 10 xG: {xg_last10:.2f}.",
    ]
    if "hot_streak" in flags:
        analysis_parts.append(f"Hot streak — {goals_last3}G in last 3.")
    if "goal_drought" in flags:
        analysis_parts.append("Goal drought — no goals in last 5 matches.")
    if ict_data:
        analysis_parts.append(f"ICT index: {ict_data['ict_index']}. FPL form: {ict_data['fpl_form']}. PPG: {ict_data['points_per_game']}.")

    return {
        "score": final,
        "analysis": " ".join(analysis_parts),
        "flags": flags,
        "data": {
            "goals_90": round(goals_90, 2),
            "xg_delta": round(xg_delta, 2),
            "goals_last3": goals_last3,
            "goals_last5": goals_last5,
            "assists_last3": assists_last3,
            "assists_last5": assists_last5,
            "xgi_last5": xgi_last5,
            "shots_last5": shots_last5,
            "xg_last3": round(xg_last3, 2),
            "xg_last5": round(xg_last5, 2),
            "xg_last10": round(xg_last10, 2),
            **ict_data,
        }
    }


# ── Dimension 2: Team Context & Support (weight 10%) ─────────────────────────

def dim_team_context(player: dict, team_injuries: list[dict]) -> dict:
    """Team position in table, attacking support, key teammate availability."""
    flags = []
    score = 60  # neutral baseline

    # Count injuries on same team
    injury_count = len([i for i in team_injuries if i.get("status") in ("Out", "Suspended")])

    if injury_count == 0:
        score += 15
    elif injury_count <= 2:
        score += 5
    elif injury_count >= 5:
        score -= 15
        flags.append("team_injury_crisis")

    # Position-based adjustment (we don't have league table, use heuristic)
    team = player.get("team", "")
    elite_teams = {"Man City", "Arsenal", "Liverpool", "Chelsea", "Man Utd", "Spurs"}
    if team in elite_teams:
        score += 10

    analysis = (
        f"{team} has {injury_count} first-team players out or suspended. "
        + ("Key support players available." if injury_count <= 2 else "Squad depth being tested.")
    )

    return {
        "score": _clamp(score),
        "analysis": analysis,
        "flags": flags,
        "data": {"team_injury_count": injury_count}
    }


# ── Dimension 3: Opponent Analysis (weight 12%) ───────────────────────────────

def dim_opponent(opponent_team: str, all_match_logs: list[dict], opponent_injuries: list[dict]) -> dict:
    """Opponent defensive record and H2H."""
    flags = []

    # H2H from match logs
    h2h = [m for m in all_match_logs if m.get("opponent", "").lower() == opponent_team.lower()]
    h2h_goals = sum(m.get("goals", 0) for m in h2h)
    h2h_xg = sum(m.get("xG", 0) for m in h2h)

    score = 55  # neutral

    if len(h2h) >= 2:
        if h2h_goals >= len(h2h):  # at least 1 goal/game vs this opponent
            score += 15
            flags.append("good_h2h_record")
        if h2h_goals == 0:
            score -= 10
            flags.append("poor_h2h_record")

    # Opponent defensive injuries
    def_injuries = [i for i in opponent_injuries
                    if i.get("status") in ("Out", "Suspended")]
    if len(def_injuries) >= 2:
        score += 12
        flags.append("opponent_defensive_injuries")
    elif len(def_injuries) >= 1:
        score += 6

    if len(h2h) == 0:
        analysis = f"No H2H data vs {opponent_team}. "
    else:
        analysis = f"H2H vs {opponent_team}: {h2h_goals}G in {len(h2h)} matches (xG: {h2h_xg:.1f}). "

    if def_injuries:
        analysis += f"Opponent has {len(def_injuries)} defensive absentees."

    return {
        "score": _clamp(score),
        "analysis": analysis,
        "flags": flags,
        "data": {
            "h2h_matches": len(h2h),
            "h2h_goals": h2h_goals,
            "opponent_defensive_injuries": len(def_injuries),
        }
    }


# ── Dimension 4: Schedule & Fatigue (weight 8%) ───────────────────────────────

def dim_schedule_fatigue(match_logs: list[dict]) -> dict:
    """Days since last match, fixture congestion."""
    from datetime import datetime, timedelta
    flags = []
    score = 70

    if not match_logs:
        return {
            "score": score, "analysis": "No match log data available.",
            "flags": [], "data": {}
        }

    last_match_date_str = match_logs[0].get("date", "")
    try:
        last_date = datetime.strptime(last_match_date_str[:10], "%Y-%m-%d")
        now = datetime.now()
        days_rest = (now - last_date).days
    except ValueError:
        days_rest = 7  # assume normal rest

    if days_rest >= 7:
        score = 85
    elif days_rest >= 5:
        score = 75
    elif days_rest >= 3:
        score = 60
    else:
        score = 40
        flags.append("fixture_congestion")

    # Check how many games in last 14 days
    cutoff = datetime.now() - timedelta(days=14)
    recent_games = 0
    for m in match_logs:
        try:
            d = datetime.strptime(m["date"][:10], "%Y-%m-%d")
            if d >= cutoff:
                recent_games += 1
        except (ValueError, KeyError):
            pass

    if recent_games >= 4:
        score -= 10
        flags.append("heavy_schedule")

    analysis = (
        f"{days_rest} days since last match. "
        f"{recent_games} games in last 14 days. "
        + ("Well rested." if days_rest >= 7 else "Some fatigue possible.")
    )

    return {
        "score": _clamp(score),
        "analysis": analysis,
        "flags": flags,
        "data": {"days_rest": days_rest, "games_last_14": recent_games}
    }


# ── Dimension 5: Injuries & Lineup (weight 10%) ──────────────────────────────

def dim_injuries_lineup(player: dict, all_injuries: list[dict]) -> dict:
    """Player fitness status from injury table."""
    flags = []
    player_name = player.get("name", "").lower()

    # Check if player is listed as injured
    for inj in all_injuries:
        if inj.get("player_name", "").lower() == player_name:
            status = inj.get("status", "")
            if status == "Out":
                flags.append("player_injured")
                return {
                    "score": 10,
                    "analysis": f"INJURY FLAG: {player['name']} listed as OUT ({inj.get('injury_type','unknown injury')}). Expected return: {inj.get('expected_return','unknown')}.",
                    "flags": flags,
                    "data": {"injury_status": status, "injury_type": inj.get("injury_type")}
                }
            elif status in ("Doubt", "Suspended"):
                flags.append("player_doubt")
                return {
                    "score": 40,
                    "analysis": f"DOUBT FLAG: {player['name']} is listed as {status} ({inj.get('injury_type','unknown')}). Availability uncertain.",
                    "flags": flags,
                    "data": {"injury_status": status}
                }

    # Player not on injury list — assume fit
    analysis = f"{player['name']} is not on the injury list. Assumed fit and available to start."
    return {
        "score": 88,
        "analysis": analysis,
        "flags": flags,
        "data": {"injury_status": "fit"}
    }


# ── Dimension 6: Manager & Tactical Signals (weight 5%) — STUB ───────────────

def dim_manager_tactical() -> dict:
    return {
        "score": 60,
        "analysis": "Tactical signal analysis not yet automated. Default neutral score assigned. Will integrate press conference NLP and lineup pattern analysis in future versions.",
        "flags": ["stub"],
        "data": {}
    }


# ── Dimension 7: Market Intelligence (weight 10%) ────────────────────────────

def dim_market_intelligence(
    fixture_id: int | None,
    player: dict,
    model_goal_prob: float,
    fpl_stats: dict | None = None,
) -> dict:
    """Compare market odds to model probability; also surfaces ownership/transfer intel."""
    import db as _db
    flags = []
    score = 50
    analysis_parts = []
    market_data: dict = {}

    # ── Betting odds edge ─────────────────────────────────────────────────────
    edge_pct = None
    best_team_odds = None
    implied_prob = None

    if fixture_id:
        odds_rows = _db.get_odds_for_fixture(fixture_id)
        if odds_rows:
            h2h_odds = [o for o in odds_rows if o["market"] == "h2h"]
            fixture = _db.get_fixture_by_id(fixture_id)
            player_team = player.get("team", "")
            if fixture:
                team_outcome = (
                    fixture["home_team"]
                    if _fuzzy_team_match(player_team, fixture.get("home_team", ""))
                    else fixture["away_team"]
                )
            else:
                team_outcome = player_team

            team_odds_list = [
                o["odds"] for o in h2h_odds
                if _fuzzy_team_match(o.get("outcome", ""), team_outcome)
            ]
            best_team_odds = max(team_odds_list) if team_odds_list else None
            implied_prob = (1 / best_team_odds) if best_team_odds else None

            if implied_prob and model_goal_prob > 0:
                edge_pct = (model_goal_prob - implied_prob) * 100
                if edge_pct > 10:
                    score = min(score + 35, 95)
                    flags.append("strong_market_edge")
                elif edge_pct > 5:
                    score = min(score + 20, 80)
                    flags.append("positive_market_edge")
                elif edge_pct > 0:
                    score = min(score + 10, 70)
                elif edge_pct > -5:
                    score = max(score - 5, 40)
                else:
                    score = max(score - 20, 25)
                    flags.append("market_overpriced")

            if best_team_odds:
                analysis_parts.append(
                    f"Best team odds: {best_team_odds:.2f} (implied {(implied_prob or 0)*100:.1f}%)."
                )
            if edge_pct is not None:
                analysis_parts.append(
                    f"Model prob: {model_goal_prob*100:.1f}%. Edge: {edge_pct:+.1f}%."
                )

            market_data.update({
                "best_team_odds": best_team_odds,
                "implied_prob": round(implied_prob, 3) if implied_prob else None,
                "model_prob": round(model_goal_prob, 3),
                "edge_pct": round(edge_pct, 1) if edge_pct is not None else None,
            })

    # ── FPL ownership & transfer intelligence ────────────────────────────────
    if fpl_stats:
        ownership = fpl_stats.get("ownership_pct", 0) or 0
        t_in = fpl_stats.get("transfers_in_event", 0) or 0
        t_out = fpl_stats.get("transfers_out_event", 0) or 0
        net_transfers = t_in - t_out
        price = fpl_stats.get("price", 0) or 0
        cost_change = fpl_stats.get("cost_change_start", 0) or 0

        # High net transfers → market confidence in this player
        if net_transfers > 200_000:
            score = min(score + 10, 95)
            flags.append("high_fpl_transfers_in")
        elif net_transfers < -200_000:
            score = max(score - 10, 20)
            flags.append("high_fpl_transfers_out")

        # Rising price is a sentiment signal
        if cost_change > 0:
            flags.append("price_rising")
        elif cost_change < -5:
            flags.append("price_falling")

        analysis_parts.append(
            f"FPL ownership: {ownership:.1f}%. "
            f"GW transfers: +{t_in:,} / -{t_out:,} (net {net_transfers:+,}). "
            f"Price: £{price:.1f}m ({cost_change:+.1f} since start)."
        )

        market_data.update({
            "fpl_ownership_pct": round(ownership, 1),
            "transfers_in_event": t_in,
            "transfers_out_event": t_out,
            "net_transfers": net_transfers,
            "price": round(price, 1),
            "cost_change_start": cost_change,
        })

    if not analysis_parts:
        analysis_parts.append("No odds or FPL market data available for this player/fixture.")

    return {
        "score": _clamp(score),
        "analysis": " ".join(analysis_parts),
        "flags": flags,
        "data": market_data,
    }


def _fuzzy_team_match(a: str, b: str) -> bool:
    a, b = a.lower(), b.lower()
    return a in b or b in a or a[:4] == b[:4]


# ── Dimension 8: Role & Usage Changes (weight 5%) — STUB ─────────────────────

def dim_role_usage() -> dict:
    return {
        "score": 60,
        "analysis": "Role and usage change analysis requires heatmap/positional data not yet available. Monitoring substitution patterns as a proxy.",
        "flags": ["stub"],
        "data": {}
    }


# ── Dimension 9: Psychological & Narrative (weight 5%) — STUB ────────────────

def dim_psychological(match_logs: list[dict]) -> dict:
    """Stub — derive basic streak psychology from results."""
    flags = []
    recent_5 = match_logs[:5]
    if not recent_5:
        return {"score": 60, "analysis": "No recent data.", "flags": [], "data": {}}

    # Count wins in last 5
    wins = sum(1 for m in recent_5 if m.get("result", "").endswith("W"))
    goals_streak = sum(m.get("goals", 0) for m in recent_5)

    score = 55
    if wins >= 4:
        score = 75
        flags.append("team_on_winning_run")
    elif wins <= 1:
        score = 40
        flags.append("team_poor_form")

    if goals_streak >= 4:
        flags.append("player_on_scoring_streak")

    analysis = f"Team form: {wins}W in last 5. Player scored {goals_streak}G in last 5."

    return {
        "score": _clamp(score),
        "analysis": analysis,
        "flags": flags,
        "data": {"wins_last5": wins, "goals_last5": goals_streak}
    }


# ── Dimension 10: External Conditions (weight 3%) — STUB ─────────────────────

def dim_external_conditions() -> dict:
    return {
        "score": 65,
        "analysis": "Weather and external condition analysis not yet integrated. Assuming standard conditions. Will add weather API in next iteration.",
        "flags": ["stub"],
        "data": {}
    }


# ── Dimension 11: Change Detection (weight 7%) ───────────────────────────────

def dim_change_detection(match_logs: list[dict], all_injuries: list[dict],  # noqa: ARG001
                          player: dict) -> dict:  # noqa: ARG001
    """Detect meaningful changes since last report: form trajectory, new injuries."""
    flags = []
    score = 60

    if len(match_logs) < 2:
        return {
            "score": score,
            "analysis": "Insufficient match history for change detection.",
            "flags": [], "data": {}
        }

    # xG trajectory: is it rising or falling?
    last_3_xg = [m.get("xG", 0) for m in match_logs[:3]]
    last_3_to_6_xg = [m.get("xG", 0) for m in match_logs[3:6]]

    avg_recent = sum(last_3_xg) / len(last_3_xg) if last_3_xg else 0
    avg_prior = sum(last_3_to_6_xg) / len(last_3_to_6_xg) if last_3_to_6_xg else avg_recent

    if avg_recent > avg_prior * 1.2:
        score += 15
        flags.append("xG_rising")
    elif avg_recent < avg_prior * 0.8:
        score -= 10
        flags.append("xG_declining")

    # Minutes trend (being subbed more?)
    recent_mins = [m.get("minutes", 90) for m in match_logs[:4]]
    avg_mins = sum(recent_mins) / len(recent_mins) if recent_mins else 90
    if avg_mins < 70:
        score -= 10
        flags.append("reduced_minutes")

    analysis = (
        f"xG over last 3 games: {sum(last_3_xg):.2f} vs prior 3: {sum(last_3_to_6_xg):.2f}. "
        f"Avg minutes last 4 starts: {avg_mins:.0f}. "
        + ("Form improving." if "xG_rising" in flags else
           "Form declining." if "xG_declining" in flags else "Form stable.")
    )

    return {
        "score": _clamp(score),
        "analysis": analysis,
        "flags": flags,
        "data": {
            "avg_xg_recent": round(avg_recent, 2),
            "avg_xg_prior": round(avg_prior, 2),
            "avg_mins": round(avg_mins, 1),
        }
    }


# ── Dimension 12: Risk Indicators (weight 5%) ────────────────────────────────

def dim_risk_indicators(
    match_logs: list[dict],
    all_injuries: list[dict],
    player: dict,
    fpl_stats: dict | None = None,
) -> dict:
    """Rotation risk, availability, card risk — enhanced with real FPL starts data."""
    flags = []
    risk_flags = []

    player_name = player.get("name", "").lower()

    # ── Rotation risk ─────────────────────────────────────────────────────────
    if fpl_stats and fpl_stats.get("starts") is not None:
        # Use real FPL starts data when available
        starts = fpl_stats.get("starts", 0) or 0
        fpl_minutes = fpl_stats.get("minutes", 0) or 0
        gw_played = max(max(starts, fpl_minutes // 90), 1)
        start_rate = starts / gw_played
        avg_mins = fpl_minutes / gw_played

        from engine.fpl_points import rotation_risk_label
        rotation_risk = rotation_risk_label(starts, gw_played, avg_mins)

        if rotation_risk == "HIGH":
            risk_flags.append("high_rotation_risk")
            flags.append("high_rotation_risk")
        elif rotation_risk == "MEDIUM":
            risk_flags.append("rotation_risk")

        early_sub_pct = round((1 - start_rate) * 100)
        lineup_certainty = round(start_rate * 100)

        chance = fpl_stats.get("chance_of_playing_next_round")
        if chance is not None and chance < 75:
            risk_flags.append("doubt_for_next_gw")
            flags.append("doubt_for_next_gw")
    else:
        # Fallback: infer from match log minutes
        recent_10 = match_logs[:10]
        sub_offs = sum(1 for m in recent_10 if m.get("minutes", 90) < 80)
        rotation_risk = "HIGH" if sub_offs >= 4 else ("MEDIUM" if sub_offs >= 2 else "LOW")
        if sub_offs >= 4:
            risk_flags.append("high_rotation_risk")
            flags.append("high_rotation_risk")
        elif sub_offs >= 2:
            risk_flags.append("rotation_risk")
        early_sub_pct = round(sub_offs / max(len(recent_10), 1) * 100)
        lineup_certainty = max(30, 95 - sub_offs * 5)
        chance = None
        avg_mins = 90.0
        start_rate = 1.0

    # ── Card / suspension risk ────────────────────────────────────────────────
    yellows = (fpl_stats or {}).get("yellow_cards", 0) or 0
    reds = (fpl_stats or {}).get("red_cards", 0) or 0
    booking_risk = "HIGH" if yellows >= 8 or reds >= 1 else ("MEDIUM" if yellows >= 4 else "LOW")
    if booking_risk == "HIGH":
        risk_flags.append("card_risk")
    if yellows >= 9:
        flags.append("one_yellow_from_suspension")

    # ── Injury flag ───────────────────────────────────────────────────────────
    injury_flag = any(
        i.get("player_name", "").lower() == player_name for i in all_injuries
    )
    if injury_flag:
        risk_flags.append("injury_concern")

    score = _clamp(100 - len(risk_flags) * 15)

    analysis_parts = [
        f"Rotation risk: {rotation_risk}. Lineup certainty: {lineup_certainty}%.",
        f"Card risk: {booking_risk} ({yellows} yellows, {reds} reds this season).",
        f"Injury listed: {'Yes' if injury_flag else 'No'}.",
    ]
    if chance is not None and chance < 100:
        analysis_parts.append(f"Chance of playing next GW: {chance}%.")

    return {
        "score": score,
        "analysis": " ".join(analysis_parts),
        "flags": flags,
        "data": {
            "rotation_risk": rotation_risk,
            "booking_risk": booking_risk,
            "early_sub_pct": early_sub_pct,
            "lineup_certainty": lineup_certainty,
            "injury_flag": injury_flag,
            "yellow_cards": yellows,
            "red_cards": reds,
            "chance_of_playing": chance,
            "risk_flag_count": len(risk_flags),
        }
    }


# ── Dimension 13: Output Metrics (weight 5%) ─────────────────────────────────

def dim_output_metrics(all_scores: list[float], weighted_score: float) -> dict:
    """Synthesized final metrics — depends on all other dimensions."""
    confidence = "HIGH" if weighted_score >= 75 else ("MEDIUM" if weighted_score >= 55 else "LOW")
    spread = max(all_scores) - min(all_scores) if all_scores else 0

    analysis = (
        f"Composite Edge Score: {weighted_score:.0f}. Confidence: {confidence}. "
        f"Score spread across dimensions: {spread:.0f} pts "
        f"({'consistent' if spread < 25 else 'high variance'} signal)."
    )

    return {
        "score": _clamp(weighted_score),
        "analysis": analysis,
        "flags": [],
        "data": {
            "composite_score": round(weighted_score, 1),
            "confidence": confidence,
            "score_spread": round(spread, 1),
        }
    }
