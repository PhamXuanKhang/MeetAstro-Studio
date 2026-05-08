from __future__ import annotations

import threading
import time

import flet as ft

from frontend.core.state import AppState
from frontend.mock_data import get_mock_meeting_detail


def build_new_meeting_view(
    *,
    page: ft.Page,
    state: AppState,
    toast,
    set_busy,
    on_open_results,
    on_open_review=None,
) -> ft.Control:
    title = ft.TextField(
        label="Meeting title",
        hint_text="Sprint Planning - Phase 1.1",
        dense=True,
        border_radius=8,
    )
    selected_file = ft.Text("No local file selected", size=12, color=ft.Colors.GREY_600)
    processing = ft.Container(
        visible=False,
        bgcolor=ft.Colors.BLUE_50,
        border=ft.border.all(1, ft.Colors.BLUE_100),
        border_radius=8,
        padding=ft.padding.all(14),
        content=ft.Row(
            [
                ft.ProgressRing(width=20, height=20, stroke_width=2),
                ft.Text("Processing mock meeting...", size=12, color=ft.Colors.BLUE_800),
            ],
            spacing=10,
        ),
    )

    def _finish_mock_flow(source: str) -> None:
        def _run():
            _set_processing(True)
            time.sleep(1.2)
            detail = get_mock_meeting_detail()
            meeting_title = (title.value or "").strip()
            if meeting_title:
                detail["meeting"]["title"] = meeting_title
            detail["meeting"]["audio_storage_path"] = (
                state.audio_storage_path or detail["meeting"]["audio_storage_path"]
            )
            detail["meeting"]["status"] = "draft"
            state.selected_meeting = detail["meeting"]
            state.current_meeting_id = detail["meeting"]["id"]
            state.meeting_status = detail["meeting"]["status"]
            state.analysis_result = detail["analysis_result"]
            state.transcript_segments = detail["transcript_segments"]
            state.action_items = detail["action_items"]
            state.processing_state = ""
            state.is_recording = False
            _set_processing(False)
            toast(f"{source} mock flow completed.")
            on_open_results()

        threading.Thread(target=_run, daemon=True).start()

    def _set_processing(active: bool) -> None:
        def _update():
            processing.visible = active
            state.processing_state = "processing" if active else ""
            page.update()

        try:
            page.call_from_thread(_update)
        except Exception:
            _update()

    def pick_mock_file(_e) -> None:
        state.audio_storage_path = "file:///Users/name/Documents/MeetSync/records/mock-upload.wav"
        selected_file.value = state.audio_storage_path
        toast("Mock local audio path selected.")
        page.update()

    def start_upload_flow(_e) -> None:
        if not state.audio_storage_path:
            pick_mock_file(_e)
        _finish_mock_flow("Upload")

    def start_record_flow(_e) -> None:
        state.is_recording = True
        state.audio_storage_path = (
            "file:///Users/name/Documents/MeetSync/records/mock-live-record.wav"
        )
        selected_file.value = state.audio_storage_path
        page.update()
        _finish_mock_flow("Live record")

    upload_tab = ft.Container(
        padding=ft.padding.all(16),
        content=ft.Column(
            [
                title,
                ft.Container(height=4),
                ft.Text("Upload File", size=15, weight=ft.FontWeight.W_700),
                ft.Text(
                    "Phase 1.1 UI mock: only local path state changes, no API calls.",
                    size=12,
                    color=ft.Colors.GREY_700,
                ),
                ft.Row(
                    [
                        ft.OutlinedButton(
                            "Choose mock file",
                            icon=ft.Icons.UPLOAD_FILE,
                            on_click=pick_mock_file,
                        ),
                        ft.ElevatedButton(
                            "Start mock processing",
                            icon=ft.Icons.PLAY_ARROW,
                            on_click=start_upload_flow,
                        ),
                    ],
                    spacing=10,
                ),
                selected_file,
            ],
            spacing=12,
        ),
    )

    record_tab = ft.Container(
        padding=ft.padding.all(16),
        content=ft.Column(
            [
                ft.Text("Live Record", size=15, weight=ft.FontWeight.W_700),
                ft.Text(
                    (
                        "The real recording pipeline is future/research. "
                        "This button only simulates UI state."
                    ),
                    size=12,
                    color=ft.Colors.GREY_700,
                ),
                ft.ElevatedButton(
                    "Start mock live record",
                    icon=ft.Icons.MIC,
                    bgcolor=ft.Colors.RED_600,
                    color=ft.Colors.WHITE,
                    on_click=start_record_flow,
                ),
            ],
            spacing=12,
        ),
    )

    upload_tab.visible = True
    record_tab.visible = False

    def show_upload_tab(_e) -> None:
        upload_tab.visible = True
        record_tab.visible = False
        upload_tab_button.disabled = True
        record_tab_button.disabled = False
        page.update()

    def show_record_tab(_e) -> None:
        upload_tab.visible = False
        record_tab.visible = True
        upload_tab_button.disabled = False
        record_tab_button.disabled = True
        page.update()

    upload_tab_button = ft.ElevatedButton(
        "Upload File",
        icon=ft.Icons.UPLOAD_FILE,
        disabled=True,
        on_click=show_upload_tab,
    )
    record_tab_button = ft.OutlinedButton(
        "Live Record",
        icon=ft.Icons.MIC_NONE,
        on_click=show_record_tab,
    )
    tabs = ft.Column(
        [
            ft.Row([upload_tab_button, record_tab_button], spacing=8),
            upload_tab,
            record_tab,
            processing,
        ],
        spacing=0,
    )

    return ft.Container(
        padding=ft.padding.all(18),
        expand=True,
        bgcolor=ft.Colors.GREY_50,
        content=ft.Container(
            width=960,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
            border_radius=8,
            padding=ft.padding.all(12),
            content=ft.Column(
                [
                    ft.Text("New Meeting", size=20, weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Mock-first UI for the hybrid contract. No backend, HTTP, "
                        "or Supabase calls.",
                        size=12,
                        color=ft.Colors.GREY_700,
                    ),
                    tabs,
                ],
                spacing=10,
            ),
        ),
    )
