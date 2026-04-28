"""
Unified LLM client — Groq (free, default) or Anthropic.
Provider selected via LLM_PROVIDER env var or auto-detected from available keys.
Every call is logged to llm_log for future training data collection.
"""
from __future__ import annotations

import logging
import time

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import db
from config import (
    GROQ_API_KEY, ANTHROPIC_API_KEY,
    GROQ_MODEL, CLAUDE_MODEL, LLM_PROVIDER,
)

logger = logging.getLogger(__name__)


async def chat_complete(
    *,
    system: str,
    messages: list[dict],
    max_tokens: int = 1024,
    use_case: str = "chat",
    player_id: int | None = None,
) -> str:
    """
    Send a chat completion request to the configured LLM provider.
    Logs input/output/latency to llm_log automatically.
    """
    if LLM_PROVIDER == "none":
        raise RuntimeError("No LLM API key configured. Set GROQ_API_KEY or ANTHROPIC_API_KEY.")

    provider = LLM_PROVIDER
    model = GROQ_MODEL if provider == "groq" else CLAUDE_MODEL

    t0 = time.monotonic()
    text = ""
    in_tok = out_tok = 0

    try:
        if provider == "groq":
            text, in_tok, out_tok = await _call_groq(system, messages, max_tokens, model)
        else:
            text, in_tok, out_tok = await _call_anthropic(system, messages, max_tokens, model)

        logger.info(f"LLM [{provider}/{model}] {use_case}: {in_tok}+{out_tok} tokens")
        return text

    except Exception as e:
        logger.error(f"LLM call failed [{provider}/{model}]: {e}")
        raise

    finally:
        latency = int((time.monotonic() - t0) * 1000)
        user_msg = messages[-1]["content"] if messages else ""
        try:
            db.log_llm(
                provider=provider, model=model, use_case=use_case,
                player_id=player_id, user_message=user_msg, response=text,
                input_tokens=in_tok, output_tokens=out_tok, latency_ms=latency,
            )
        except Exception as log_err:
            logger.warning(f"LLM log write failed: {log_err}")


async def _call_groq(system: str, messages: list[dict], max_tokens: int, model: str):
    from groq import AsyncGroq
    client = AsyncGroq(api_key=GROQ_API_KEY)
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system}] + messages,
        max_tokens=max_tokens,
        temperature=0.7,
    )
    text = resp.choices[0].message.content.strip()
    usage = resp.usage
    return text, usage.prompt_tokens, usage.completion_tokens


async def _call_anthropic(system: str, messages: list[dict], max_tokens: int, model: str):
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    resp = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    text = resp.content[0].text.strip()
    usage = resp.usage
    return text, usage.input_tokens, usage.output_tokens
