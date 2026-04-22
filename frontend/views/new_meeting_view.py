from __future__ import annotations

import threading

import flet as ft

from frontend.core.local_backend import LocalBackend
from frontend.core.state import AppState


def build_new_meeting_view(
    *,
    page: ft.Page,
    state: AppState,
    toast,
    set_busy,
    on_open_results,
) -> ft.Control:
    backend = LocalBackend()

    def ui(fn) -> None:
        # Flet yêu cầu UI updates chạy trên main thread.
        try:
            page.call_from_thread(fn)
        except Exception:
            fn()

    meeting_title = ft.TextField(label="Tên cuộc họp", hint_text="Vd: Họp sprint planning 15/01", dense=True)
    diarization = ft.Checkbox(
        label="Nhận diện người nói (Diarization)",
        value=False,
    )

    transcript = ft.TextField(
        label="Transcript (có thể chỉnh sửa trước khi phân tích)",
        value=state.transcript or "",
        multiline=True,
        min_lines=12,
        max_lines=14,
        dense=True,
    )

    summary = ft.TextField(
        label="Tóm tắt (streaming)",
        value="",
        multiline=True,
        min_lines=4,
        max_lines=6,
        dense=True,
        read_only=True,
    )

    def _sync_state_from_controls() -> None:
        state.transcript = transcript.value or ""

    chosen_file_text = ft.Text(value="Chưa chọn file", size=11, color=ft.Colors.GREY_700)

    def pick_file(_e) -> None:
        # Tránh dùng ft.FilePicker (Flet 0.84 desktop báo "Unknown control: FilePicker")
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception as exc:
            toast(f"Không import được tkinter: {exc}", error=True)
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
        chosen_file_text.value = path
        toast("Đã chọn file audio.")
        page.update()

    record_status = ft.Text("", size=11, color=ft.Colors.GREY_700)

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
            backend.init_db()
            path = backend.start_recording()
            state.audio_path = path
            ui(lambda: _set_record_status(f"🔴 Đang ghi âm... ({path})"))

        _run_bg(_do, busy_text="Đang bắt đầu ghi âm hệ thống...")

    def stop_record(_e) -> None:
        def _do():
            path = backend.stop_recording()
            state.audio_path = path
            ui(lambda: _set_record_status(f"✅ Đã lưu: {path}"))
            ui(lambda: toast("Dừng ghi âm thành công."))

        _run_bg(_do, busy_text="Đang dừng ghi âm...")

    def transcribe_click(_e) -> None:
        if not state.audio_path:
            toast("Vui lòng chọn file hoặc ghi âm trước.", error=True)
            return

        def _do():
            text = backend.transcribe(state.audio_path, diarize=bool(diarization.value))
            state.transcript = text
            ui(lambda: _set_transcript(text))
            ui(lambda: toast("Transcribe thành công."))

        _run_bg(_do, busy_text="Đang transcribe...")

    def analyze_click(_e) -> None:
        _sync_state_from_controls()
        if not state.transcript.strip():
            toast("Transcript đang trống.", error=True)
            return

        def _do_stream_and_analyze():
            ui(lambda: _set_summary(""))

            def on_token(tok: str) -> None:
                ui(lambda: _append_summary(tok))

            backend.generate_summary_stream(state.transcript, on_token=on_token)
            analysis = backend.analyze(state.transcript)
            if not analysis.summary:
                analysis.summary = summary.value or ""
            state.analysis = analysis
            ui(lambda: toast("Phân tích xong."))
            ui(on_open_results)

        _run_bg(_do_stream_and_analyze, busy_text="Đang phân tích bằng GPT...")

    def export_md(_e) -> None:
        if not state.analysis:
            toast("Chưa có analysis.", error=True)
            return
        content = backend.export_markdown(state.analysis)
        path = backend.save_text_via_dialog(filename="meeting_analysis.md", content=content)
        if path:
            toast(f"Đã lưu: {path}")

    def export_json(_e) -> None:
        if not state.analysis:
            toast("Chưa có analysis.", error=True)
            return
        content = backend.export_json(state.analysis)
        path = backend.save_text_via_dialog(filename="meeting_analysis.json", content=content)
        if path:
            toast(f"Đã lưu: {path}")

    def export_csv(_e) -> None:
        if not state.analysis:
            toast("Chưa có analysis.", error=True)
            return
        content = backend.export_csv(state.analysis)
        path = backend.save_text_via_dialog(filename="meeting_analysis.csv", content=content)
        if path:
            toast(f"Đã lưu: {path}")

    def save_db(_e) -> None:
        if not state.analysis:
            toast("Chưa có analysis.", error=True)
            return
        title = (meeting_title.value or "").strip() or "Note"
        backend.init_db()
        mid = backend.create_meeting(
            title=title,
            transcript=state.transcript,
            audio_path=state.audio_path,
            analysis=state.analysis,
        )
        toast(f"Đã lưu vào DB. ID={mid}")

    def push_jira(_e) -> None:
        if not state.analysis:
            toast("Chưa có analysis.", error=True)
            return

        def _do():
            result = backend.push_to_jira(state.analysis)
            if result.is_stub:
                ui(lambda: toast("Jira STUB mode — chưa gửi API thật.", error=True))
            else:
                ui(lambda: toast(f"Đẩy Jira OK. Epics={result.epic_count} Tasks={result.task_count}"))

        _run_bg(_do, busy_text="Đang đẩy lên Jira...")

    def _set_transcript(text: str) -> None:
        transcript.value = text
        page.update()

    def _set_summary(text: str) -> None:
        summary.value = text
        page.update()

    def _append_summary(tok: str) -> None:
        summary.value = (summary.value or "") + tok
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
                ft.Text("Audio Input", size=14, weight=ft.FontWeight.W_800),
                meeting_title,
                ft.Row(
                    [
                        ft.ElevatedButton("Upload file", icon=ft.Icons.UPLOAD_FILE, on_click=pick_file),
                        ft.TextButton("Start record", icon=ft.Icons.FIBER_MANUAL_RECORD, on_click=start_record),
                        ft.TextButton("Stop record", icon=ft.Icons.STOP_CIRCLE_OUTLINED, on_click=stop_record),
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
                        ft.OutlinedButton("Tải Markdown", icon=ft.Icons.DESCRIPTION_OUTLINED, on_click=export_md),
                        ft.OutlinedButton("Tải JSON", icon=ft.Icons.DATA_OBJECT, on_click=export_json),
                        ft.OutlinedButton("Tải CSV", icon=ft.Icons.TABLE_VIEW, on_click=export_csv),
                        ft.ElevatedButton("Lưu vào DB", icon=ft.Icons.SAVE, on_click=save_db),
                        ft.ElevatedButton("Đẩy lên Jira", icon=ft.Icons.ROCKET_LAUNCH, on_click=push_jira),
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

