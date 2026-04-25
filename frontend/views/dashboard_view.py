from __future__ import annotations

import flet as ft

from frontend.core.backend_factory import get_backend
from frontend.core.state import AppState
from frontend.utils.helpers import fmt_dt


def build_dashboard_view(
    *,
    page: ft.Page,
    state: AppState,
    toast,
    set_busy,
    on_open_results,
) -> ft.Control:
    backend = get_backend()

    def load() -> list:
        try:
            backend.init_db()
            meetings = backend.list_meetings()
            state.cached_meetings = meetings
            return meetings
        except Exception as exc:
            toast(f"Failed to load meetings: {exc}", error=True)
            return []

    meetings = state.cached_meetings or load()

    q = (state.search_query or "").strip().lower()
    if q:
        meetings = [m for m in meetings if q in (m.title or "").lower()]

    def meeting_card(rec) -> ft.Control:
        def _open(_e):
            on_open_results(rec)

        if rec.analysis and rec.analysis.summary:
            ellipsis = "…" if len(rec.analysis.summary) > 90 else ""
            subtitle = f"{fmt_dt(rec.created_at)}  •  {rec.analysis.summary[:90]}{ellipsis}"
        else:
            subtitle = fmt_dt(rec.created_at)

        thumb = ft.Container(
            width=44,
            height=44,
            border_radius=14,
            bgcolor=ft.Colors.TEAL_50,
            content=ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, color=ft.Colors.TEAL_400),
            alignment=ft.alignment.Alignment(0, 0),
        )

        return ft.Container(
            on_click=_open,
            border_radius=16,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
            padding=ft.padding.all(14),
            content=ft.Row(
                [
                    thumb,
                    ft.Column(
                        [
                            ft.Text(rec.title or "Note", size=15, weight=ft.FontWeight.W_700),
                            ft.Text(subtitle, size=11, color=ft.Colors.GREY_700),
                        ],
                        spacing=4,
                        tight=True,
                        expand=True,
                    ),
                    ft.Icon(ft.Icons.CHEVRON_RIGHT, color=ft.Colors.GREY_500),
                ],
                spacing=12,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    if not meetings:
        empty = ft.Container(
            padding=ft.padding.all(18),
            border_radius=16,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
            content=ft.Column(
                [
                    ft.Text("No meetings yet.", size=14, weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Start a new meeting to record, upload, and analyze.",
                        size=12, color=ft.Colors.GREY_700
                    ),
                ],
                spacing=6,
            ),
        )
        return ft.Container(padding=ft.padding.all(18), content=empty, expand=True)

    cards = ft.Column([meeting_card(m) for m in meetings], spacing=12)
    return ft.Container(
        padding=ft.padding.all(18),
        content=ft.Container(
            alignment=ft.alignment.Alignment(0, -1),
            content=ft.Container(width=1100, content=cards),
        ),
        expand=True,
    )
