from __future__ import annotations

import json
from typing import Callable, Optional

from dotenv import load_dotenv

from src.modules.database import (
    create_meeting as db_create_meeting,
    delete_provider_config as db_delete_provider_config,
    init_db as db_init_db,
    list_meetings as db_list_meetings,
    list_provider_configs as db_list_provider_configs,
    set_provider_config as db_set_provider_config,
)
from src.modules.exporter import export_csv, export_json, export_markdown
from src.schema import MeetingAnalysis, MeetingRecord
from src.services.analysis_service import analyze
from src.services.jira_service import JiraPushResult, push_analysis_to_jira
from src.services.recording_service import start_recording, stop_recording
from src.services.transcription_service import transcribe, transcribe_diarized
from src.services.summarization_service import generate_summary_stream


load_dotenv()


class LocalBackend:
    """
    Facade gọi trực tiếp logic hiện có trong repo (`src.*`).
    Mục tiêu: UI Flet không phụ thuộc Streamlit và dễ thay bằng HTTP client khi có FastAPI.
    """

    def __init__(self) -> None:
        pass

    # ---- DB ----
    def init_db(self) -> None:
        db_init_db()

    def list_meetings(self) -> list[MeetingRecord]:
        return db_list_meetings()

    def create_meeting(
        self,
        *,
        title: str,
        transcript: str,
        audio_path: Optional[str],
        analysis: Optional[MeetingAnalysis],
    ) -> int:
        rec = MeetingRecord(title=title, transcript=transcript, audio_path=audio_path, analysis=analysis)
        return db_create_meeting(rec)

    # ---- Provider configs ----
    def list_provider_configs(self) -> list[str]:
        return db_list_provider_configs()

    def set_provider_config(self, provider_name: str, config_dict: dict) -> None:
        db_set_provider_config(provider_name, config_dict)

    def delete_provider_config(self, provider_name: str) -> None:
        db_delete_provider_config(provider_name)

    # ---- Recording ----
    def start_recording(self) -> str:
        return start_recording()

    def stop_recording(self) -> str:
        return stop_recording()

    # ---- Transcription ----
    def transcribe(self, audio_path: str, *, diarize: bool) -> str:
        if diarize:
            return transcribe_diarized(audio_path)
        return transcribe(audio_path)

    # ---- Summary streaming ----
    def generate_summary_stream(self, transcript: str, *, on_token: Callable[[str], None]) -> str:
        """
        Wrap async generator -> callback, để view gọi từ thread.
        """

        async def _run() -> str:
            acc = ""
            async for token in generate_summary_stream(transcript):
                acc += token
                on_token(token)
            return acc

        return _ensure_async(_run)

    # ---- Analysis ----
    def analyze(self, transcript: str) -> MeetingAnalysis:
        return analyze(transcript)

    # ---- Exporters ----
    def export_markdown(self, analysis: MeetingAnalysis) -> str:
        return export_markdown(analysis)

    def export_json(self, analysis: MeetingAnalysis) -> str:
        return export_json(analysis)

    def export_csv(self, analysis: MeetingAnalysis) -> str:
        return export_csv(analysis)

    # ---- Jira ----
    def push_to_jira(self, analysis: MeetingAnalysis) -> JiraPushResult:
        return push_analysis_to_jira(analysis)

    # ---- Helpers ----
    def parse_json_or_empty(self, raw: str) -> dict:
        s = (raw or "").strip()
        if not s:
            return {}
        try:
            val = json.loads(s)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSON không hợp lệ: {exc}") from exc
        if not isinstance(val, dict):
            raise ValueError("Config JSON phải là object/dict.")
        return val

    def save_text_via_dialog(self, *, filename: str, content: str) -> Optional[str]:
        """
        Dùng Tkinter Save As dialog để tránh lỗi 'Unknown control: FilePicker' trên Flet desktop client.
        Trả về path nếu user chọn, None nếu hủy.
        """
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"Không import được tkinter: {exc}") from exc

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.asksaveasfilename(
            defaultextension="",
            initialfile=filename,
            filetypes=[("All files", "*.*")],
        )
        root.destroy()
        if not path:
            return None
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path


def _ensure_async(coro_fn):
    """
    Chạy coroutine trong context sync (thread) an toàn.
    """
    try:
        loop = None
        try:
            loop = __import__("asyncio").get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            fut = __import__("asyncio").run_coroutine_threadsafe(coro_fn(), loop)
            return fut.result()
        return __import__("asyncio").run(coro_fn())
    except Exception:
        # Để caller xử lý message
        raise

