from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

# Cho phép chạy kiểu: `uv run .\\frontend\\main.py` (sys.path mặc định là `frontend/`)
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from frontend.app import build_app  # noqa: E402


def main(page: ft.Page) -> None:
    page.title = "AI Meeting Assistant"
    page.padding = 0
    page.window_min_width = 1100
    page.window_min_height = 700
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.TEAL,
        font_family="Aptos",
    )
    page.bgcolor = ft.Colors.GREY_50

    build_app(page)


if __name__ == "__main__":
    ft.run(main, view=ft.AppView.FLET_APP)
