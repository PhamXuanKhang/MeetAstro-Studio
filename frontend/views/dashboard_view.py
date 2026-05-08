from __future__ import annotations

import flet as ft

from frontend.core.state import AppState
from frontend.mock_data import get_mock_meetings


def build_dashboard_view(
    *,
    page: ft.Page,
    state: AppState,
    toast,
    set_busy,
    on_open_results,
) -> ft.Control:
    meetings = get_mock_meetings()
    state.cached_meetings = meetings

    cards = [_meeting_card(m, on_open_results) for m in meetings]

    return ft.Container(
        padding=ft.padding.all(18),
        expand=True,
        bgcolor=ft.Colors.GREY_50,
        content=ft.Column(
            [
                ft.Text("Overview", size=20, weight=ft.FontWeight.W_700),
                ft.Text(
                    "Mock dashboard using the Phase 1.1 hybrid contract shapes.",
                    size=12,
                    color=ft.Colors.GREY_700,
                ),
                ft.Column(cards, spacing=10),
            ],
            spacing=12,
        ),
    )


def _meeting_card(meeting: dict, on_open_results) -> ft.Control:
    return ft.Container(
        on_click=lambda _e: on_open_results(meeting),
        bgcolor=ft.Colors.WHITE,
        border=ft.border.all(1, ft.Colors.GREY_200),
        border_radius=8,
        padding=ft.padding.all(14),
        content=ft.Row(
            [
                ft.Icon(ft.Icons.PLAY_CIRCLE_OUTLINE, color=ft.Colors.TEAL_600),
                ft.Column(
                    [
                        ft.Text(meeting.get("title", "Untitled"), weight=ft.FontWeight.W_700),
                        ft.Text(
                            f"{meeting.get('status', 'pending')} | "
                            f"{meeting.get('audio_duration_seconds', 0)}s",
                            size=11,
                            color=ft.Colors.GREY_700,
                        ),
                    ],
                    spacing=3,
                    expand=True,
                ),
                ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ft.Colors.GREY_500),
            ],
            spacing=12,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )
