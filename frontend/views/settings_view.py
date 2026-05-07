from __future__ import annotations

import flet as ft

from frontend.core.state import AppState


def build_settings_view(
    *,
    page: ft.Page,
    state: AppState,
    toast,
    set_busy,
) -> ft.Control:
    jira_site = ft.TextField(label="Jira site URL", value="https://company.atlassian.net")
    jira_email = ft.TextField(label="Jira email", value="user@example.com")
    jira_token = ft.TextField(label="Jira API token", password=True, can_reveal_password=True)
    jira_project = ft.TextField(label="Project key", value="DEV")

    openai_key = ft.TextField(label="OpenAI API key", password=True, can_reveal_password=True)
    openai_model = ft.TextField(label="Default model", value="gpt-4o")

    def save_mock(_e) -> None:
        toast("Mock settings saved locally. No API call was made.")

    jira_content = ft.Container(
        padding=ft.padding.all(16),
        content=ft.Column(
            [jira_site, jira_email, jira_token, jira_project, _save_button(save_mock)],
            spacing=10,
        ),
    )
    openai_content = ft.Container(
        padding=ft.padding.all(16),
        visible=False,
        content=ft.Column(
            [openai_key, openai_model, _save_button(save_mock)],
            spacing=10,
        ),
    )

    def show_jira_tab(_e) -> None:
        jira_content.visible = True
        openai_content.visible = False
        jira_tab_button.disabled = True
        openai_tab_button.disabled = False
        page.update()

    def show_openai_tab(_e) -> None:
        jira_content.visible = False
        openai_content.visible = True
        jira_tab_button.disabled = False
        openai_tab_button.disabled = True
        page.update()

    jira_tab_button = ft.ElevatedButton(
        "Jira",
        icon=ft.Icons.INTEGRATION_INSTRUCTIONS_OUTLINED,
        disabled=True,
        on_click=show_jira_tab,
    )
    openai_tab_button = ft.OutlinedButton(
        "OpenAI",
        icon=ft.Icons.KEY_OUTLINED,
        on_click=show_openai_tab,
    )
    content = ft.Column(
        [
            ft.Row([jira_tab_button, openai_tab_button], spacing=8),
            jira_content,
            openai_content,
        ],
        spacing=0,
    )

    return ft.Container(
        padding=ft.padding.all(18),
        expand=True,
        bgcolor=ft.Colors.GREY_50,
        content=ft.Container(
            width=960,
            bgcolor=ft.Colors.WHITE,
            border=ft.border.all(1, ft.Colors.GREY_200),
            border_radius=8,
            padding=ft.padding.all(12),
            content=ft.Column(
                [
                    ft.Text("Settings", size=20, weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Mock provider settings UI. Real Fernet save happens via FastAPI later.",
                        size=12,
                        color=ft.Colors.GREY_700,
                    ),
                    content,
                ],
                spacing=10,
            ),
        ),
    )


def _save_button(on_click) -> ft.Control:
    return ft.ElevatedButton("Save mock config", icon=ft.Icons.SAVE, on_click=on_click)
