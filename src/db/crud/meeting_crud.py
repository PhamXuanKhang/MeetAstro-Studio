"""
CRUD cho Meeting, Transcript, AnalysisResult via Supabase.

Dùng supabase-py client (SERVICE_ROLE_KEY). Tất cả hàm đồng bộ (sync).
"""
import uuid
from typing import Any, Optional

from src.db import supabase_client as sc


def create_meeting(
    *,
    title: str,
    audio_path: Optional[str] = None,
    user_id: str = "00000000-0000-0000-0000-000000000000",
) -> dict[str, Any]:
    """Tạo meeting mới với trạng thái pending."""
    return sc.insert(sc.TABLE_MEETINGS, {
        "title": title,
        "audio_path": audio_path,
        "user_id": user_id,
        "status": "pending",
    })


def get_meeting(meeting_id: str | uuid.UUID) -> Optional[dict[str, Any]]:
    """Lấy meeting theo ID."""
    return sc.fetch_one(sc.TABLE_MEETINGS, {"id": str(meeting_id)})


def list_meetings(
    *,
    user_id: str = "00000000-0000-0000-0000-000000000000",
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    """Lấy danh sách meetings, trả về (items, total)."""
    client = sc.get_supabase_client()
    filters: dict[str, Any] = {"user_id": user_id}
    if status:
        filters["status"] = status

    query = client.table(sc.TABLE_MEETINGS).select("*", count="exact")
    for col, val in filters.items():
        query = query.eq(col, val)
    query = query.order("created_at", ascending=False)
    query = query.range((page - 1) * page_size, page * page_size - 1)
    result = query.execute()

    count_result = client.table(sc.TABLE_MEETINGS).select("id", count="exact")
    for col, val in filters.items():
        count_result = count_result.eq(col, val)
    total = count_result.execute().count or 0

    return result.data or [], total


def update_meeting(
    meeting_id: str | uuid.UUID,
    **kwargs: Any,
) -> dict[str, Any]:
    """Cập nhật meeting fields."""
    return sc.update_by_id(sc.TABLE_MEETINGS, str(meeting_id), kwargs)


def update_meeting_status(
    meeting_id: str | uuid.UUID,
    *,
    status: str,
    celery_task_id: Optional[str] = None,
    error_message: Optional[str] = None,
) -> dict[str, Any]:
    """Cập nhật status và celery_task_id."""
    data: dict[str, Any] = {"status": status}
    if celery_task_id is not None:
        data["celery_task_id"] = celery_task_id
    if error_message is not None:
        data["error_message"] = error_message
    return sc.update_by_id(sc.TABLE_MEETINGS, str(meeting_id), data)


def delete_meeting(meeting_id: str | uuid.UUID) -> bool:
    """Xóa meeting (cascade tự động qua Supabase RLS/foreign keys)."""
    return sc.delete_by_id(sc.TABLE_MEETINGS, str(meeting_id))


def delete_transcript_for_meeting(meeting_id: str | uuid.UUID) -> bool:
    """Xóa transcript cũ của meeting (nếu có)."""
    client = sc.get_supabase_client()
    existing = get_transcript(meeting_id)
    if not existing:
        return False
    client.table(sc.TABLE_TRANSCRIPTS).delete().eq("id", existing["id"]).execute()
    return True


def create_transcript(
    *,
    meeting_id: str | uuid.UUID,
    raw_text: str,
    diarized_text: Optional[str] = None,
    language: str = "en",
) -> dict[str, Any]:
    """Lưu transcript sau khi transcribe xong."""
    meeting_uuid = str(meeting_id)
    existing = sc.fetch_one(sc.TABLE_TRANSCRIPTS, {"meeting_id": meeting_uuid})
    if existing:
        sc.update_by_id(sc.TABLE_TRANSCRIPTS, existing["id"], {
            "raw_text": raw_text,
            "diarized_text": diarized_text,
            "language": language,
            "char_count": len(raw_text),
        })
        return {**existing, "raw_text": raw_text, "diarized_text": diarized_text,
                "language": language, "char_count": len(raw_text)}

    return sc.insert(sc.TABLE_TRANSCRIPTS, {
        "meeting_id": meeting_uuid,
        "raw_text": raw_text,
        "diarized_text": diarized_text,
        "language": language,
        "char_count": len(raw_text),
    })


def get_transcript(meeting_id: str | uuid.UUID) -> Optional[dict[str, Any]]:
    """Lấy transcript của meeting."""
    return sc.fetch_one(sc.TABLE_TRANSCRIPTS, {"meeting_id": str(meeting_id)})


def create_analysis_result(
    *,
    meeting_id: str | uuid.UUID,
    analysis_json: dict[str, Any],
    summary: Optional[str] = None,
    overall_confidence: Optional[float] = None,
    validation_metrics: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Upsert analysis result cho meeting."""
    meeting_uuid = str(meeting_id)
    existing = sc.fetch_one(sc.TABLE_ANALYSIS_RESULTS, {"meeting_id": meeting_uuid})
    data: dict[str, Any] = {
        "meeting_id": meeting_uuid,
        "analysis_json": analysis_json,
        "summary": summary,
        "overall_confidence": overall_confidence,
        "validation_metrics": validation_metrics,
    }
    if existing:
        return sc.update_by_id(sc.TABLE_ANALYSIS_RESULTS, existing["id"], data)
    return sc.insert(sc.TABLE_ANALYSIS_RESULTS, data)


def get_analysis_result(meeting_id: str | uuid.UUID) -> Optional[dict[str, Any]]:
    """Lấy analysis result của meeting."""
    return sc.fetch_one(sc.TABLE_ANALYSIS_RESULTS, {"meeting_id": str(meeting_id)})


def update_transcript(
    meeting_id: str | uuid.UUID,
    raw_text: Optional[str] = None,
    diarized_text: Optional[str] = None,
    language: Optional[str] = None,
) -> dict[str, Any]:
    """Cập nhật transcript fields."""
    data: dict[str, Any] = {}
    if raw_text is not None:
        data["raw_text"] = raw_text
        data["char_count"] = len(raw_text)
    if diarized_text is not None:
        data["diarized_text"] = diarized_text
    if language is not None:
        data["language"] = language
    if not data:
        return get_transcript(meeting_id) or {}
    client = sc.get_supabase_client()
    existing = get_transcript(meeting_id)
    if not existing:
        raise RuntimeError(f"Transcript for meeting {meeting_id} not found.")
    result = client.table(sc.TABLE_TRANSCRIPTS).update(data).eq(
        "id", existing["id"]
    ).execute()
    if result.data:
        return result.data[0]
    raise RuntimeError(f"Update transcript {existing['id']} failed.")
