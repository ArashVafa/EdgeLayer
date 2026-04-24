"""
Claude API narrative generation.
Sends structured report data to Claude and gets 3 betting narratives.
"""
import json
import logging

import anthropic

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are EdgeLayer's narrative engine. Given structured pre-bet intelligence data for a player's upcoming match, generate three betting narratives.

1. AGGRESSIVE — emphasizes upside, suggests higher-risk props (multi-goal, first scorer, parlays), acknowledges risks briefly
2. AVERAGE — balanced assessment, highlights the strongest angle, notes key risks, gives a clear verdict
3. CONSERVATIVE — emphasizes risks and caveats, suggests safer bets (shots on target, team totals), warns against high-variance props

Each narrative should be 2-4 paragraphs. Use specific numbers from the data. Mention the edge score and confidence level. Be direct and opinionated — this is decision support, not a textbook.

Do NOT include any disclaimers about gambling. The app already has those.

Return ONLY a valid JSON object with exactly these keys:
{
  "aggressive": "...",
  "average": "...",
  "conservative": "..."
}

Each value is a plain text narrative (no markdown, no HTML tags)."""


def _build_payload(report: dict) -> str:
    """Strip the report to the essentials for Claude to keep cost low."""
    player = report.get("player", {})
    stats = report.get("stats", {})
    fixture = report.get("fixture") or {}
    opponent = report.get("opponent", "TBD")

    # Pull top dimension scores only
    dims = report.get("dimensions", {})
    dim_summary = {
        k: {"score": v["score"], "analysis": v["analysis"][:200]}
        for k, v in dims.items()
    }

    payload = {
        "player": {
            "name": player.get("name"),
            "team": player.get("team"),
            "position": player.get("position"),
        },
        "season_stats": {
            "goals": stats.get("goals"),
            "assists": stats.get("assists"),
            "xG": stats.get("xG"),
            "appearances": stats.get("appearances"),
            "minutes": stats.get("minutes"),
        },
        "next_fixture": {
            "opponent": opponent,
            "home_away": "Home" if _is_home(player.get("team", ""), fixture) else "Away",
            "date": fixture.get("date", "TBD"),
        },
        "edge_score": report.get("edge_score"),
        "confidence": report.get("confidence"),
        "risk_level": report.get("risk_level"),
        "risk_flags": report.get("all_flags", [])[:8],
        "key_dimensions": dim_summary,
        "market_data": report.get("market_data", {}),
        "recent_form": [
            {
                "opponent": m.get("opponent"),
                "goals": m.get("goals"),
                "assists": m.get("assists"),
                "xG": m.get("xG"),
                "result": m.get("result"),
            }
            for m in report.get("match_logs", [])[:5]
        ],
    }
    return json.dumps(payload, indent=2)


def _is_home(player_team: str, fixture: dict) -> bool:
    home = fixture.get("home_team", "")
    return player_team.lower() in home.lower() or home.lower() in player_team.lower()


async def generate_narratives(report: dict) -> dict:
    """
    Call Claude API and return {"aggressive": str, "average": str, "conservative": str}.
    Falls back to placeholder text on error.
    """
    if not ANTHROPIC_API_KEY:
        logger.warning("ANTHROPIC_API_KEY not set — returning placeholder narratives")
        return _placeholder_narratives(report)

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    payload = _build_payload(report)

    try:
        message = await client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"Generate betting narratives for this player report:\n\n{payload}"}
            ],
        )

        raw = message.content[0].text.strip()

        # Strip markdown fences if Claude added them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        narratives = json.loads(raw)
        return {
            "aggressive": narratives.get("aggressive", ""),
            "average": narratives.get("average", ""),
            "conservative": narratives.get("conservative", ""),
        }

    except json.JSONDecodeError as e:
        logger.error(f"Claude returned non-JSON: {e}")
        return _placeholder_narratives(report)
    except Exception as e:
        logger.error(f"Claude API call failed: {e}")
        return _placeholder_narratives(report)


def _placeholder_narratives(report: dict) -> dict:
    """Placeholder when Claude is unavailable."""
    player_name = report.get("player", {}).get("name", "This player")
    edge = report.get("edge_score", 0)
    confidence = report.get("confidence", "MEDIUM")
    opponent = report.get("opponent", "their next opponent")

    return {
        "average": (
            f"{player_name} heads into this fixture with an Edge Score of {edge} and {confidence} confidence. "
            f"The data points to a competitive edge vs {opponent}. "
            "Review the dimension cards above for the key supporting signals. "
            "Narrative generation via Claude API requires a valid API key."
        ),
        "aggressive": (
            f"Edge Score {edge} — {confidence} confidence. {player_name} is set up well vs {opponent}. "
            "The aggressive narrative would highlight upside props and parlay angles. "
            "Set ANTHROPIC_API_KEY to enable full narrative generation."
        ),
        "conservative": (
            f"Caution warranted. Edge Score {edge} with {confidence} confidence vs {opponent}. "
            "The conservative narrative would surface key risks and lower-variance bet angles. "
            "Set ANTHROPIC_API_KEY to enable full narrative generation."
        ),
    }
