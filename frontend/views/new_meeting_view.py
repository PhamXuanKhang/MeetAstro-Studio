from __future__ import annotations

import threading
import time

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
    _timer_running: list[bool] = [False]

    def ui(fn) -> None:
        try:
            page.call_from_thread(fn)
        except Exception:
            fn()

    # ── Persistent controls (handlers reference these via late binding) ───

    meeting_title = ft.TextField(
        label="Tiêu đề cuộc họp",
        hint_text="VD: Sprint Planning 04/25",
        dense=True,
        border_radius=10,
    )
    diarization = ft.Checkbox(label="Nhận dạng người nói", value=False)

    # Recording indicator
    dot = ft.Container(
        width=12, height=12,
        bgcolor=ft.Colors.RED_600,
        border_radius=6,
        opacity=1.0,
    )
    timer_text = ft.Text("00:00", size=20, weight=ft.FontWeight.W_700, color=ft.Colors.RED_600)
    rec_indicator = ft.Container(
        visible=False,
        bgcolor=ft.Colors.RED_50,
        border_radius=12,
        border=ft.border.all(1, ft.Colors.RED_200),
        padding=ft.padding.symmetric(horizontal=24, vertical=14),
        content=ft.Row(
            [dot, ft.Text("ĐANG GHI ÂM", size=13, weight=ft.FontWeight.W_700, color=ft.Colors.RED_700), timer_text],
            spacing=12,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
    )

    chosen_file_text = ft.Text(
        f"Đã chọn: {state.audio_path}" if state.audio_path else "Chưa chọn file",
        size=12,
        color=ft.Colors.GREY_600,
    )
    record_status = ft.Text("", size=12, color=ft.Colors.GREY_600)

    transcript = ft.TextField(
        label="Transcript (có thể chỉnh sửa trước khi phân tích)",
        value=state.transcript or "",
        multiline=True,
        min_lines=10,
        max_lines=14,
        dense=True,
        border_radius=10,
    )

    summary = ft.TextField(
        label="Tóm tắt",
        value=state.analysis.summary if state.analysis else "",
        multiline=True,
        min_lines=4,
        max_lines=6,
        dense=True,
        read_only=True,
        border_radius=10,
    )

    progress_bar = ft.Column(
        [
            ft.ProgressBar(color=ft.Colors.BLUE_400, bgcolor=ft.Colors.BLUE_50),
            ft.Text("Đang xử lý... (có thể mất vài phút)", size=11, color=ft.Colors.GREY_600),
        ],
        visible=False,
        spacing=6,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    # ── Handlers ─────────────────────────────────────────────────────────

    def _run_bg(fn, *, busy_text: str) -> None:
        def _runner():
            try:
                ui(lambda: set_busy(True, busy_text))
                fn()
            finally:
                ui(lambda: set_busy(False, ""))
        threading.Thread(target=_runner, daemon=True).start()

    def _run_timer_loop() -> None:
        start = time.time()
        tick = [0]
        while _timer_running[0]:
            elapsed = int(time.time() - start)
            m, s = divmod(elapsed, 60)
            label = f"{m:02d}:{s:02d}"
            tick[0] += 1
            show_dot = (tick[0] % 2 == 0)

            def _upd(lbl=label, sd=show_dot):
                timer_text.value = lbl
                dot.opacity = 1.0 if sd else 0.25
                try:
                    rec_indicator.update()
                except Exception:
                    pass

            try:
                page.call_from_thread(_upd)
            except Exception:
                pass
            time.sleep(1)

    def start_record(_e) -> None:
        def _do():
            path = backend.start_recording()
            state.audio_path = path
            state.current_meeting_id = None
            state.analysis = None
            state.transcript = ""
            state.is_recording = True
            _timer_running[0] = True
            threading.Thread(target=_run_timer_loop, daemon=True).start()

            def _show():
                record_btn.visible = False
                upload_btn.disabled = True
                rec_indicator.visible = True
                timer_text.value = "00:00"
                record_status.value = ""
                chosen_file_text.value = f"Sẽ lưu: {path}"
                workflow_section.visible = True
                page.update()

            ui(_show)

        _run_bg(_do, busy_text="Đang khởi động ghi âm...")

    def stop_record(_e) -> None:
        def _do():
            _timer_running[0] = False
            state.is_recording = False
            path = backend.stop_recording()
            state.audio_path = path

            def _show():
                record_btn.visible = True
                upload_btn.disabled = False
                rec_indicator.visible = False
                record_status.value = f"✅ Đã lưu: {path}"
                chosen_file_text.value = path
                workflow_section.visible = True
                page.update()

            ui(_show)
            ui(lambda: toast("Ghi âm đã dừng."))

        _run_bg(_do, busy_text="Đang dừng ghi âm...")

    def pick_file(_e) -> None:
        try:
            import tkinter as tk
            from tkinter import filedialog
        except Exception as exc:
            toast(f"Tkinter không khả dụng: {exc}", error=True)
            return
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            filetypes=[("Audio", "*.wav *.mp3 *.m4a *.ogg *.flac"), ("All files", "*.*")]
        )
        root.destroy()
        if not path:
            return
        state.audio_path = path
        state.current_meeting_id = None
        state.analysis = None
        state.transcript = ""
        chosen_file_text.value = path
        transcript.value = ""
        summary.value = ""
        workflow_section.visible = True
        toast("Đã chọn file audio.")
        page.update()

    def _ensure_meeting_id() -> str:
        if state.current_meeting_id:
            return state.current_meeting_id
        title = (meeting_title.value or "").strip() or "Untitled meeting"
        meeting_id = backend.create_meeting(
            title=title, transcript="", audio_path=state.audio_path, analysis=None,
        )
        state.current_meeting_id = str(meeting_id)
        return state.current_meeting_id

    def transcribe_click(_e) -> None:
        if not state.audio_path:
            toast("Vui lòng chọn hoặc ghi âm trước.", error=True)
            return

        def _do():
            ui(lambda: _set_progress(True))
            meeting_id = _ensure_meeting_id()
            text = backend.transcribe(
                state.audio_path, diarize=bool(diarization.value), meeting_id=meeting_id,
            )
            state.transcript = text
            ui(lambda: _set_progress(False))
            ui(lambda: _set_transcript(text))
            ui(lambda: toast("Chuyển văn bản hoàn tất."))

        _run_bg(_do, busy_text="Đang chuyển văn bản...")

    def analyze_click(_e) -> None:
        state.transcript = transcript.value or ""
        if not state.transcript.strip():
            toast("Transcript trống.", error=True)
            return

        def _do():
            ui(lambda: _set_progress(True))
            meeting_id = _ensure_meeting_id()
            backend.update_transcript(meeting_id, state.transcript)
            analysis = backend.analyze(state.transcript, meeting_id=meeting_id)
            state.analysis = analysis
            ui(lambda: _set_progress(False))
            ui(lambda: _set_summary(analysis.summary or ""))
            ui(lambda: toast("Phân tích hoàn tất."))
            ui(on_open_results)

        _run_bg(_do, busy_text="Đang phân tích...")

    def export_md(_e) -> None:
        if not state.analysis or not state.current_meeting_id:
            toast("Chưa có kết quả phân tích.", error=True)
            return
        content = backend.export_markdown(state.analysis, meeting_id=state.current_meeting_id)
        path = backend.save_text_via_dialog(filename="meeting_analysis.md", content=content)
        if path:
            toast(f"Đã lưu: {path}")

    def export_json(_e) -> None:
        if not state.analysis or not state.current_meeting_id:
            toast("Chưa có kết quả phân tích.", error=True)
            return
        content = backend.export_json(state.analysis, meeting_id=state.current_meeting_id)
        path = backend.save_text_via_dialog(filename="meeting_analysis.json", content=content)
        if path:
            toast(f"Đã lưu: {path}")

    def export_csv(_e) -> None:
        if not state.analysis or not state.current_meeting_id:
            toast("Chưa có kết quả phân tích.", error=True)
            return
        content = backend.export_csv(state.analysis, meeting_id=state.current_meeting_id)
        path = backend.save_text_via_dialog(filename="meeting_analysis.csv", content=content)
        if path:
            toast(f"Đã lưu: {path}")

    def push_jira(_e) -> None:
        if not state.analysis or not state.current_meeting_id:
            toast("Chưa có kết quả phân tích.", error=True)
            return
        if on_open_review is not None:
            on_open_review()
        else:
            toast("Mở màn hình Review để duyệt items trước khi push.", error=True)

    def _set_transcript(text: str) -> None:
        transcript.value = text
        page.update()

    def _set_summary(text: str) -> None:
        summary.value = text
        page.update()

    def _set_progress(visible: bool) -> None:
        progress_bar.visible = visible
        try:
            progress_bar.update()
        except Exception:
            page.update()

    # ── Big action buttons ────────────────────────────────────────────────

    record_btn = ft.ElevatedButton(
        "Ghi âm",
        icon=ft.Icons.MIC,
        on_click=start_record,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.RED_600,
            color=ft.Colors.WHITE,
            padding=ft.padding.symmetric(horizontal=40, vertical=20),
            text_style=ft.TextStyle(size=16, weight=ft.FontWeight.W_700),
            shape=ft.RoundedRectangleBorder(radius=14),
        ),
        height=72,
    )

    upload_btn = ft.OutlinedButton(
        "Tải file audio",
        icon=ft.Icons.UPLOAD_FILE,
        on_click=pick_file,
        style=ft.ButtonStyle(
            padding=ft.padding.symmetric(horizontal=40, vertical=20),
            text_style=ft.TextStyle(size=16, weight=ft.FontWeight.W_700),
            shape=ft.RoundedRectangleBorder(radius=14),
            side=ft.BorderSide(2, ft.Colors.GREY_400),
        ),
        height=72,
    )

    # ── Workflow section (shown after audio is ready) ─────────────────────

    workflow_section = ft.Container(
        visible=bool(state.audio_path),
        content=ft.Column(
            [
                ft.Divider(height=1, color=ft.Colors.GREY_200),
                ft.Container(height=8),
                # Step indicator
                ft.Row(
                    [
                        _step_badge("1", "Audio", done=bool(state.audio_path)),
                        ft.Icon(ft.Icons.ARROW_FORWARD, size=14, color=ft.Colors.GREY_400),
                        _step_badge("2", "Transcript", done=bool(state.transcript)),
                        ft.Icon(ft.Icons.ARROW_FORWARD, size=14, color=ft.Colors.GREY_400),
                        _step_badge("3", "Phân tích", done=bool(state.analysis)),
                    ],
                    spacing=8,
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=8),
                # Meeting settings
                meeting_title,
                diarization,
                ft.ElevatedButton(
                    "Chuyển văn bản",
                    icon=ft.Icons.SUBTITLES,
                    on_click=transcribe_click,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.BLUE_600,
                        color=ft.Colors.WHITE,
                        padding=ft.padding.symmetric(horizontal=24, vertical=14),
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                ),
                progress_bar,
                transcript,
                ft.ElevatedButton(
                    "Phân tích",
                    icon=ft.Icons.AUTO_AWESOME,
                    on_click=analyze_click,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.PURPLE_600,
                        color=ft.Colors.WHITE,
                        padding=ft.padding.symmetric(horizontal=24, vertical=14),
                        shape=ft.RoundedRectangleBorder(radius=10),
                    ),
                ),
                summary,
                # Export + push actions
                ft.Row(
                    [
                        ft.OutlinedButton("Export MD", icon=ft.Icons.DESCRIPTION_OUTLINED, on_click=export_md),
                        ft.OutlinedButton("Export JSON", icon=ft.Icons.DATA_OBJECT, on_click=export_json),
                        ft.OutlinedButton("Export CSV", icon=ft.Icons.TABLE_VIEW, on_click=export_csv),
                        ft.ElevatedButton(
                            "Review & Push to Jira",
                            icon=ft.Icons.ROCKET_LAUNCH,
                            on_click=push_jira,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.INDIGO_600,
                                color=ft.Colors.WHITE,
                                shape=ft.RoundedRectangleBorder(radius=10),
                            ),
                        ),
                    ],
                    wrap=True,
                    spacing=8,
                    run_spacing=8,
                ),
            ],
            spacing=14,
        ),
    )

    # ── Hero section ──────────────────────────────────────────────────────

    hero = ft.Column(
        [
            ft.Text("Cuộc họp mới", size=26, weight=ft.FontWeight.W_800, text_align=ft.TextAlign.CENTER),
            ft.Text(
                "Ghi âm trực tiếp hoặc tải file audio để bắt đầu",
                size=13,
                color=ft.Colors.GREY_600,
                text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=20),
            ft.Row([record_btn, upload_btn], alignment=ft.MainAxisAlignment.CENTER, spacing=20),
            ft.Container(height=10),
            rec_indicator,
            ft.Container(height=2),
            chosen_file_text,
            record_status,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=8,
    )

    return ft.Container(
        padding=ft.padding.all(24),
        expand=True,
        content=ft.Column(
            [
                ft.Container(
                    padding=ft.padding.symmetric(vertical=24),
                    content=hero,
                    alignment=ft.alignment.center,
                ),
                workflow_section,
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )


def _step_badge(num: str, label: str, *, done: bool) -> ft.Container:
    if done:
        bg, tc, icon = ft.Colors.GREEN_100, ft.Colors.GREEN_800, ft.Icons.CHECK_CIRCLE_OUTLINE
    else:
        bg, tc, icon = ft.Colors.GREY_100, ft.Colors.GREY_600, ft.Icons.RADIO_BUTTON_UNCHECKED
    return ft.Container(
        bgcolor=bg,
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=12, vertical=6),
        content=ft.Row(
            [ft.Icon(icon, size=14, color=tc), ft.Text(label, size=12, color=tc, weight=ft.FontWeight.W_600)],
            spacing=4,
        ),
    )
