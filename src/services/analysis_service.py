"""
Analysis service — orchestrate parallel summary + AI extraction + validation.
"""
from __future__ import annotations

import asyncio
from typing import Any

from src.config import OPENAI_API_KEY, get_logger
from src.providers.mock_analyzer import MockAnalyzer
from src.providers.openai_analyzer import OpenAIAnalyzer
from src.schema import Epic, MeetingAnalysis, Priority, Subtask, Task
from src.services.extraction_service import rule_based_extraction
from src.services.summarization_service import generate_summary
from src.services.validation_service import validate_action_items

logger = get_logger(__name__)

_PRIORITY_MAP = {
    "critical": Priority.CRITICAL,
    "high": Priority.HIGH,
    "medium": Priority.MEDIUM,
    "low": Priority.LOW,
}


def _extract_via_openai(transcript: str) -> list[dict[str, Any]]:
    """Gọi OpenAIAnalyzer sync, trả về list dict của tasks từ tất cả epics."""
    analyzer = OpenAIAnalyzer()
    analysis = analyzer.analyze(transcript)
    items = []
    for epic in analysis.epics:
        for task in epic.tasks:
            items.append({
                "title": task.summary,
                "description": task.context,
                "assignee": task.assignee or "Unassigned",
                "deadline": task.deadline or "",
                "priority": task.priority.value.lower() if hasattr(task.priority, "value") else str(task.priority).lower(),
                "context": task.context,
                "_epic_summary": epic.summary,
                "_epic_description": epic.description,
                "_subtasks": [
                    {
                        "title": s.summary,
                        "description": s.context,
                        "assignee": s.assignee or "Unassigned",
                        "deadline": s.deadline or "",
                        "priority": s.priority.value.lower() if hasattr(s.priority, "value") else str(s.priority).lower(),
                        "context": s.context,
                    }
                    for s in task.subtasks
                ],
            })
    return items


def _build_analysis(
    validated_items: list[dict[str, Any]],
    summary_result: dict[str, Any],
) -> MeetingAnalysis:
    """Tái tạo MeetingAnalysis từ validated items + summary result."""
    epics_map: dict[str, Epic] = {}

    for item in validated_items:
        epic_summary = item.get("_epic_summary", "General")
        epic_desc = item.get("_epic_description", "")
        if epic_summary not in epics_map:
            epics_map[epic_summary] = Epic(summary=epic_summary, description=epic_desc)

        priority_str = item.get("priority", "medium").lower()
        priority = _PRIORITY_MAP.get(priority_str, Priority.MEDIUM)

        subtasks = []
        for sub in item.get("_subtasks", []):
            sub_priority = _PRIORITY_MAP.get(sub.get("priority", "medium").lower(), Priority.MEDIUM)
            subtasks.append(Subtask(
                summary=sub.get("title", ""),
                assignee=sub.get("assignee") or None,
                deadline=sub.get("deadline") or None,
                priority=sub_priority,
                context=sub.get("context", ""),
                confidence=item.get("confidence", 0.0),
                validation_notes=item.get("validation_notes", []),
            ))

        task = Task(
            summary=item.get("title", ""),
            assignee=item.get("assignee") or None,
            deadline=item.get("deadline") or None,
            priority=priority,
            context=item.get("context", ""),
            subtasks=subtasks,
            confidence=item.get("confidence", 0.0),
            validation_notes=item.get("validation_notes", []),
        )
        epics_map[epic_summary].tasks.append(task)

    return MeetingAnalysis(
        epics=list(epics_map.values()),
        summary=summary_result.get("summary", ""),
        key_decisions=summary_result.get("key_decisions", []),
        discussion_points=summary_result.get("discussion_points", []),
        parking_lot=summary_result.get("parking_lot_items", []),
    )


async def analyze_async(transcript: str) -> MeetingAnalysis:
    """Async core: run summary + AI extraction in parallel, validate, build result.

    Raises ValueError for empty transcript.
    Falls back to MockAnalyzer when OPENAI_API_KEY is empty.
    """
    if not transcript.strip():
        raise ValueError("Transcript cannot be empty.")

    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY empty — using MockAnalyzer.")
        return MockAnalyzer().analyze(transcript)

    loop = asyncio.get_event_loop()

    summary_coro = generate_summary(transcript)
    ai_extract_future = loop.run_in_executor(None, _extract_via_openai, transcript)

    summary_result, ai_items = await asyncio.gather(summary_coro, ai_extract_future)

    rule_items = rule_based_extraction(transcript)
    validated, metrics = validate_action_items(ai_items, rule_items, transcript)

    logger.info(
        "Validation metrics: overall=%.3f cross=%.3f context=%.3f structural=%.3f",
        metrics["overall_confidence"],
        metrics["cross_validation_score"],
        metrics["context_coherence_score"],
        metrics["structural_validation_score"],
    )

    analysis = _build_analysis(validated, summary_result)
    logger.info(
        "Phân tích xong: %d epics, %d tasks.",
        len(analysis.epics),
        sum(len(e.tasks) for e in analysis.epics),
    )
    return analysis


def analyze(transcript: str) -> MeetingAnalysis:
    """Sync wrapper for UI / scripts that run outside an event loop.

    Use analyze_async() when already inside an event loop (e.g. Celery async tasks).
    Falls back to MockAnalyzer when OPENAI_API_KEY is empty.
    """
    if not transcript.strip():
        raise ValueError("Transcript cannot be empty.")

    if not OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY empty — using MockAnalyzer.")
        return MockAnalyzer().analyze(transcript)

    return asyncio.run(analyze_async(transcript))
