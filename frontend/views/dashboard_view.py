from __future__ import annotations

import threading

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

    # Persistent slots — updated from background thread via page.call_from_thread
    loading_ring = ft.Container(
        padding=ft.padding.all(48),
        content=ft.Column(
            [
                ft.ProgressRing(width=32, height=32, stroke_width=3),
                ft.Text("Đang tải...", size=12, color=ft.Colors.GREY_600),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
        alignment=ft.alignment.center,
        visible=True,
    )
    cards_col = ft.Column(spacing=12, visible=False)

    def _build_card(rec) -> ft.Control:
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

    def _load() -> None:
        try:
            backend.init_db()
            meetings = backend.list_meetings()
            state.cached_meetings = meetings
        except Exception as exc:
            page.call_from_thread(lambda: toast(f"Không thể tải danh sách: {exc}", error=True))
            meetings = state.cached_meetings  # fall back to cache

        q = (state.search_query or "").strip().lower()
        if q:
            meetings = [m for m in meetings if q in (m.title or "").lower()]

        def _update():
            loading_ring.visible = False
            if not meetings:
                cards_col.controls = [
                    ft.Container(
                        padding=ft.padding.all(18),
                        border_radius=16,
                        bgcolor=ft.Colors.WHITE,
                        border=ft.border.all(1, ft.Colors.GREY_200),
                        content=ft.Column(
                            [
                                ft.Text("Chưa có cuộc họp nào.", size=14, weight=ft.FontWeight.W_700),
                                ft.Text(
                                    "Bắt đầu bằng cách ghi âm hoặc tải file audio.",
                                    size=12,
                                    color=ft.Colors.GREY_700,
                                ),
                            ],
                            spacing=6,
                        ),
                    )
                ]
            else:
                cards_col.controls = [_build_card(m) for m in meetings]
            cards_col.visible = True
            page.update()

        page.call_from_thread(_update)

    threading.Thread(target=_load, daemon=True).start()

    return ft.Container(
        padding=ft.padding.all(18),
        expand=True,
        content=ft.Container(
            alignment=ft.alignment.Alignment(0, -1),
            content=ft.Container(
                width=1100,
                content=ft.Column([loading_ring, cards_col], spacing=0),
            ),
        ),
    )
