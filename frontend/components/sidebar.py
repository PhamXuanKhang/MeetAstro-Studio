from __future__ import annotations

import flet as ft

from frontend.config import CONFIG


def build_sidebar(
    *,
    active_route: str,
    on_navigate,
) -> ft.Control:
    def nav_item(label: str, route: str, icon: str) -> ft.Control:
        selected = active_route == route

        def _click(_e):
            on_navigate(route)

        return ft.Container(
            content=ft.Row(
                [
                    ft.Icon(
                        icon,
                        size=18,
                        color=ft.Colors.BLUE_600 if selected else ft.Colors.GREY_700
                    ),
                    ft.Text(
                        label,
                        size=13,
                        weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_500,
                        color=ft.Colors.BLUE_800 if selected else ft.Colors.GREY_800,
                    ),
                ],
                spacing=10,
            ),
            padding=ft.padding.symmetric(horizontal=14, vertical=10),
            border_radius=12,
            bgcolor=ft.Colors.BLUE_50 if selected else ft.Colors.TRANSPARENT,
            on_click=_click,
        )

    profile = ft.Container(
        content=ft.Row(
            [
                ft.CircleAvatar(
                    content=ft.Text("A"), bgcolor=ft.Colors.TEAL_500, color=ft.Colors.WHITE
                ),
                ft.Column(
                    [
                        ft.Text("AI Meeting Assistant", size=13, weight=ft.FontWeight.W_700),
                        ft.Text("Mock workspace", size=11, color=ft.Colors.GREY_600),
                    ],
                    spacing=2,
                    tight=True,
                ),
            ],
            spacing=10,
        ),
        padding=ft.padding.symmetric(horizontal=14, vertical=14),
    )

    return ft.Container(
        width=CONFIG.sidebar_width,
        bgcolor=ft.Colors.WHITE,
        border=ft.border.only(right=ft.BorderSide(1, ft.Colors.GREY_200)),
        content=ft.Column(
            [
                profile,
                ft.Divider(height=1),
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=12, vertical=12),
                    content=ft.Column(
                        [
                            nav_item("Overview", "home", ft.Icons.HOME_OUTLINED),
                            nav_item("New meeting", "new_meeting", ft.Icons.ADD_CIRCLE_OUTLINE),
                            nav_item("History", "history", ft.Icons.HISTORY),
                            nav_item("Settings", "settings", ft.Icons.SETTINGS_OUTLINED),
                        ],
                        spacing=6,
                    ),
                ),
                ft.Container(expand=True),
                ft.Container(
                    padding=ft.padding.only(left=14, right=14, bottom=14),
                    content=ft.Column(
                        [
                            ft.Text("API connection", size=11, color=ft.Colors.GREY_600),
                            ft.Text("Disconnected UI mode", size=10, color=ft.Colors.GREY_700),
                        ],
                        spacing=8,
                    ),
                ),
            ],
            spacing=0,
        ),
    )
