"""
SQLite CRUD cho MeetingRecord.
Dùng sqlite3 stdlib — không cần ORM bên ngoài.
"""
import json
import sqlite3
from datetime import datetime
from typing import Optional

from src.config import DATABASE_URL, get_logger
from src.schema import MeetingAnalysis, MeetingRecord

logger = get_logger(__name__)


def _db_path() -> str:
    """Trả về đường dẫn file SQLite từ DATABASE_URL."""
    # SQLite URL: sqlite:///relative/path  hoặc sqlite:////absolute/path
    url = DATABASE_URL
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///"):]
    return url


def _get_conn(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or _db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Tạo bảng meetings nếu chưa tồn tại."""
    with _get_conn(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS meetings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT    NOT NULL,
                audio_path  TEXT,
                transcript  TEXT    NOT NULL DEFAULT '',
                analysis    TEXT,
                created_at  TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL
            )
        """)
        conn.commit()
    logger.info("Database initialized: %s", db_path or _db_path())


def create_meeting(record: MeetingRecord, db_path: Optional[str] = None) -> int:
    """Thêm MeetingRecord mới vào DB. Trả về id được tạo."""
    now = datetime.utcnow().isoformat()
    analysis_json = record.analysis.to_json() if record.analysis else None
    with _get_conn(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO meetings (title, audio_path, transcript, analysis, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (record.title, record.audio_path, record.transcript, analysis_json, now, now),
        )
        conn.commit()
        new_id = cur.lastrowid
    logger.info("Đã tạo meeting id=%d: '%s'.", new_id, record.title)
    return new_id


def get_meeting(meeting_id: int, db_path: Optional[str] = None) -> Optional[MeetingRecord]:
    """Lấy MeetingRecord theo id. Trả về None nếu không tìm thấy."""
    with _get_conn(db_path) as conn:
        row = conn.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)).fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def list_meetings(db_path: Optional[str] = None) -> list[MeetingRecord]:
    """Liệt kê tất cả MeetingRecord, mới nhất trước."""
    with _get_conn(db_path) as conn:
        rows = conn.execute("SELECT * FROM meetings ORDER BY created_at DESC").fetchall()
    return [_row_to_record(r) for r in rows]


def update_meeting(record: MeetingRecord, db_path: Optional[str] = None) -> None:
    """Cập nhật MeetingRecord (cần record.id)."""
    if record.id is None:
        raise ValueError("record.id không được None khi update.")
    now = datetime.utcnow().isoformat()
    analysis_json = record.analysis.to_json() if record.analysis else None
    with _get_conn(db_path) as conn:
        conn.execute(
            """
            UPDATE meetings
            SET title=?, audio_path=?, transcript=?, analysis=?, updated_at=?
            WHERE id=?
            """,
            (record.title, record.audio_path, record.transcript, analysis_json, now, record.id),
        )
        conn.commit()
    logger.info("Đã cập nhật meeting id=%d.", record.id)


def delete_meeting(meeting_id: int, db_path: Optional[str] = None) -> None:
    """Xóa MeetingRecord theo id."""
    with _get_conn(db_path) as conn:
        conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
        conn.commit()
    logger.info("Đã xóa meeting id=%d.", meeting_id)


def _row_to_record(row: sqlite3.Row) -> MeetingRecord:
    analysis = None
    if row["analysis"]:
        try:
            analysis = MeetingAnalysis.from_json(row["analysis"])
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Không parse được analysis JSON cho id=%s: %s", row["id"], exc)
    return MeetingRecord(
        id=row["id"],
        title=row["title"],
        audio_path=row["audio_path"],
        transcript=row["transcript"],
        analysis=analysis,
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )
