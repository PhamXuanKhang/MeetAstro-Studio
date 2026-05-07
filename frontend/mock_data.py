from __future__ import annotations

from copy import deepcopy
from typing import Any


MEETING_DETAIL: dict[str, Any] = {
    "meeting": {
        "id": "11111111-1111-4111-8111-111111111111",
        "user_id": "22222222-2222-4222-8222-222222222222",
        "title": "Sprint Planning - Phase 1.1",
        "status": "draft",
        "storage_provider": "local",
        "audio_storage_path": "file:///Users/name/Documents/MeetSync/records/sprint.wav",
        "audio_duration_seconds": 1830,
        "error_message": None,
        "created_at": "2026-05-05T10:00:00Z",
        "updated_at": "2026-05-05T10:30:00Z",
    },
    "analysis_result": {
        "id": "33333333-3333-4333-8333-333333333333",
        "meeting_id": "11111111-1111-4111-8111-111111111111",
        "summary_text": (
            "Team chot scope Phase 1.1: migrate database sang Supabase, "
            "giu local audio path, va tach UI direct Supabase voi FastAPI trigger."
        ),
        "key_decisions": [
            "UI render action_items tu flat list bang parent_id.",
            "Provider keys di qua FastAPI de Fernet encrypt.",
            "Live recording va chunking de Future/Research.",
        ],
        "parking_lot": [
            "Chot co can bang durable cho recording sessions khong.",
            "Chot WebSocket hay Supabase Realtime cho transcript streaming.",
        ],
        "raw_response": {
            "provider": "openai",
            "model": "gpt-4o",
            "content": {"mock": True},
        },
        "ai_model": "gpt-4o",
        "input_tokens": 1248,
        "output_tokens": 702,
        "created_at": "2026-05-05T10:28:00Z",
    },
    "transcript_segments": [
        {
            "id": "44444444-4444-4444-8444-444444444401",
            "meeting_id": "11111111-1111-4111-8111-111111111111",
            "speaker": "Duy",
            "start_time": 0.0,
            "end_time": 8.4,
            "content": "Phase nay minh uu tien chuyen database sang Supabase truoc.",
        },
        {
            "id": "44444444-4444-4444-8444-444444444402",
            "meeting_id": "11111111-1111-4111-8111-111111111111",
            "speaker": "Khang",
            "start_time": 8.5,
            "end_time": 18.0,
            "content": "UI se dung flat action_items va tu build tree o client.",
        },
        {
            "id": "44444444-4444-4444-8444-444444444403",
            "meeting_id": "11111111-1111-4111-8111-111111111111",
            "speaker": "Thuc",
            "start_time": 18.1,
            "end_time": 29.0,
            "content": (
                "AI pipeline chi can tra output cuoi theo transcript_segments "
                "va action_items."
            ),
        },
    ],
    "action_items": [
        {
            "id": "55555555-5555-4555-8555-555555555501",
            "meeting_id": "11111111-1111-4111-8111-111111111111",
            "parent_id": None,
            "item_type": "epic",
            "title": "Supabase migration foundation",
            "description": "Hoan tat nen tang database va contract Phase 1.1.",
            "assignee": "Duy",
            "deadline": "2026-05-10",
            "priority": "high",
            "context": "uu tien chuyen database sang Supabase truoc",
            "confidence_score": 0.94,
            "review_status": "approved",
            "is_selected": True,
            "sync_status": "pending",
            "sync_error": None,
            "jira_issue_key": None,
            "jira_issue_url": None,
            "created_at": "2026-05-05T10:29:00Z",
            "updated_at": "2026-05-05T10:29:00Z",
        },
        {
            "id": "55555555-5555-4555-8555-555555555502",
            "meeting_id": "11111111-1111-4111-8111-111111111111",
            "parent_id": "55555555-5555-4555-8555-555555555501",
            "item_type": "task",
            "title": "Write hybrid contract v1",
            "description": "Define routing for Supabase SDK vs FastAPI triggers.",
            "assignee": "Duy",
            "deadline": "2026-05-07",
            "priority": "high",
            "context": "tach UI direct Supabase voi FastAPI trigger",
            "confidence_score": 0.9,
            "review_status": "approved",
            "is_selected": True,
            "sync_status": "pending",
            "sync_error": None,
            "jira_issue_key": None,
            "jira_issue_url": None,
            "created_at": "2026-05-05T10:29:10Z",
            "updated_at": "2026-05-05T10:29:10Z",
        },
        {
            "id": "55555555-5555-4555-8555-555555555503",
            "meeting_id": "11111111-1111-4111-8111-111111111111",
            "parent_id": "55555555-5555-4555-8555-555555555502",
            "item_type": "subtask",
            "title": "Remove live/chunking from required scope",
            "description": "Keep research topics out of Phase 1.1 contract.",
            "assignee": "Duy",
            "deadline": "2026-05-07",
            "priority": "medium",
            "context": "Live recording va chunking de Future/Research",
            "confidence_score": 0.88,
            "review_status": "edited",
            "is_selected": False,
            "sync_status": "pending",
            "sync_error": None,
            "jira_issue_key": None,
            "jira_issue_url": None,
            "created_at": "2026-05-05T10:29:20Z",
            "updated_at": "2026-05-05T10:29:20Z",
        },
        {
            "id": "55555555-5555-4555-8555-555555555504",
            "meeting_id": "11111111-1111-4111-8111-111111111111",
            "parent_id": None,
            "item_type": "epic",
            "title": "Frontend UI refactor",
            "description": "Update Flet screens to new contract terminology.",
            "assignee": "Khang",
            "deadline": "2026-05-11",
            "priority": "high",
            "context": "UI se dung flat action_items",
            "confidence_score": 0.86,
            "review_status": "draft",
            "is_selected": False,
            "sync_status": "pending",
            "sync_error": None,
            "jira_issue_key": None,
            "jira_issue_url": None,
            "created_at": "2026-05-05T10:29:30Z",
            "updated_at": "2026-05-05T10:29:30Z",
        },
        {
            "id": "55555555-5555-4555-8555-555555555505",
            "meeting_id": "11111111-1111-4111-8111-111111111111",
            "parent_id": "55555555-5555-4555-8555-555555555504",
            "item_type": "task",
            "title": "Render Action Items tree",
            "description": "Build Epic -> Task -> Subtask tree from parent_id.",
            "assignee": "Khang",
            "deadline": "2026-05-09",
            "priority": "high",
            "context": "tu build tree o client",
            "confidence_score": 0.91,
            "review_status": "draft",
            "is_selected": False,
            "sync_status": "pending",
            "sync_error": None,
            "jira_issue_key": None,
            "jira_issue_url": None,
            "created_at": "2026-05-05T10:29:40Z",
            "updated_at": "2026-05-05T10:29:40Z",
        },
    ],
}


def get_mock_meeting_detail() -> dict[str, Any]:
    return deepcopy(MEETING_DETAIL)


def get_mock_meetings() -> list[dict[str, Any]]:
    detail = get_mock_meeting_detail()
    return [
        detail["meeting"],
        {
            **detail["meeting"],
            "id": "11111111-1111-4111-8111-111111111112",
            "title": "Design Review - Action Item Tree",
            "status": "transcribed",
            "audio_duration_seconds": 1420,
            "created_at": "2026-05-04T14:00:00Z",
            "updated_at": "2026-05-04T14:25:00Z",
        },
    ]
