"""
CRUD cho Meeting, Transcript (segments), AnalysisResult via Supabase.

Dùng supabase-py client (SERVICE_ROLE_KEY). Tất cả hàm đồng bộ (sync).

Transcript storage sử dụng transcript_segments table (per-segment: speaker, start, end, content)
thay vì transcripts table (per-meeting: raw_text, diarized_text).
"""
import uuid
from typing import Any, Optional

from src.db import supabase_client as sc


def create_meeting(
    *,
    title: str,
    audio_storage_path: Optional[str] = None,
    user_id: str = "7f3572eb-aed9-4e7f-a4b1-41ecb03319e9",
) -> dict[str, Any]:
    """Tạo meeting mới với trạng thái pending."""
    return sc.insert(sc.TABLE_MEETINGS, {
        "title": title,
        "audio_storage_path": audio_storage_path,
        "user_id": user_id,
        "status": "pending",
    })


def get_meeting(meeting_id: str | uuid.UUID) -> Optional[dict[str, Any]]:
    """Lấy meeting theo ID."""
    return sc.fetch_one(sc.TABLE_MEETINGS, {"id": str(meeting_id)})


def list_meetings(
    *,
    user_id: str = "7f3572eb-aed9-4e7f-a4b1-41ecb03319e9",
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
    error_message: Optional[str] = None,
) -> dict[str, Any]:
    """Cập nhật status của meeting."""
    data: dict[str, Any] = {"status": status}
    if error_message is not None:
        data["error_message"] = error_message
    return sc.update_by_id(sc.TABLE_MEETINGS, str(meeting_id), data)


def delete_meeting(meeting_id: str | uuid.UUID) -> bool:
    """Xóa meeting (cascade tự động qua Supabase RLS/foreign keys)."""
    return sc.delete_by_id(sc.TABLE_MEETINGS, str(meeting_id))


# ── Transcript (segments) CRUD ──────────────────────────────────────────


def delete_transcript_segments_for_meeting(meeting_id: str | uuid.UUID) -> bool:
    """Xóa tất cả transcript segments của meeting."""
    client = sc.get_supabase_client()
    result = client.table(sc.TABLE_TRANSCRIPT_SEGMENTS).delete().eq(
        "meeting_id", str(meeting_id)
    ).execute()
    return bool(result.data)


def create_transcript_segments(
    meeting_id: str | uuid.UUID,
    segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Lưu transcript segments sau khi transcribe xong.

    Args:
        meeting_id: UUID của meeting.
        segments: Danh sách segment dicts từ WhisperLiveKit, mỗi dict có:
            speaker (str|None), start (float), end (float), text (str).

    Returns:
        Danh sách các segment đã lưu.
    """
    meeting_uuid = str(meeting_id)

    # Xóa segments cũ nếu có
    delete_transcript_segments_for_meeting(meeting_uuid)

    if not segments:
        return []

    # Insert all segments
    rows = [
        {
            "meeting_id": meeting_uuid,
            "speaker": seg.get("speaker"),
            "start_time": float(seg.get("start", 0)),
            "end_time": float(seg.get("end", 0)),
            "content": seg.get("text", ""),
        }
        for seg in segments
    ]

    client = sc.get_supabase_client()
    result = client.table(sc.TABLE_TRANSCRIPT_SEGMENTS).insert(rows).execute()
    return result.data or []


def get_transcript_segments(meeting_id: str | uuid.UUID) -> list[dict[str, Any]]:
    """
    Lấy tất cả transcript segments của meeting, sắp xếp theo start_time.
    """
    client = sc.get_supabase_client()
    result = (
        client.table(sc.TABLE_TRANSCRIPT_SEGMENTS)
        .select("*")
        .eq("meeting_id", str(meeting_id))
        .order("start_time", desc=False)
        .execute()
    )
    return result.data or []


def build_transcript_text(
    segments: list[dict[str, Any]],
    include_timing: bool = False,
) -> str:
    """
    Chuyển danh sách segments thành text.

    - Nếu có speaker: dùng định dạng [Speaker N]: text
    - Nếu không có speaker (plain Whisper): nối text thường
    - Nếu include_timing: thêm thời gian ở đầu dòng
    """
    if not segments:
        return ""

    lines: list[str] = []
    for seg in segments:
        speaker = seg.get("speaker")
        content = (seg.get("content") or "").strip()
        if not content:
            continue

        if speaker:
            prefix = f"[{speaker}]: "
        else:
            prefix = ""

        if include_timing:
            start = seg.get("start_time", 0)
            mins, secs = divmod(int(start), 60)
            prefix = f"[{mins:02d}:{secs:02d}] {prefix}"

        lines.append(f"{prefix}{content}")

    return "\n".join(lines)


def get_transcript_text(
    meeting_id: str | uuid.UUID,
    include_timing: bool = False,
) -> str:
    """Lấy transcript text của meeting (reassembled từ segments)."""
    segments = get_transcript_segments(meeting_id)
    return build_transcript_text(segments, include_timing=include_timing)


def get_analysis_result(meeting_id: str | uuid.UUID) -> Optional[dict[str, Any]]:
    """Lấy analysis result của meeting."""
    return sc.fetch_one(sc.TABLE_ANALYSIS_RESULTS, {"meeting_id": str(meeting_id)})


def create_analysis_result(
    *,
    meeting_id: str | uuid.UUID,
    analysis_json: dict[str, Any],
    summary: Optional[str] = None,
    overall_confidence: Optional[float] = None,
    validation_metrics: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Upsert analysis result cho meeting.

    Column mapping to Supabase analysis_results:
      - analysis_json     → raw_response
      - summary           → summary_text
      - key_decisions     → key_decisions
      - parking_lot       → parking_lot
    """
    meeting_uuid = str(meeting_id)
    existing = sc.fetch_one(sc.TABLE_ANALYSIS_RESULTS, {"meeting_id": meeting_uuid})
    data: dict[str, Any] = {
        "meeting_id": meeting_uuid,
        "raw_response": analysis_json,
        "summary_text": summary,
        "key_decisions": analysis_json.get("key_decisions"),
        "parking_lot": analysis_json.get("parking_lot"),
    }
    if existing:
        return sc.update_by_id(sc.TABLE_ANALYSIS_RESULTS, existing["id"], data)
    return sc.insert(sc.TABLE_ANALYSIS_RESULTS, data)
