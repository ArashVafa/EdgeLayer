"""
xFPL calculator — expected Fantasy Premier League points.

FPL scoring rules (2024/25):
  Playing <60 min: 1pt | 60+ min: 2pts
  Goal: GK=10, DEF=6, MID=5, FWD=4
  Assist: 3pts (all positions)
  Clean sheet: GK/DEF=4, MID=1, FWD=0
  Every 3 saves (GK): 1pt
  Penalty save: 5pts | Penalty miss: -2pts
  Yellow card: -1pt | Red card: -3pts
  Own goal: -2pts
  Every 2 goals conceded (GK/DEF): -1pt
  Bonus: 1–3pts (top 3 BPS per match)
  Defensive contribution (CBIT≥10 for DEF/MID/FWD): +2pts
"""
from __future__ import annotations

# element_type: 1=GKP, 2=DEF, 3=MID, 4=FWD
GOAL_PTS = {1: 10, 2: 6, 3: 5, 4: 4}
CS_PTS = {1: 4, 2: 4, 3: 1, 4: 0}
ASSIST_PTS = 3
APPEARANCE_START_PTS = 2   # 60+ mins
APPEARANCE_SUB_PTS = 1     # <60 mins
YELLOW_PTS = -1
RED_PTS = -3
PENALTY_SAVE_PTS = 5
PENALTY_MISS_PTS = -2
SAVE_PER_3_PTS = 1
CONCEDE_PER_2_PTS = -1    # GK/DEF every 2 goals conceded


def calculate_xfpl(
    element_type: int,
    xg: float,
    xa: float,
    minutes: int,
    starts: int,
    total_gw_played: int,
    clean_sheets: int = 0,
    goals_conceded: int = 0,
    yellow_cards: int = 0,
    red_cards: int = 0,
    saves: int = 0,
    bonus: int = 0,
) -> float:
    """
    Return expected FPL points per game for this player.
    element_type: 1=GKP, 2=DEF, 3=MID, 4=FWD
    """
    gw = max(total_gw_played, 1)

    xg_per_game = xg / gw
    xa_per_game = xa / gw
    start_rate = starts / gw
    cs_rate = clean_sheets / gw
    concede_rate = goals_conceded / gw
    saves_per_game = saves / gw
    yellow_rate = yellow_cards / gw
    red_rate = red_cards / gw
    bonus_per_game = bonus / gw

    # Appearance points (starters get full 60+ points, subs get ~1pt with ~30% chance)
    appearance_pts = start_rate * APPEARANCE_START_PTS + (1 - start_rate) * 0.3 * APPEARANCE_SUB_PTS

    # Expected goal / assist points
    goal_pts = xg_per_game * GOAL_PTS.get(element_type, 4)
    assist_pts = xa_per_game * ASSIST_PTS

    # Clean sheet points (weighted by start rate since subs rarely earn CS pts)
    cs_pts = cs_rate * CS_PTS.get(element_type, 0) * start_rate

    # Goals conceded deduction (GK / DEF only)
    concede_pts = 0.0
    if element_type in (1, 2):
        concede_pts = (concede_rate / 2) * CONCEDE_PER_2_PTS * start_rate

    # Save points (GK only)
    save_pts = 0.0
    if element_type == 1:
        save_pts = (saves_per_game / 3) * SAVE_PER_3_PTS

    # Card deductions
    card_pts = yellow_rate * YELLOW_PTS + red_rate * RED_PTS

    total = (
        appearance_pts
        + goal_pts
        + assist_pts
        + cs_pts
        + concede_pts
        + save_pts
        + card_pts
        + bonus_per_game
    )
    return round(total, 2)


def captaincy_score(
    element_type: int,
    xg: float,
    xa: float,
    minutes: int,
    starts: int,
    total_gw_played: int,
    clean_sheets: int = 0,
    penalty_taker: bool = False,
) -> float:
    """
    Score 0–100 reflecting captaincy value.
    Captain doubles points, so expected cap pts = 2 × xFPL.
    """
    base = calculate_xfpl(
        element_type, xg, xa, minutes, starts,
        total_gw_played, clean_sheets
    )
    cap_pts = base * 2

    if penalty_taker:
        # ~30% of PKs result in a goal (saves/misses reduce expected value)
        cap_pts += 0.3 * GOAL_PTS.get(element_type, 4)

    # 20 pts captain ceiling → 100 score
    return min(100.0, round(cap_pts / 20 * 100, 1))


def differential_score(
    ownership_pct: float,
    xfpl_per_game: float,
    form: float,
) -> float:
    """
    Score 0–100 for differential (low-owned, high-value) potential.
    Combines low ownership × high xFPL × good form.
    """
    # Players under 20% ownership qualify as differentials
    eo_factor = max(0.0, (20.0 - min(ownership_pct, 20.0)) / 20.0)
    quality_factor = min(1.0, xfpl_per_game / 12.0)
    form_factor = min(1.0, form / 10.0)

    score = (eo_factor * 0.4 + quality_factor * 0.4 + form_factor * 0.2) * 100
    return round(score, 1)


def rotation_risk_label(starts: int, total_gw: int, avg_minutes: float) -> str:
    """Return 'LOW', 'MEDIUM', or 'HIGH' rotation risk from FPL starts data."""
    gw = max(total_gw, 1)
    start_rate = starts / gw
    if start_rate >= 0.85 and avg_minutes >= 75:
        return "LOW"
    if start_rate >= 0.65 or avg_minutes >= 60:
        return "MEDIUM"
    return "HIGH"
