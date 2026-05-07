from __future__ import annotations

import flet as ft

from frontend.core.state import AppState
from frontend.mock_data import get_mock_meetings


def build_history_view(
    *,
    page: ft.Page,
    state: AppState,
    toast,
    set_busy,
    on_open_results,
) -> ft.Control:
    meetings = get_mock_meetings()
    q = (state.search_query or "").strip().lower()
    if q:
        meetings = [m for m in meetings if q in (m.get("title") or "").lower()]

    items: list[ft.Control] = []
    for meeting in meetings:
        items.append(_meeting_tile(meeting, on_open_results))

    content = (
        ft.Column(items, spacing=0)
        if items
        else ft.Text("No mock meetings found.", color=ft.Colors.GREY_700)
    )

    return ft.Container(
        padding=ft.padding.all(18),
        expand=True,
        bgcolor=ft.Colors.GREY_50,
        content=ft.Container(
            width=1100,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
            border_radius=8,
            content=content,
        ),
    )


def _meeting_tile(meeting: dict, on_open_results) -> ft.Control:
    return ft.ListTile(
        title=ft.Text(meeting.get("title", "Untitled"), weight=ft.FontWeight.W_600),
        subtitle=ft.Text(
            f"{meeting.get('status', 'pending')} | {meeting.get('created_at', '')}",
            size=11,
            color=ft.Colors.GREY_700,
        ),
        leading=ft.Icon(ft.Icons.DESCRIPTION_OUTLINED),
        trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
        on_click=lambda _e: on_open_results(meeting),
    )
