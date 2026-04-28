"""
Claude-powered player chatbot.
Stateless: caller passes full conversation history each request.
"""
from __future__ import annotations

import json
import logging

import anthropic

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import db
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

MAX_HISTORY = 20  # keep last N turns to avoid token bloat


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
        (i for i in injuries if i.get("player_name", "").lower() == name.lower()),
        None
    )

    fixtures = db.get_upcoming_fixtures(team=team, limit=2)
    next_fix = fixtures[0] if fixtures else None

    # Format recent form
    form_lines = []
    for m in match_logs:
        form_lines.append(
            f"  {m.get('date','?')} vs {m.get('opponent','?')} ({m.get('home_away','?')}) — "
            f"{m.get('goals',0)}G {m.get('assists',0)}A, xG {m.get('xG',0):.2f}, "
            f"result: {m.get('result','?')}"
        )
    form_text = "\n".join(form_lines) if form_lines else "  No recent match data"

    # Format injury
    if injury:
        inj_text = f"{injury.get('status','Unknown')} — {injury.get('injury_type','Unknown')}. Expected return: {injury.get('expected_return','Unknown')}"
    else:
        inj_text = "No current injury recorded"

    # Format next fixture
    if next_fix:
        is_home = team.lower() in next_fix.get("home_team","").lower()
        opponent = next_fix.get("away_team") if is_home else next_fix.get("home_team")
        venue = "Home" if is_home else "Away"
        fix_text = f"{opponent} ({venue}) on {next_fix.get('date','TBD')}"
    else:
        fix_text = "No upcoming fixture data"

    return f"""You are EdgeLayer's AI analyst specialising in Premier League player performance and pre-match betting intelligence.

The user is asking about: {name} ({position}, {team})

CURRENT SEASON STATS (2024-25):
  Goals: {stats.get('goals', 'N/A')}  Assists: {stats.get('assists', 'N/A')}
  xG: {stats.get('xG', 'N/A')}  xA: {stats.get('xA', 'N/A')}
  Shots: {stats.get('shots', 'N/A')}  Appearances: {stats.get('appearances', 'N/A')}
  Minutes: {stats.get('minutes', 'N/A')}

RECENT FORM (last 5 matches):
{form_text}

INJURY STATUS: {inj_text}

NEXT FIXTURE: {fix_text}

INSTRUCTIONS:
- Answer questions about this player with data-driven analysis using the numbers above
- If the user provides additional context (transfer news, manager decisions, team form, injuries not in the data), factor it into your analysis and reasoning
- Be specific — cite actual numbers, not vague generalisations
- Keep responses focused (2-4 paragraphs unless asked for more)
- When estimating probabilities, use the season xG/shot data as your base rate and reason from there
- Do not add disclaimers about gambling — the platform already handles that
- If asked about something genuinely unknown (future match results, undisclosed injuries), reason probabilistically rather than refusing"""


async def chat(player_id: int, message: str, history: list[dict]) -> str:
    """
    Send a message and return the assistant reply.
    history: list of {"role": "user"|"assistant", "content": str}
    """
    if not ANTHROPIC_API_KEY:
        return "Claude API key not configured. Please set ANTHROPIC_API_KEY in environment variables."

    system_prompt = _build_system_prompt(player_id)

    # Trim history to avoid token bloat
    trimmed = history[-(MAX_HISTORY * 2):]

    messages = trimmed + [{"role": "user", "content": message}]

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    try:
        response = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text.strip()
    except Exception as e:
        logger.error(f"Chatbot API error [{type(e).__name__}]: {e}")
        # Surface more detail in development to help diagnose
        detail = getattr(e, 'message', None) or getattr(e, 'body', None) or str(e)
        return f"API error: {detail}"
