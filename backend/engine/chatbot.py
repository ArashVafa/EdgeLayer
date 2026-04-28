"""
Player chatbot — context-aware Q&A via unified LLM client.
Stateless: caller passes full conversation history each request.
"""
from __future__ import annotations

import logging

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import db
from config import LLM_PROVIDER
from engine.llm import chat_complete

logger = logging.getLogger(__name__)

MAX_HISTORY = 20


def _build_system_prompt(player_id: int) -> str:
    player = db.get_player(player_id)
    if not player:
        return "You are EdgeLayer's AI analyst for Premier League pre-match intelligence."

    name = player.get("name", "Unknown")
    team = player.get("team", "Unknown")
    position = player.get("position", "Unknown")

    stats_rows = db.get_player_stats(player_id)
    stats = (stats_rows[0] if isinstance(stats_rows, list) and stats_rows else stats_rows) or {}

    match_logs = db.get_match_logs(player_id, limit=5)
    injuries = db.get_injuries()
    injury = next(
        (i for i in injuries if i.get("player_name", "").lower() == name.lower()), None
    )

    fixtures = db.get_upcoming_fixtures(team=team, limit=2)
    next_fix = fixtures[0] if fixtures else None

    form_lines = [
        f"  {m.get('date','?')} vs {m.get('opponent','?')} ({m.get('home_away','?')}) — "
        f"{m.get('goals',0)}G {m.get('assists',0)}A xG:{m.get('xG',0):.2f} {m.get('result','?')}"
        for m in match_logs
    ]
    form_text = "\n".join(form_lines) if form_lines else "  No recent match data"

    inj_text = (
        f"{injury.get('status')} — {injury.get('injury_type')}. Return: {injury.get('expected_return')}"
        if injury else "No current injury recorded"
    )

    if next_fix:
        is_home = team.lower() in next_fix.get("home_team", "").lower()
        opponent = next_fix.get("away_team") if is_home else next_fix.get("home_team")
        fix_text = f"{opponent} ({'Home' if is_home else 'Away'}) on {next_fix.get('date', 'TBD')}"
    else:
        fix_text = "No upcoming fixture data"

    return f"""You are EdgeLayer's AI analyst specialising in Premier League player performance and pre-match betting intelligence.

Player: {name} ({position}, {team})

SEASON STATS (2024-25):
  Goals: {stats.get('goals','N/A')}  Assists: {stats.get('assists','N/A')}
  xG: {stats.get('xG','N/A')}  xA: {stats.get('xA','N/A')}
  Shots: {stats.get('shots','N/A')}  Apps: {stats.get('appearances','N/A')}  Mins: {stats.get('minutes','N/A')}

RECENT FORM (last 5):
{form_text}

INJURY: {inj_text}
NEXT FIXTURE: {fix_text}

Answer questions about this player with data-driven analysis. Cite actual numbers.
If the user provides extra context (transfer news, tactical changes, fitness updates), factor it in.
Estimate probabilities using xG/shot data as your base rate.
Keep responses focused (2-4 paragraphs). Do not add gambling disclaimers."""


async def chat(player_id: int, message: str, history: list[dict]) -> str:
    if LLM_PROVIDER == "none":
        return "No LLM configured. Add GROQ_API_KEY (free at console.groq.com) or ANTHROPIC_API_KEY."

    system = _build_system_prompt(player_id)
    trimmed = history[-(MAX_HISTORY * 2):]
    messages = trimmed + [{"role": "user", "content": message}]

    try:
        return await chat_complete(
            system=system,
            messages=messages,
            max_tokens=1024,
            use_case="chat",
            player_id=player_id,
        )
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        detail = getattr(e, 'message', None) or str(e)
        return f"Sorry, something went wrong: {detail}"
