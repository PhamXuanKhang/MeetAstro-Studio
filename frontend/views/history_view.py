from __future__ import annotations

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

    try:
        backend.init_db()
        meetings = backend.list_meetings()
    except Exception as exc:
        toast(f"Failed to load history: {exc}", error=True)
        meetings = []

    q = (state.search_query or "").strip().lower()
    if q:
        meetings = [m for m in meetings if q in (m.title or "").lower() or q in (m.transcript or "").lower()]

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

    if not items:
        return ft.Container(
            padding=ft.padding.all(18),
            content=ft.Text("No history available yet.", color=ft.Colors.GREY_700),
            expand=True,
        )

    return ft.Container(
        padding=ft.padding.all(18),
        content=ft.Container(
            alignment=ft.alignment.Alignment(0, -1),
            content=ft.Container(
                width=1100,
                border_radius=16,
                bgcolor=ft.Colors.WHITE,
                border=ft.border.all(1, ft.Colors.GREY_200),
                content=ft.Column(items, spacing=0),
            ),
        ),
        expand=True,
    )

