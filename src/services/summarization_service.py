"""
Summarization service - call OpenAI async to generate summary + key decisions.
"""
from __future__ import annotations

import json
from typing import Any, Optional

import openai

from src.config import get_logger, get_settings
from src.services.language_service import detect_primary_language

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
You are a senior meeting-note writer. Analyze the transcript and produce a concise, readable meeting note in JSON.

Write for people who did not attend the meeting:
- Use concrete nouns and project/product names from the transcript.
- Prefer specific outcomes, next steps, blockers, and rationale over generic summaries.
- Keep each list item self-contained; avoid vague items like "discussed the issue".
- Detect the transcript language and write every user-facing value in that same language.
- Do not translate English meetings into Vietnamese. Do not translate Vietnamese meetings into English.
- Ignore application UI language, JSON field names, and developer instructions when choosing output language.
- Do not invent facts, deadlines, owners, or decisions that are not supported by the transcript.

Return JSON with these fields:
- "summary": string - 3-6 sentences describing the meeting context, main conclusions, and next direction.
- "key_decisions": list[string] - finalized decisions only. Each item should be one clear sentence.
- "discussion_points": list[string] - important insights, tradeoffs, open questions, or rationale. Each item should be specific.
- "parking_lot_items": list[string] - unresolved/deferred issues, risks, blockers, or questions.

Return only JSON, no markdown and no additional text.
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
        language = detect_primary_language(transcript)
        user_content = (
            f"Detected source language: {language}.\n"
            "Write summary, key_decisions, discussion_points, and parking_lot_items "
            "in the detected source language only. Do not translate to another language.\n\n"
            f"{transcript}"
        )
        response = await client.chat.completions.create(
            model=actual_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
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
