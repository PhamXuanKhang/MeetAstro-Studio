"""Code-only retrieval and validation for work status update suggestions."""
from __future__ import annotations

import json
import re
from typing import Any

from src.schema import StatusUpdate, WorkStatus

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "have", "has",
    "was", "were", "are", "our", "you", "your", "toi", "minh", "chung",
    "ta", "cac", "nhung", "cho", "voi", "cua", "mot", "la", "thi",
}


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(text.lower())
        if len(token) >= 3 and token not in _STOPWORDS
    }


def _candidate_text(row: dict[str, Any]) -> str:
    return " ".join(
        str(value or "")
        for value in [
            row.get("title"),
            row.get("description"),
            row.get("context"),
            row.get("assignee"),
            row.get("jira_issue_key"),
        ]
    )


def rank_status_candidates(
    source_text: str,
    candidates: list[dict[str, Any]],
    *,
    current_meeting_id: str,
    limit: int = 30,
) -> list[dict[str, Any]]:
    """Rank recent open tasks using deterministic token overlap and recency."""
    source_tokens = _tokens(source_text)
    ranked: list[tuple[float, int, dict[str, Any]]] = []

    for index, candidate in enumerate(candidates):
        title = str(candidate.get("title") or "")
        assignee = str(candidate.get("assignee") or "")
        jira_key = str(candidate.get("jira_issue_key") or "")
        candidate_tokens = _tokens(_candidate_text(candidate))

        overlap = len(source_tokens & candidate_tokens)
        score = float(overlap)
        if title and title.lower() in source_text.lower():
            score += 8.0
        if assignee and assignee.lower() in source_text.lower():
            score += 2.0
        if jira_key and jira_key.lower() in source_text.lower():
            score += 6.0
        if str(candidate.get("meeting_id")) == current_meeting_id:
            score += 1.5

        ranked.append((score, -index, candidate))

    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)

    selected = [candidate for score, _, candidate in ranked if score > 0][:limit]
    if len(selected) < min(limit, len(candidates)):
        selected_ids = {str(item.get("id")) for item in selected}
        for _, _, candidate in ranked:
            if len(selected) >= limit:
                break
            candidate_id = str(candidate.get("id"))
            if candidate_id not in selected_ids:
                selected.append(candidate)
                selected_ids.add(candidate_id)
    return selected[:limit]


def format_status_candidates_for_prompt(candidates: list[dict[str, Any]]) -> str:
    if not candidates:
        return "[]"

    payload = []
    for item in candidates:
        payload.append({
            "id": item.get("id"),
            "title": item.get("title"),
            "description": item.get("description") or item.get("context"),
            "assignee": item.get("assignee"),
            "work_status": item.get("work_status") or WorkStatus.TODO.value,
            "sync_status": item.get("sync_status") or "pending",
            "jira_issue_key": item.get("jira_issue_key"),
        })
    return json.dumps(payload, ensure_ascii=False, indent=2)


def filter_status_updates(
    updates: list[StatusUpdate],
    candidates: list[dict[str, Any]],
    *,
    min_confidence: float = 0.5,
) -> list[StatusUpdate]:
    """Keep only proposals that point to an actual candidate row."""
    by_id = {str(item.get("id")): item for item in candidates if item.get("id")}
    valid: list[StatusUpdate] = []

    for update in updates:
        item_id = str(update.matched_action_item_id or "")
        candidate = by_id.get(item_id)
        if not candidate or update.confidence < min_confidence:
            continue
        update.matched_title = candidate.get("title") or update.matched_title
        try:
            update.old_status = WorkStatus(candidate.get("work_status") or WorkStatus.TODO.value)
        except ValueError:
            update.old_status = WorkStatus.TODO
        valid.append(update)
    return valid


def status_update_item_ids(updates: list[StatusUpdate]) -> set[str]:
    return {
        str(update.matched_action_item_id)
        for update in updates
        if update.matched_action_item_id
    }
