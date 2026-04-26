from __future__ import annotations

import threading

import flet as ft

from frontend.core.backend_factory import get_backend
from frontend.core.state import AppState
from frontend.utils.helpers import fmt_dt


def build_history_view(
    *,
    page: ft.Page,
    state: AppState,
    toast,
    set_busy,
    on_open_results,
) -> ft.Control:
    backend = get_backend()

    loading_ring = ft.Container(
        padding=ft.padding.all(48),
        content=ft.Column(
            [
                ft.ProgressRing(width=32, height=32, stroke_width=3),
                ft.Text("Đang tải lịch sử...", size=12, color=ft.Colors.GREY_600),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=12,
        ),
        alignment=ft.alignment.center,
        visible=True,
    )
    list_container = ft.Container(visible=False)

    def _load() -> None:
        try:
            backend.init_db()
            meetings = backend.list_meetings()
        except Exception as exc:
            page.call_from_thread(lambda: toast(f"Không thể tải lịch sử: {exc}", error=True))
            meetings = []

        q = (state.search_query or "").strip().lower()
        if q:
            meetings = [m for m in meetings if q in (m.title or "").lower()]

        def _update():
            loading_ring.visible = False
            if not meetings:
                list_container.content = ft.Text(
                    "Chưa có lịch sử cuộc họp.", color=ft.Colors.GREY_700
                )
            else:
                items: list[ft.Control] = []
                for rec in meetings:
                    def _mk_open(r):
                        return lambda _e: on_open_results(r)

                    items.append(
                        ft.ListTile(
                            title=ft.Text(rec.title or "Note", weight=ft.FontWeight.W_600),
                            subtitle=ft.Text(fmt_dt(rec.created_at), size=11, color=ft.Colors.GREY_700),
                            leading=ft.Icon(ft.Icons.DESCRIPTION_OUTLINED),
                            trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
                            on_click=_mk_open(rec),
                        )
                    )
                list_container.content = ft.Container(
                    border_radius=16,
                    bgcolor=ft.Colors.WHITE,
                    border=ft.border.all(1, ft.Colors.GREY_200),
                    content=ft.Column(items, spacing=0),
                )
            list_container.visible = True
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
                content=ft.Column([loading_ring, list_container], spacing=0),
            ),
        ),
    )
