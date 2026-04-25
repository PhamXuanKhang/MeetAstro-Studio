"""
Summarization service - call OpenAI async to generate summary + key decisions.
"""
from __future__ import annotations

import json
from typing import Any, Optional

import openai

from src.config import get_logger, get_settings

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are an AI assistant that analyzes meeting transcripts. \
Create a concise summary from the transcript below.
Return JSON with the following fields:
- "summary": string - overall summary of the meeting (2-5 sentences)
- "key_decisions": list[string] - key decisions that were finalized
- "discussion_points": list[string] - main discussion points
- "parking_lot_items": list[string] - unresolved issues, deferred items

Return only JSON, no additional text.
"""


async def generate_summary(
    transcript: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> dict[str, Any]:
    """
    Call OpenAI async to generate summary from transcript.

    Args:
        transcript: Meeting transcript text.
        api_key: OpenAI API key. If None, loads from settings.
        model: Model name. If None, loads from settings.

    Returns:
        Dict with keys: summary, key_decisions, discussion_points, parking_lot_items.
    """
    settings = get_settings()
    actual_api_key = api_key if api_key is not None else settings.openai_api_key
    actual_model = model if model is not None else settings.openai_model

    client = openai.AsyncOpenAI(api_key=actual_api_key)
    try:
        response = await client.chat.completions.create(
            model=actual_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": transcript},
            ],
            temperature=0.2,
        )
        raw = response.choices[0].message.content or "{}"
        result = json.loads(raw)
    except Exception as exc:
        logger.warning("generate_summary failed: %s - using empty fallback.", exc)
        result = {}

    return {
        "summary": result.get("summary", ""),
        "key_decisions": result.get("key_decisions", []),
        "discussion_points": result.get("discussion_points", []),
        "parking_lot_items": result.get("parking_lot_items", []),
    }
