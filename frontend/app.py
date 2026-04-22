from __future__ import annotations

import flet as ft

from frontend.components.sidebar import build_sidebar
from frontend.components.topbar import build_topbar
from frontend.core.state import AppState
from frontend.views.dashboard_view import build_dashboard_view
from frontend.views.history_view import build_history_view
from frontend.views.new_meeting_view import build_new_meeting_view
from frontend.views.results_view import build_results_view
from frontend.views.settings_view import build_settings_view


def build_app(page: ft.Page) -> None:
    state = AppState()

    content_host = ft.Container(expand=True)

    def toast(message: str, *, error: bool = False) -> None:
        page.snack_bar = ft.SnackBar(
            ft.Text(message),
            bgcolor=ft.Colors.RED_600 if error else ft.Colors.GREY_900,
        )
        page.snack_bar.open = True
        page.update()

    def set_busy(busy: bool, text: str = "") -> None:
        state.busy = busy
        state.progress_text = text
        render()

    def on_navigate(route: str) -> None:
        state.route = route
        render()

    def on_search_change(e: ft.ControlEvent) -> None:
        state.search_query = e.control.value or ""
        render()

    def on_record_click() -> None:
        state.route = "new_meeting"
        render()

    def render() -> None:
        route = state.route

        if route == "home":
            title = "For you"
            body = build_dashboard_view(page=page, state=state, toast=toast, set_busy=set_busy, on_open_results=lambda rec: _open_record(rec))
        elif route == "new_meeting":
            title = "New meeting"
            body = build_new_meeting_view(page=page, state=state, toast=toast, set_busy=set_busy, on_open_results=lambda: on_navigate("results"))
        elif route == "results":
            title = "Results"
            body = build_results_view(page=page, state=state, toast=toast, set_busy=set_busy)
        elif route == "history":
            title = "History"
            body = build_history_view(page=page, state=state, toast=toast, set_busy=set_busy, on_open_results=lambda rec: _open_record(rec))
        elif route == "settings":
            title = "Settings"
            body = build_settings_view(page=page, state=state, toast=toast, set_busy=set_busy)
        else:
            title = "Home"
            body = ft.Text("Not found")

        sidebar = build_sidebar(active_route=route, on_navigate=on_navigate)
        topbar = build_topbar(
            title=title,
            search_value=state.search_query,
            on_search_change=on_search_change,
            on_record_click=on_record_click,
        )

        busy_banner = (
            ft.Container(
                padding=ft.padding.symmetric(horizontal=18, vertical=10),
                bgcolor=ft.Colors.AMBER_50,
                border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.AMBER_100)),
                content=ft.Row(
                    [
                        ft.ProgressRing(width=18, height=18, stroke_width=2),
                        ft.Text(state.progress_text or "Đang xử lý...", size=12, color=ft.Colors.GREY_800),
                    ],
                    spacing=10,
                ),
            )
            if state.busy
            else ft.Container(height=0)
        )

        content_host.content = ft.Column(
            [topbar, busy_banner, ft.Container(expand=True, bgcolor=ft.Colors.GREY_50, content=body)],
            spacing=0,
            expand=True,
        )

        page.clean()
        page.add(ft.Row([sidebar, content_host], expand=True, spacing=0))
        page.update()

    def _open_record(rec) -> None:
        state.selected_meeting = rec
        state.analysis = rec.analysis
        state.transcript = rec.transcript or ""
        state.audio_path = rec.audio_path
        on_navigate("results")

    render()

