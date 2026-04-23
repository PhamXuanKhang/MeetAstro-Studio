"""
HttpBackend: call FastAPI over HTTP only.

This client is the single backend for the Flet app.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

import httpx

from src.config import DEFAULT_TRANSCRIPTION_LANGUAGE
from src.schema import MeetingAnalysis, MeetingRecord, ReviewItem


class HttpBackend:
    """
    Gọi FastAPI server qua HTTP.
    Sử dụng httpx.Client (sync) vì Flet views chạy trong thread.
    """

    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self._base = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self._base, timeout=60)

    def _url(self, path: str) -> str:
        return f"/api/v1{path}"

    # ── DB lifecycle ──────────────────────────────────────────────────────────
    def init_db(self) -> None:
        """No-op: server manages DB."""
        return None

    # ── Meetings ──────────────────────────────────────────────────────────────
    def list_meetings(self) -> list[MeetingRecord]:
        resp = self._client.get(self._url("/meetings"))
        resp.raise_for_status()
        return [_parse_meeting(m) for m in resp.json()["items"]]

    def create_meeting(
        self,
        *,
        title: str,
        transcript: str,
        audio_path: Optional[str],
        analysis: Optional[MeetingAnalysis],
        user_id: str = "default_user",
    ) -> str:
        """Create a meeting and return meeting_id (UUID string)."""
        resp = self._client.post(
            self._url("/meetings"),
            json={"title": title, "user_id": user_id},
        )
        resp.raise_for_status()
        return str(resp.json()["id"])

    # ── Provider configs ──────────────────────────────────────────────────────
    def list_provider_configs(self) -> list[str]:
        resp = self._client.get(self._url("/settings/providers"))
        resp.raise_for_status()
        return resp.json()["providers"]

    def set_provider_config(self, provider_name: str, config_dict: dict) -> None:
        resp = self._client.post(
            self._url(f"/settings/providers/{provider_name}"),
            json={"config": config_dict},
        )
        resp.raise_for_status()

    def delete_provider_config(self, provider_name: str) -> None:
        resp = self._client.delete(self._url(f"/settings/providers/{provider_name}"))
        resp.raise_for_status()

    # ── Recording ─────────────────────────────────────────────────────────────
    def start_recording(self) -> str:
        """Recording runs locally via recording_service."""
        from src.services.recording_service import start_recording
        return start_recording()

    def stop_recording(self) -> str:
        from src.services.recording_service import stop_recording
        return stop_recording()

    # ── Transcription ─────────────────────────────────────────────────────────
    def transcribe(
        self,
        audio_path: str,
        *,
        diarize: bool,
        meeting_id: Optional[str] = None,
    ) -> str:
        """Upload audio -> queue pipeline -> poll until transcript is ready."""
        if not meeting_id:
            raise ValueError("HttpBackend.transcribe requires meeting_id.")

        with open(audio_path, "rb") as f:
            resp = self._client.post(
                self._url(f"/meetings/{meeting_id}/audio"),
                files={"file": (Path(audio_path).name, f, "audio/wav")},
                data={"diarize": str(diarize).lower(), "language": DEFAULT_TRANSCRIPTION_LANGUAGE},
                timeout=30,
            )
        resp.raise_for_status()
        job_id = resp.json()["job_id"]

        # Poll pipeline (transcribe + analyze) đến khi done
        self._poll_job(job_id, timeout=300)

        # Lấy transcript text
        resp2 = self._client.get(self._url(f"/meetings/{meeting_id}/transcript"))
        resp2.raise_for_status()
        return resp2.json()["raw_text"]

    def update_transcript(self, meeting_id: str, raw_text: str) -> str:
        """Update transcript text before analysis."""
        resp = self._client.patch(
            self._url(f"/meetings/{meeting_id}/transcript"),
            json={"raw_text": raw_text},
        )
        resp.raise_for_status()
        return resp.json()["raw_text"]

    # ── Summary streaming ─────────────────────────────────────────────────────
    def generate_summary_stream(
        self, transcript: str, *, on_token: Callable[[str], None]
    ) -> str:
        """Streaming summary is not supported in HTTP-only mode."""
        raise RuntimeError("Summary streaming is not available in HTTP-only mode.")

    # ── Analysis ──────────────────────────────────────────────────────────────
    def analyze(
        self, transcript: str, *, meeting_id: Optional[str] = None
    ) -> MeetingAnalysis:
        """Call /analyze, poll until done, then fetch analysis JSON."""
        if not meeting_id:
            raise ValueError("HttpBackend.analyze requires meeting_id.")

        resp = self._client.post(self._url(f"/meetings/{meeting_id}/analyze"))
        resp.raise_for_status()
        job_id = resp.json()["job_id"]
        self._poll_job(job_id, timeout=180)

        resp2 = self._client.get(self._url(f"/meetings/{meeting_id}/analysis"))
        resp2.raise_for_status()
        return MeetingAnalysis.from_dict(resp2.json()["analysis_json"])

    # ── Review items ──────────────────────────────────────────────────────────
    def list_review_items(self, meeting_id: str) -> list[ReviewItem]:
        resp = self._client.get(self._url(f"/meetings/{meeting_id}/review"))
        resp.raise_for_status()
        return [ReviewItem.from_dict(i) for i in resp.json()]

    def patch_review_item(self, meeting_id: str, item_id: str, **updates) -> ReviewItem:
        resp = self._client.patch(
            self._url(f"/meetings/{meeting_id}/review/{item_id}"),
            json=updates,
        )
        resp.raise_for_status()
        return ReviewItem.from_dict(resp.json())

    def approve_review_item(self, meeting_id: str, item_id: str) -> ReviewItem:
        resp = self._client.post(
            self._url(f"/meetings/{meeting_id}/review/{item_id}/approve")
        )
        resp.raise_for_status()
        return ReviewItem.from_dict(resp.json())

    def reject_review_item(self, meeting_id: str, item_id: str) -> ReviewItem:
        resp = self._client.post(
            self._url(f"/meetings/{meeting_id}/review/{item_id}/reject")
        )
        resp.raise_for_status()
        return ReviewItem.from_dict(resp.json())

    def approve_all_review_items(self, meeting_id: str) -> int:
        resp = self._client.post(
            self._url(f"/meetings/{meeting_id}/review/approve_all")
        )
        resp.raise_for_status()
        return resp.json()["approved_count"]

    def get_review_summary(self, meeting_id: str) -> dict:
        resp = self._client.get(self._url(f"/meetings/{meeting_id}/review/summary"))
        resp.raise_for_status()
        return resp.json()

    # ── Exporters ─────────────────────────────────────────────────────────────
    def export_markdown(self, analysis: MeetingAnalysis, meeting_id: Optional[str] = None) -> str:
        if not meeting_id:
            raise ValueError("export_markdown requires meeting_id in HTTP-only mode.")
        resp = self._client.get(self._url(f"/meetings/{meeting_id}/export/markdown"))
        resp.raise_for_status()
        return resp.text

    def export_json(self, analysis: MeetingAnalysis, meeting_id: Optional[str] = None) -> str:
        if not meeting_id:
            raise ValueError("export_json requires meeting_id in HTTP-only mode.")
        resp = self._client.get(self._url(f"/meetings/{meeting_id}/export/json"))
        resp.raise_for_status()
        return resp.text

    def export_csv(self, analysis: MeetingAnalysis, meeting_id: Optional[str] = None) -> str:
        if not meeting_id:
            raise ValueError("export_csv requires meeting_id in HTTP-only mode.")
        resp = self._client.get(self._url(f"/meetings/{meeting_id}/export/csv"))
        resp.raise_for_status()
        return resp.text

    # ── Jira ──────────────────────────────────────────────────────────────────
    def push_to_jira(
        self, analysis: MeetingAnalysis, *, meeting_id: Optional[str] = None
    ):
        if not meeting_id:
            raise ValueError("push_to_jira requires meeting_id in HTTP-only mode.")
        resp = self._client.post(self._url(f"/meetings/{meeting_id}/jira/push"))
        resp.raise_for_status()
        data = resp.json()
        job_id = data.get("job_id")
        if job_id:
            self._poll_job(job_id, timeout=120)
        return data

    # ── Helpers ───────────────────────────────────────────────────────────────
    def save_text_via_dialog(self, *, filename: str, content: str) -> Optional[str]:
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception as exc:
            raise RuntimeError(f"Tkinter is not available: {exc}") from exc
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

    def _poll_job(self, job_id: str, timeout: int = 180, interval: float = 2.0) -> dict:
        """Poll GET /jobs/{job_id} đến khi state = SUCCESS hoặc FAILURE."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = self._client.get(f"/api/v1/jobs/{job_id}")
            if resp.status_code == 200:
                data = resp.json()
                state = data.get("state", "PENDING")
                if state == "SUCCESS":
                    return data
                if state == "FAILURE":
                    raise RuntimeError(
                        f"Job {job_id} thất bại: {data.get('error', 'unknown error')}"
                    )
            time.sleep(interval)
        raise TimeoutError(f"Job {job_id} did not finish within {timeout}s.")


def _parse_meeting(data: dict) -> MeetingRecord:
    """Convert API response dict to MeetingRecord."""
    return MeetingRecord(
        id=str(data.get("id")) if data.get("id") else None,
        title=data.get("title", ""),
        transcript="",
        audio_path=data.get("audio_path"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )
