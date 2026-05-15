"""Lightweight language detection helpers for analysis prompts."""
from __future__ import annotations

import re


_VIETNAMESE_CHAR_RE = re.compile(
    r"[\u0102\u0103\u00C2\u00E2\u0110\u0111\u00CA\u00EA\u00D4\u00F4\u01A0\u01A1\u01AF\u01B0"
    r"\u00C0-\u00C3\u00C8-\u00CA\u00CC-\u00CD\u00D2-\u00D5\u00D9-\u00DA\u00DD"
    r"\u00E0-\u00E3\u00E8-\u00EA\u00EC-\u00ED\u00F2-\u00F5\u00F9-\u00FA\u00FD"
    r"\u1EA0-\u1EF9]",
    re.IGNORECASE,
)

_VIETNAMESE_WORDS = {
    "anh", "chi", "em", "toi", "minh", "ban", "cac", "nhung", "duoc", "khong",
    "trong", "ngoai", "voi", "cho", "can", "nen", "phai", "se", "da", "dang",
    "viec", "nhiem", "vu", "hop", "du an", "khach", "hang", "san pham",
}

_ENGLISH_WORDS = {
    "the", "and", "that", "this", "with", "for", "from", "will", "should",
    "meeting", "project", "customer", "team", "task", "action", "decision",
    "today", "need", "review", "assign", "analysis", "output", "follow", "next",
}


def detect_primary_language(text: str) -> str:
    """Return a stable language label for prompt guardrails.

    The project currently needs strong English/Vietnamese behavior. The detector
    intentionally stays lightweight and deterministic because the model itself is
    still asked to follow the detected source language.
    """
    sample = " ".join(text[:12000].lower().split())
    if not sample:
        return "the source language"

    vietnamese_chars = len(_VIETNAMESE_CHAR_RE.findall(sample))
    if vietnamese_chars >= 2:
        return "Vietnamese"

    words = re.findall(r"[a-zA-Z]+", sample)
    if not words:
        return "the source language"

    padded = f" {sample} "
    vietnamese_hits = sum(1 for word in _VIETNAMESE_WORDS if f" {word} " in padded)
    english_hits = sum(1 for word in _ENGLISH_WORDS if word in words)

    if vietnamese_hits >= 5 and vietnamese_hits >= english_hits:
        return "Vietnamese"
    if english_hits >= 3 and english_hits > vietnamese_hits:
        return "English"
    return "the source language"
