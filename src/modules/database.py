"""
SQLite CRUD cho MeetingRecord + provider_configs.
Dùng sqlite3 stdlib — không cần ORM bên ngoài.
"""
import json
import sqlite3
from datetime import datetime
from typing import Any, Optional

from src.config import DATABASE_URL, get_logger
from src.schema import MeetingAnalysis, MeetingRecord

logger = get_logger(__name__)


def _db_path() -> str:
    """Trả về đường dẫn file SQLite từ DATABASE_URL."""
    url = DATABASE_URL
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///"):]
    return url


def _get_conn(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or _db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate_schema(conn: sqlite3.Connection) -> None:
    """Idempotent schema migration — an toàn chạy nhiều lần."""
    for col, default in [
        ("status", "'processed'"),
        ("key_decisions", "'[]'"),
        ("parking_lot", "'[]'"),
    ]:
        try:
            conn.execute(f"ALTER TABLE meetings ADD COLUMN {col} TEXT DEFAULT {default}")
        except sqlite3.OperationalError:
            pass  # column đã tồn tại

    conn.execute("""
        CREATE TABLE IF NOT EXISTS provider_configs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      TEXT NOT NULL DEFAULT 'default_user',
            provider_name TEXT NOT NULL,
            config_json  TEXT NOT NULL,
            active       INTEGER DEFAULT 1,
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL,
            UNIQUE(user_id, provider_name)
        )
    """)
    conn.commit()


def init_db(db_path: Optional[str] = None) -> None:
    """Tạo bảng meetings + provider_configs nếu chưa tồn tại. Chạy migration."""
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
        _migrate_schema(conn)
    logger.info("Database initialized: %s", db_path or _db_path())


# ── Meeting CRUD ─────────────────────────────────────────────────────────────

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


# ── Provider Configs CRUD ─────────────────────────────────────────────────────

def get_provider_config(
    provider_name: str,
    user_id: str = "default_user",
    db_path: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """Lấy config dict (đã decrypt) cho provider. Trả về None nếu chưa có."""
    from src.modules.credential_vault import decrypt

    with _get_conn(db_path) as conn:
        row = conn.execute(
            "SELECT config_json FROM provider_configs WHERE user_id=? AND provider_name=? AND active=1",
            (user_id, provider_name),
        ).fetchone()
    if row is None:
        return None
    try:
        decrypted = decrypt(row["config_json"])
        return json.loads(decrypted)
    except Exception as exc:
        logger.warning("Không decrypt được config cho provider '%s': %s", provider_name, exc)
        return None


def set_provider_config(
    provider_name: str,
    config_dict: dict[str, Any],
    user_id: str = "default_user",
    db_path: Optional[str] = None,
) -> None:
    """Lưu (upsert) config dict đã encrypt cho provider."""
    from src.modules.credential_vault import encrypt

    now = datetime.utcnow().isoformat()
    encrypted = encrypt(json.dumps(config_dict))
    with _get_conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO provider_configs (user_id, provider_name, config_json, active, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?)
            ON CONFLICT(user_id, provider_name) DO UPDATE SET
                config_json=excluded.config_json,
                active=1,
                updated_at=excluded.updated_at
            """,
            (user_id, provider_name, encrypted, now, now),
        )
        conn.commit()
    logger.info("Đã lưu config cho provider '%s'.", provider_name)


def list_provider_configs(
    user_id: str = "default_user",
    db_path: Optional[str] = None,
) -> list[str]:
    """Trả về danh sách provider_name đang active."""
    with _get_conn(db_path) as conn:
        rows = conn.execute(
            "SELECT provider_name FROM provider_configs WHERE user_id=? AND active=1",
            (user_id,),
        ).fetchall()
    return [r["provider_name"] for r in rows]


def delete_provider_config(
    provider_name: str,
    user_id: str = "default_user",
    db_path: Optional[str] = None,
) -> None:
    """Xóa config cho provider."""
    with _get_conn(db_path) as conn:
        conn.execute(
            "DELETE FROM provider_configs WHERE user_id=? AND provider_name=?",
            (user_id, provider_name),
        )
        conn.commit()
    logger.info("Đã xóa config cho provider '%s'.", provider_name)
