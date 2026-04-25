from __future__ import annotations

import threading

import flet as ft

from frontend.core.backend_factory import get_backend
from frontend.core.state import AppState


def build_new_meeting_view(
    *,
    page: ft.Page,
    state: AppState,
    toast,
    set_busy,
    on_open_results,
    on_open_review=None,
) -> ft.Control:
    backend = get_backend()

    def ui(fn) -> None:
        # Flet yêu cầu UI updates chạy trên main thread.
        try:
            page.call_from_thread(fn)
        except Exception:
            fn()

    meeting_title = ft.TextField(
        label="Meeting title",
        hint_text="e.g. Sprint planning 04/15",
        dense=True,
    )
    diarization = ft.Checkbox(
        label="Speaker diarization",
        value=False,
    )

    transcript = ft.TextField(
        label="Transcript (editable before analysis)",
        value=state.transcript or "",
        multiline=True,
        min_lines=12,
        max_lines=14,
        dense=True,
    )

    summary = ft.TextField(
        label="Summary",
        value=state.analysis.summary if state.analysis else "",
        multiline=True,
        min_lines=4,
        max_lines=6,
        dense=True,
        read_only=True,
    )

    def _sync_state_from_controls() -> None:
        state.transcript = transcript.value or ""

    chosen_file_text = ft.Text(value="No file selected", size=11, color=ft.Colors.GREY_700)

    def pick_file(_e) -> None:
        # Avoid ft.FilePicker on desktop due to runtime control errors.
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception as exc:
            toast(f"Tkinter is not available: {exc}", error=True)
            return

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            filetypes=[
                ("Audio", "*.wav *.mp3 *.m4a *.ogg *.flac"),
                ("All files", "*.*"),
            ]
        )
        root.destroy()
        if not path:
            return
        state.audio_path = path
        state.current_meeting_id = None
        state.analysis = None
        state.transcript = ""
        chosen_file_text.value = path
        toast("Audio file selected.")
        page.update()

    record_status = ft.Text("", size=11, color=ft.Colors.GREY_700)

    def _ensure_meeting_id() -> str:
        if state.current_meeting_id:
            return state.current_meeting_id
        title = (meeting_title.value or "").strip() or "Untitled meeting"
        meeting_id = backend.create_meeting(
            title=title,
            transcript="",
            audio_path=state.audio_path,
            analysis=None,
        )
        state.current_meeting_id = str(meeting_id)
        return state.current_meeting_id

    def _run_bg(fn, *, busy_text: str):
        def _runner():
            try:
                ui(lambda: set_busy(True, busy_text))
                fn()
            finally:
                ui(lambda: set_busy(False, ""))

        threading.Thread(target=_runner, daemon=True).start()

    def start_record(_e) -> None:
        def _do():
            path = backend.start_recording()
            state.audio_path = path
            state.current_meeting_id = None
            state.analysis = None
            state.transcript = ""
            ui(lambda: _set_record_status(f"🔴 Recording... ({path})"))

        _run_bg(_do, busy_text="Starting system recording...")

    def stop_record(_e) -> None:
        def _do():
            path = backend.stop_recording()
            state.audio_path = path
            ui(lambda: _set_record_status(f"✅ Saved: {path}"))
            ui(lambda: toast("Recording stopped."))

        _run_bg(_do, busy_text="Stopping recording...")

    def transcribe_click(_e) -> None:
        if not state.audio_path:
            toast("Please select or record audio first.", error=True)
            return

        def _do():
            meeting_id = _ensure_meeting_id()
            text = backend.transcribe(
                state.audio_path,
                diarize=bool(diarization.value),
                meeting_id=meeting_id,
            )
            state.transcript = text
            ui(lambda: _set_transcript(text))
            ui(lambda: toast("Transcription completed."))

        _run_bg(_do, busy_text="Transcribing audio...")

    def analyze_click(_e) -> None:
        _sync_state_from_controls()
        if not state.transcript.strip():
            toast("Transcript is empty.", error=True)
            return

        def _do_analyze():
            meeting_id = _ensure_meeting_id()
            backend.update_transcript(meeting_id, state.transcript)
            analysis = backend.analyze(state.transcript, meeting_id=meeting_id)
            state.analysis = analysis
            ui(lambda: _set_summary(analysis.summary or ""))
            ui(lambda: toast("Analysis completed."))
            ui(on_open_results)

        _run_bg(_do_analyze, busy_text="Running analysis...")

    def export_md(_e) -> None:
        if not state.analysis or not state.current_meeting_id:
            toast("No analysis to export yet.", error=True)
            return
        content = backend.export_markdown(state.analysis, meeting_id=state.current_meeting_id)
        path = backend.save_text_via_dialog(filename="meeting_analysis.md", content=content)
        if path:
            toast(f"Saved: {path}")

    def export_json(_e) -> None:
        if not state.analysis or not state.current_meeting_id:
            toast("No analysis to export yet.", error=True)
            return
        content = backend.export_json(state.analysis, meeting_id=state.current_meeting_id)
        path = backend.save_text_via_dialog(filename="meeting_analysis.json", content=content)
        if path:
            toast(f"Saved: {path}")

    def export_csv(_e) -> None:
        if not state.analysis or not state.current_meeting_id:
            toast("No analysis to export yet.", error=True)
            return
        content = backend.export_csv(state.analysis, meeting_id=state.current_meeting_id)
        path = backend.save_text_via_dialog(filename="meeting_analysis.csv", content=content)
        if path:
            toast(f"Saved: {path}")

    def push_jira(_e) -> None:
        if not state.analysis or not state.current_meeting_id:
            toast("No analysis to push yet.", error=True)
            return
        if on_open_review is not None:
            on_open_review()
        else:
            toast("Open the Review screen to approve items before pushing.", error=True)

    def _set_transcript(text: str) -> None:
        transcript.value = text
        page.update()

    def _set_summary(text: str) -> None:
        summary.value = text
        page.update()

    def _set_record_status(text: str) -> None:
        record_status.value = text
        page.update()

    input_card = ft.Container(
        width=1100,
        bgcolor=ft.Colors.WHITE,
        border_radius=16,
        border=ft.border.all(1, ft.Colors.GREY_200),
        padding=ft.padding.all(18),
        content=ft.Column(
            [
                ft.Text("Audio input", size=14, weight=ft.FontWeight.W_800),
                meeting_title,
                ft.Row(
                    [
                        ft.ElevatedButton("Upload audio", icon=ft.Icons.UPLOAD_FILE, on_click=pick_file),
                        ft.TextButton("Start recording", icon=ft.Icons.FIBER_MANUAL_RECORD, on_click=start_record),
                        ft.TextButton("Stop recording", icon=ft.Icons.STOP_CIRCLE_OUTLINED, on_click=stop_record),
                    ],
                    spacing=10,
                ),
                chosen_file_text,
                record_status,
                diarization,
                ft.ElevatedButton("Transcribe", icon=ft.Icons.MIC, on_click=transcribe_click),
            ],
            spacing=10,
        ),
    )

    transcript_card = ft.Container(
        width=1100,
        bgcolor=ft.Colors.WHITE,
        border_radius=16,
        border=ft.border.all(1, ft.Colors.GREY_200),
        padding=ft.padding.all(18),
        content=ft.Column(
            [
                ft.Text("Transcript", size=14, weight=ft.FontWeight.W_800),
                transcript,
                ft.ElevatedButton("Analyze", icon=ft.Icons.AUTO_AWESOME, on_click=analyze_click),
                summary,
            ],
            spacing=10,
        ),
    )

    actions_card = ft.Container(
        width=1100,
        bgcolor=ft.Colors.WHITE,
        border_radius=16,
        border=ft.border.all(1, ft.Colors.GREY_200),
        padding=ft.padding.all(18),
        content=ft.Column(
            [
                ft.Text("Actions", size=14, weight=ft.FontWeight.W_800),
                ft.Row(
                    [
                        ft.OutlinedButton("Export Markdown", icon=ft.Icons.DESCRIPTION_OUTLINED, on_click=export_md),
                        ft.OutlinedButton("Export JSON", icon=ft.Icons.DATA_OBJECT, on_click=export_json),
                        ft.OutlinedButton("Export CSV", icon=ft.Icons.TABLE_VIEW, on_click=export_csv),
                        ft.ElevatedButton("Review & Push to Jira", icon=ft.Icons.ROCKET_LAUNCH, on_click=push_jira),
                    ],
                    wrap=True,
                    spacing=10,
                    run_spacing=10,
                ),
            ],
            spacing=12,
        ),
    )

    return ft.Container(
        padding=ft.padding.all(18),
        content=ft.Container(
            alignment=ft.alignment.Alignment(0, -1),
            content=ft.Column(
                [input_card, transcript_card, actions_card],
                spacing=14,
                scroll=ft.ScrollMode.AUTO,
            ),
        ),
        expand=True,
    )
