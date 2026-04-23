from __future__ import annotations

import flet as ft


def build_topbar(
    *,
    title: str,
    search_value: str,
    on_search_change,
    on_record_click,
) -> ft.Control:
    search = ft.TextField(
        value=search_value,
        hint_text="Search meetings or transcripts",
        height=40,
        dense=True,
        border_radius=14,
        border_color=ft.Colors.GREY_200,
        bgcolor=ft.Colors.GREY_50,
        prefix_icon=ft.Icons.SEARCH,
        on_change=on_search_change,
        expand=True,
    )

    record_btn = ft.ElevatedButton(
        "New recording",
        icon=ft.Icons.FIBER_MANUAL_RECORD,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.BLUE_600,
            color=ft.Colors.WHITE,
            shape=ft.RoundedRectangleBorder(radius=12),
            padding=ft.padding.symmetric(horizontal=18, vertical=12),
        ),
        on_click=lambda _e: on_record_click(),
    )

    return ft.Container(
        padding=ft.padding.symmetric(horizontal=18, vertical=14),
        bgcolor=ft.Colors.WHITE,
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.GREY_200)),
        content=ft.Row(
            [
                ft.Text(title, size=18, weight=ft.FontWeight.W_700),
                ft.Container(width=12),
                search,
                record_btn,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
    )

