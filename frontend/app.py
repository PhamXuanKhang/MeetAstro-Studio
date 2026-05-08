from __future__ import annotations

import threading

import flet as ft

from frontend.components.sidebar import build_sidebar
from frontend.components.topbar import build_topbar
from frontend.core.state import AppState
from frontend.views.dashboard_view import build_dashboard_view
from frontend.views.history_view import build_history_view
from frontend.views.new_meeting_view import build_new_meeting_view
from frontend.views.results_view import build_results_view
from frontend.views.review_view import build_review_view
from frontend.views.settings_view import build_settings_view

_TITLES = {
    "home": "Overview",
    "new_meeting": "New Meeting",
    "results": "Results",
    "review": "Review",
    "history": "History",
    "settings": "Settings",
}


def build_app(page: ft.Page) -> None:
    state = AppState()
    _search_timer: list = [None]

    # ── Persistent busy banner — updated in-place, never rebuilt ─────────
    busy_text_ctrl = ft.Text("Working...", size=12, color=ft.Colors.GREY_800)
    busy_banner = ft.Container(
        visible=False,
        padding=ft.padding.symmetric(horizontal=18, vertical=10),
        bgcolor=ft.Colors.AMBER_50,
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.AMBER_100)),
        content=ft.Row(
            [ft.ProgressRing(width=18, height=18, stroke_width=2), busy_text_ctrl],
            spacing=10,
        ),
    )

    # ── Persistent content slots ──────────────────────────────────────────
    view_container = ft.Container(expand=True, bgcolor=ft.Colors.GREY_50)
    topbar_slot = ft.Container(expand=False)
    sidebar_slot = ft.Container(expand=False)

    def toast(message: str, *, error: bool = False) -> None:
        page.snack_bar = ft.SnackBar(
            ft.Text(message),
            bgcolor=ft.Colors.RED_600 if error else ft.Colors.GREY_900,
        )
        page.snack_bar.open = True
        page.update()

    def _ui(fn) -> None:
        try:
            page.call_from_thread(fn)
        except Exception:
            fn()

    def set_busy(busy: bool, text: str = "") -> None:
        state.busy = busy
        state.progress_text = text

        def _update():
            busy_text_ctrl.value = text or "Working..."
            busy_banner.visible = busy
            try:
                busy_banner.update()
            except Exception:
                pass

        _ui(_update)

    def _swap_content(route: str) -> None:
        """Swap chỉ phần nội dung — không bao giờ gọi page.clean()."""
        if route == "home":
            body = build_dashboard_view(
                page=page, state=state, toast=toast, set_busy=set_busy,
                on_open_results=lambda rec: _open_record(rec),
            )
        elif route == "new_meeting":
            body = build_new_meeting_view(
                page=page, state=state, toast=toast, set_busy=set_busy,
                on_open_results=lambda: on_navigate("results"),
                on_open_review=lambda: on_navigate("review"),
            )
        elif route == "results":
            body = build_results_view(
                page=page, state=state, toast=toast, set_busy=set_busy,
                on_navigate=on_navigate,
            )
        elif route == "review":
            body = build_review_view(
                page=page, state=state, toast=toast, set_busy=set_busy,
                on_navigate=on_navigate,
            )
        elif route == "history":
            body = build_history_view(
                page=page, state=state, toast=toast, set_busy=set_busy,
                on_open_results=lambda rec: _open_record(rec),
            )
        elif route == "settings":
            body = build_settings_view(page=page, state=state, toast=toast, set_busy=set_busy)
        else:
            body = ft.Text("Page not found", color=ft.Colors.GREY_700)

        title = _TITLES.get(route, route.replace("_", " ").title())
        topbar_slot.content = build_topbar(
            title=title,
            search_value=state.search_query,
            on_search_change=on_search_change,
            on_record_click=lambda: on_navigate("new_meeting"),
        )
        sidebar_slot.content = build_sidebar(active_route=route, on_navigate=on_navigate)
        view_container.content = body
        page.update()

    def on_navigate(route: str) -> None:
        state.route = route
        _swap_content(route)

    def on_search_change(e: ft.ControlEvent) -> None:
        state.search_query = e.control.value or ""
        if _search_timer[0]:
            _search_timer[0].cancel()
        t = threading.Timer(0.3, lambda: _ui(lambda: _swap_content(state.route)))
        _search_timer[0] = t
        t.start()

    def _open_record(rec) -> None:
        state.selected_meeting = rec
        state.current_meeting_id = str(rec.get("id")) if isinstance(rec, dict) else None
        state.audio_storage_path = (
            rec.get("audio_storage_path") if isinstance(rec, dict) else None
        )
        state.meeting_status = rec.get("status", "") if isinstance(rec, dict) else ""
        on_navigate("results")

    # Build layout once — never call page.clean() again
    content_col = ft.Column(
        [topbar_slot, busy_banner, view_container],
        spacing=0,
        expand=True,
    )
    page.add(
        ft.Row(
            [sidebar_slot, content_col],
            expand=True,
            spacing=0,
        )
    )
    _swap_content(state.route)
