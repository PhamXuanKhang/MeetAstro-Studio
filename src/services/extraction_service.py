"""
Extraction service — rule-based extraction dùng regex để cross-validate vs AI output.
"""
from __future__ import annotations

import re
from typing import Any


def rule_based_extraction(transcript: str) -> list[dict[str, Any]]:
    """Trích xuất action items từ transcript bằng regex pattern."""
    action_regex = re.compile(
        r"(?P<assignee>[A-Z][a-z]+)\s*(?:will|to|must|should)\s*(?P<task>.+?)(?:\.|$)",
        re.IGNORECASE,
    )
    items = []
    for line in transcript.splitlines():
        text = line.strip()
        if not text:
            continue
        match = action_regex.search(text)
        if not match:
            continue
        deadline_match = re.search(
            r"(by\s+\w+\s*\d{0,2}|next\s+week|tomorrow)", text, re.IGNORECASE
        )
        items.append({
            "title": match.group("task")[:120],
            "description": text,
            "assignee": match.group("assignee") or "Unassigned",
            "deadline": deadline_match.group(0) if deadline_match else "",
            "priority": "medium",
            "context": text,
        })
    return items
