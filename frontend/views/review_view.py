from __future__ import annotations

from typing import Callable

import flet as ft

from frontend.core.state import AppState
from frontend.mock_data import get_mock_meeting_detail


def build_review_view(
    *,
    page: ft.Page,
    state: AppState,
    toast: Callable,
    set_busy: Callable,
    on_navigate: Callable,
) -> ft.Control:
    if not state.action_items:
        detail = get_mock_meeting_detail()
        state.action_items = detail["action_items"]

    approved = sum(1 for item in state.action_items if item.get("review_status") == "approved")
    selected = sum(1 for item in state.action_items if item.get("is_selected"))

    return ft.Container(
        padding=ft.padding.all(18),
        expand=True,
        bgcolor=ft.Colors.GREY_50,
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    "Action Item Review",
                                    size=20,
                                    weight=ft.FontWeight.W_700,
                                ),
                                ft.Text(
                                    (
                                        "Mock review summary. Detailed tree lives in "
                                        "Meeting Detail > Action Items."
                                    ),
                                    size=12,
                                    color=ft.Colors.GREY_700,
                                ),
                            ],
                            expand=True,
                        ),
                        ft.OutlinedButton(
                            "Back to Meeting Detail",
                            icon=ft.Icons.ARROW_BACK,
                            on_click=lambda _: on_navigate("results"),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    border=ft.border.all(1, ft.Colors.GREY_200),
                    border_radius=8,
                    padding=ft.padding.all(16),
                    content=ft.Row(
                        [
                            _metric("Total", str(len(state.action_items))),
                            _metric("Approved", str(approved)),
                            _metric("Selected", str(selected)),
                        ],
                        spacing=12,
                    ),
                ),
                ft.ElevatedButton(
                    "Open Action Items Tree",
                    icon=ft.Icons.ACCOUNT_TREE_OUTLINED,
                    on_click=lambda _: on_navigate("results"),
                ),
            ],
            spacing=14,
        ),
    )


def _metric(label: str, value: str) -> ft.Control:
    return ft.Container(
        expand=True,
        bgcolor=ft.Colors.GREY_50,
        border_radius=8,
        padding=ft.padding.all(12),
        content=ft.Column(
            [
                ft.Text(label, size=11, color=ft.Colors.GREY_600),
                ft.Text(value, size=18, weight=ft.FontWeight.W_700),
            ],
            spacing=4,
        ),
    )
