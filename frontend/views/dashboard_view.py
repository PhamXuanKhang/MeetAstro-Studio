from __future__ import annotations

import flet as ft

from frontend.core.local_backend import LocalBackend
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
    backend = LocalBackend()

    def load() -> list:
        try:
            backend.init_db()
            meetings = backend.list_meetings()
            state.cached_meetings = meetings
            return meetings
        except Exception as exc:
            toast(f"Lỗi tải meetings: {exc}", error=True)
            return []

    meetings = state.cached_meetings or load()

    q = (state.search_query or "").strip().lower()
    if q:
        meetings = [m for m in meetings if q in (m.title or "").lower() or q in (m.transcript or "").lower()]

    def meeting_card(rec) -> ft.Control:
        def _open(_e):
            on_open_results(rec)

        subtitle = f"{fmt_dt(rec.created_at)}  •  {(len(rec.transcript or '') // 4)} chars"
        if rec.analysis and rec.analysis.summary:
            subtitle = f"{fmt_dt(rec.created_at)}  •  {rec.analysis.summary[:90]}{'…' if len(rec.analysis.summary) > 90 else ''}"

        thumb = ft.Container(
            width=44,
            height=44,
            border_radius=14,
            bgcolor=ft.Colors.PURPLE_50,
            content=ft.Icon(ft.Icons.PLAY_ARROW_ROUNDED, color=ft.Colors.PURPLE_400),
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
                    ft.Text("Chưa có meeting nào trong DB.", size=14, weight=ft.FontWeight.W_700),
                    ft.Text("Hãy vào New meeting để ghi âm / upload và phân tích.", size=12, color=ft.Colors.GREY_700),
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

