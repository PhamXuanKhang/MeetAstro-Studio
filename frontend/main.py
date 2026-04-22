from __future__ import annotations

import sys
from pathlib import Path

import flet as ft

# Cho phép chạy kiểu: `uv run .\\frontend\\main.py` (sys.path mặc định là `frontend/`)
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from frontend.app import build_app


def main(page: ft.Page) -> None:
    page.title = "AI Meeting Assistant"
    page.padding = 0
    page.window_min_width = 1100
    page.window_min_height = 700
    page.theme_mode = ft.ThemeMode.LIGHT

    build_app(page)


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.FLET_APP)

