"""
Validation service — cross-validate AI-extracted action items vs rule-based extraction.
Returns confidence scores + validation notes cho mỗi item.
"""
from __future__ import annotations

import re
from typing import Any


def _text_similarity(a: str, b: str) -> float:
    words_a = set(re.findall(r"\w+", a.lower()))
    words_b = set(re.findall(r"\w+", b.lower()))
    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def _cross_validation_score(ai_items: list[dict], rule_items: list[dict]) -> float:
    if not ai_items and not rule_items:
        return 1.0
    if not ai_items or not rule_items:
        return 0.3

    matches = 0
    for ai in ai_items:
        for rule in rule_items:
            if _text_similarity(ai.get("title", ""), rule.get("title", "")) > 0.6:
                matches += 1
                break
    union = len(ai_items) + len(rule_items) - matches
    return matches / union if union else 0.0


def _context_coherence_score(items: list[dict], transcript: str) -> float:
    if not items:
        return 1.0
    content = transcript.lower()
    total = 0.0
    for item in items:
        task_words = re.findall(
            r"\w+",
            f"{item.get('title', '')} {item.get('description', '')}".lower(),
        )
        task_words = [w for w in task_words if len(w) > 3][:8]
        found = sum(1 for w in task_words if w in content)
        if not task_words:
            total += 0.3
        else:
            total += min(1.0, found / len(task_words) + 0.2)
    return total / len(items)


def _structural_score(items: list[dict]) -> float:
    if not items:
        return 1.0
    action_verbs = {
        "implement", "create", "fix", "review", "update",
        "ship", "test", "prepare", "analyze",
    }
    score = 0.0
    for item in items:
        item_score = 0.0
        title = item.get("title", "")
        desc = item.get("description", "")
        if 6 <= len(title) <= 200:
            item_score += 0.4
        if len(desc) >= 10:
            item_score += 0.3
        text = f"{title} {desc}".lower()
        if any(v in text for v in action_verbs):
            item_score += 0.3
        score += item_score
    return score / len(items)


def validate_action_items(
    ai_items: list[dict[str, Any]],
    rule_items: list[dict[str, Any]],
    transcript: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Cross-validate AI items vs rule items.

    Returns (validated_items_with_confidence, metrics_dict).
    """
    cross_score = _cross_validation_score(ai_items, rule_items)
    context_score = _context_coherence_score(ai_items, transcript)
    structural_score = _structural_score(ai_items)

    overall = cross_score * 0.35 + context_score * 0.35 + structural_score * 0.30

    validated = []
    for item in ai_items:
        notes: list[str] = []
        item_conf = overall
        if len(item.get("title", "")) < 6:
            notes.append("Title too short")
            item_conf -= 0.15
        if not item.get("assignee") or item.get("assignee") == "Unassigned":
            notes.append("No assignee detected")
            item_conf -= 0.05
        if "?" in item.get("title", ""):
            notes.append("Possible question, not an action")
            item_conf -= 0.1

        item["confidence"] = max(0.0, min(1.0, item_conf))
        item["validation_notes"] = notes
        validated.append(item)

    metrics: dict[str, Any] = {
        "cross_validation_score": round(cross_score, 3),
        "context_coherence_score": round(context_score, 3),
        "structural_validation_score": round(structural_score, 3),
        "overall_confidence": round(overall, 3),
        "ai_items_count": len(ai_items),
        "rule_items_count": len(rule_items),
    }
    return validated, metrics
