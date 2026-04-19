"""
Summarization service — gọi OpenAI async để tạo summary + key_decisions + discussion_points + parking_lot.
Hỗ trợ streaming mode: generate_summary_stream() yield từng token text.
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator, Optional

import openai

from src.config import OPENAI_API_KEY, OPENAI_MODEL, get_logger

logger = get_logger(__name__)

_SYSTEM_PROMPT = """\
Bạn là AI trợ lý phân tích cuộc họp. Hãy tạo tóm tắt ngắn gọn từ transcript dưới đây.
Trả về JSON với các trường:
- "summary": string — tóm tắt tổng quan cuộc họp (2-5 câu)
- "key_decisions": list[string] — các quyết định chính đã được chốt
- "discussion_points": list[string] — các điểm thảo luận chính
- "parking_lot_items": list[string] — các vấn đề chưa giải quyết, tạm gác

Chỉ trả về JSON, không thêm text khác.
"""

_STREAM_SYSTEM_PROMPT = """\
Bạn là AI trợ lý phân tích cuộc họp. Hãy tạo tóm tắt ngắn gọn từ transcript dưới đây.
Chỉ viết phần tóm tắt tổng quan (2-5 câu), không thêm tiêu đề hay định dạng đặc biệt.
"""


async def generate_summary(
    transcript: str,
    api_key: str = OPENAI_API_KEY,
    model: str = OPENAI_MODEL,
) -> dict[str, Any]:
    """Gọi OpenAI async để sinh summary từ transcript.

    Returns dict với keys: summary, key_decisions, discussion_points, parking_lot_items.
    """
    client = openai.AsyncOpenAI(api_key=api_key)
    try:
        response = await client.chat.completions.create(
            model=model,
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
        logger.warning("generate_summary thất bại: %s — dùng fallback rỗng.", exc)
        result = {}

    return {
        "summary": result.get("summary", ""),
        "key_decisions": result.get("key_decisions", []),
        "discussion_points": result.get("discussion_points", []),
        "parking_lot_items": result.get("parking_lot_items", []),
    }


async def generate_summary_stream(
    transcript: str,
    api_key: str = OPENAI_API_KEY,
    model: str = OPENAI_MODEL,
) -> AsyncIterator[str]:
    """Yield từng token summary từ OpenAI streaming API."""
    client = openai.AsyncOpenAI(api_key=api_key)
    try:
        stream = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _STREAM_SYSTEM_PROMPT},
                {"role": "user", "content": transcript},
            ],
            temperature=0.2,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta
    except Exception as exc:
        logger.warning("generate_summary_stream thất bại: %s", exc)
        yield ""
