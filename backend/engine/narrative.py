"""
Narrative generation — three betting angles via unified LLM client.
"""
from __future__ import annotations

import json
import logging
import re

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import GROQ_API_KEY, ANTHROPIC_API_KEY
from engine.llm import chat_complete

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are EdgeLayer's narrative engine. Given structured pre-bet intelligence data for a player's upcoming match, generate three betting narratives.

1. AGGRESSIVE — emphasises upside, suggests higher-risk props (multi-goal, first scorer, parlays), acknowledges risks briefly
2. AVERAGE — balanced assessment, highlights the strongest angle, notes key risks, gives a clear verdict
3. CONSERVATIVE — emphasises risks and caveats, suggests safer bets (shots on target, team totals), warns against high-variance props

Each narrative should be 2-4 paragraphs. Use specific numbers from the data. Mention the edge score and confidence level. Be direct and opinionated — this is decision support, not a textbook.

Do NOT include any disclaimers about gambling. The app already has those.

Return ONLY valid JSON with exactly these keys — no markdown fences, no extra text:
{"aggressive": "...", "average": "...", "conservative": "..."}"""


def _build_payload(report: dict) -> str:
    player = report.get("player", {})
    stats = report.get("stats", {})
    fixture = report.get("fixture") or {}
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
            "opponent": report.get("opponent", "TBD"),
            "home_away": "Home" if _is_home(player.get("team", ""), fixture) else "Away",
            "date": fixture.get("date", "TBD"),
        },
        "edge_score": report.get("edge_score"),
        "confidence": report.get("confidence"),
        "risk_level": report.get("risk_level"),
        "risk_flags": report.get("all_flags", [])[:8],
        "key_dimensions": dim_summary,
        "recent_form": [
            {"opponent": m.get("opponent"), "goals": m.get("goals"),
             "assists": m.get("assists"), "xG": m.get("xG"), "result": m.get("result")}
            for m in report.get("match_logs", [])[:5]
        ],
    }
    return json.dumps(payload, indent=2)


def _is_home(player_team: str, fixture: dict) -> bool:
    home = fixture.get("home_team", "")
    return player_team.lower() in home.lower() or home.lower() in player_team.lower()


def _extract_json(raw: str) -> dict:
    """Extract JSON from response, handling markdown fences and stray text."""
    # Strip markdown fences
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    # Find the first {...} block
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(raw)


async def generate_narratives(report: dict) -> dict:
    if not (GROQ_API_KEY or ANTHROPIC_API_KEY):
        logger.warning("No LLM key set — returning placeholder narratives")
        return _placeholder_narratives(report)

    player_id = report.get("player", {}).get("id")
    payload = _build_payload(report)

    try:
        raw = await chat_complete(
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Generate betting narratives for this player report:\n\n{payload}"
            }],
            max_tokens=2048,
            use_case="narrative",
            player_id=player_id,
        )

        narratives = _extract_json(raw)
        return {
            "aggressive": narratives.get("aggressive", ""),
            "average": narratives.get("average", ""),
            "conservative": narratives.get("conservative", ""),
        }

    except json.JSONDecodeError as e:
        logger.error(f"LLM returned non-JSON: {e}\nRaw: {raw[:300]}")
        return _placeholder_narratives(report)
    except Exception as e:
        logger.error(f"Narrative generation failed: {e}")
        return _placeholder_narratives(report)


def _placeholder_narratives(report: dict) -> dict:
    name = report.get("player", {}).get("name", "This player")
    edge = report.get("edge_score", 0)
    confidence = report.get("confidence", "MEDIUM")
    opponent = report.get("opponent", "their next opponent")
    return {
        "average": (
            f"{name} heads into this fixture with an Edge Score of {edge} and {confidence} confidence "
            f"vs {opponent}. Review the dimension cards above for key signals. "
            "Set GROQ_API_KEY (free) or ANTHROPIC_API_KEY to enable full narrative generation."
        ),
        "aggressive": (
            f"Edge Score {edge} — {confidence} confidence. {name} vs {opponent}. "
            "Set GROQ_API_KEY to enable aggressive narrative generation."
        ),
        "conservative": (
            f"Caution warranted. Edge Score {edge} with {confidence} confidence vs {opponent}. "
            "Set GROQ_API_KEY to enable conservative narrative generation."
        ),
    }
