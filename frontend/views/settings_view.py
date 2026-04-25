from __future__ import annotations

import json

import flet as ft

from frontend.core.backend_factory import get_backend
from frontend.core.state import AppState


def build_settings_view(
    *,
    page: ft.Page,
    state: AppState,
    toast,
    set_busy,
) -> ft.Control:
    backend = get_backend()
    providers = ["jira", "trello", "notion", "slack", "teams"]

    provider_dd = ft.Dropdown(
        options=[ft.dropdown.Option(p) for p in providers],
        value="jira",
        width=200,
    )

    status_text = ft.Text("", size=12, color=ft.Colors.GREY_700)

    def refresh_status() -> None:
        try:
            backend.init_db()
            active = set(backend.list_provider_configs())
            p = provider_dd.value
            if p in active:
                status_text.value = f"✓ {p} configured"
                status_text.color = ft.Colors.GREEN_700
            else:
                status_text.value = f"{p} not configured"
                status_text.color = ft.Colors.GREY_700
        except Exception as exc:
            status_text.value = f"Error: {exc}"
            status_text.color = ft.Colors.RED_700

    url = ft.TextField(label="Base URL", hint_text="https://yourcompany.atlassian.net", dense=True)
    email = ft.TextField(label="Email", dense=True)
    token = ft.TextField(label="API Token", password=True, can_reveal_password=True, dense=True)
    project_key = ft.TextField(label="Project Key", hint_text="PROJ", dense=True)

    generic_kv = ft.TextField(
        label="Config JSON (for non-Jira providers)",
        hint_text='{"token":"..."}',
        multiline=True,
        min_lines=4,
        max_lines=6,
        dense=True,
    )

    def on_provider_change(_e) -> None:
        refresh_status()
        render_form()

    provider_dd.on_change = on_provider_change

    form_host = ft.Container()

    def render_form() -> None:
        p = provider_dd.value
        if p == "jira":
            form_host.content = ft.Column([url, email, token, project_key], spacing=10)
        else:
            form_host.content = ft.Column([generic_kv], spacing=10)
        page.update()

    def save_config(_e) -> None:
        p = provider_dd.value
        try:
            backend.init_db()
            if p == "jira":
                cfg = {
                    "url": (url.value or "").strip(),
                    "email": (email.value or "").strip(),
                    "token": (token.value or "").strip(),
                    "project_key": (project_key.value or "").strip(),
                }
                cfg = {k: v for k, v in cfg.items() if v}
            else:
                raw = (generic_kv.value or "").strip()
                if not raw:
                    cfg = {}
                else:
                    try:
                        cfg = json.loads(raw)
                        if not isinstance(cfg, dict):
                            raise ValueError("JSON must be an object.")
                    except (ValueError, json.JSONDecodeError) as exc:
                        toast(f"Invalid JSON: {exc}", error=True)
                        return
            if not cfg:
                toast("Please fill at least one field.", error=True)
                return
            backend.set_provider_config(p, cfg)
            toast(f"Saved {p} configuration.")
            refresh_status()
            page.update()
        except Exception as exc:
            toast(f"Failed to save config: {exc}", error=True)

    def delete_config(_e) -> None:
        p = provider_dd.value
        try:
            backend.delete_provider_config(p)
            toast(f"Deleted {p} configuration.")
            refresh_status()
            page.update()
        except Exception as exc:
            toast(f"Failed to delete config: {exc}", error=True)

    refresh_status()
    render_form()

    card = ft.Container(
        width=1100,
        bgcolor=ft.Colors.WHITE,
        border_radius=16,
        border=ft.border.all(1, ft.Colors.GREY_200),
        padding=ft.padding.all(18),
        content=ft.Column(
            [
                ft.Text("Integrations", size=16, weight=ft.FontWeight.W_800),
                ft.Row([ft.Text("Provider", size=12), provider_dd, status_text], spacing=12),
                ft.Divider(height=1),
                form_host,
                ft.Row(
                    [
                        ft.ElevatedButton("Save configuration", icon=ft.Icons.SAVE, on_click=save_config),
                        ft.OutlinedButton("Delete configuration", icon=ft.Icons.DELETE_OUTLINE, on_click=delete_config),
                    ],
                    spacing=12,
                ),
            ],
            spacing=12,
        ),
    )

    return ft.Container(
        padding=ft.padding.all(18),
        content=ft.Container(alignment=ft.alignment.Alignment(0, -1), content=card),
        expand=True,
    )
