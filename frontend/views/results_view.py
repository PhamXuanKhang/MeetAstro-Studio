from __future__ import annotations

from typing import Callable

import flet as ft

from frontend.core.state import AppState


def _confidence_badge(conf: float) -> ft.Container:
    """Badge màu hiển thị confidence score."""
    if conf < 0.4:
        color = ft.Colors.RED_400
        label = f"{conf:.0%}"
    elif conf < 0.7:
        color = ft.Colors.ORANGE_400
        label = f"{conf:.0%}"
    else:
        color = ft.Colors.GREEN_500
        label = f"{conf:.0%}"
    return ft.Container(
        content=ft.Text(label, size=10, color=ft.Colors.WHITE),
        bgcolor=color,
        padding=ft.padding.symmetric(horizontal=5, vertical=1),
        border_radius=4,
    )


def build_results_view(
    *,
    page: ft.Page,
    state: AppState,
    toast: Callable,
    set_busy: Callable,
    on_navigate: Callable | None = None,
) -> ft.Control:
    rec = state.selected_meeting
    analysis = state.analysis

    def go_to_review(_):
        if on_navigate and state.current_meeting_id:
            on_navigate("review")

    header = ft.Container(
        padding=ft.padding.all(18),
        content=ft.Container(
            width=1100,
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(rec.title if rec else "Results", size=20, weight=ft.FontWeight.W_700),
                            ft.Text(
                                "Review extracted epics, tasks, and subtasks before pushing to Jira.",
                                size=12,
                                color=ft.Colors.GREY_700,
                            ),
                        ],
                        spacing=6,
                        expand=True,
                    ),
                    ft.ElevatedButton(
                        "Review & Push to Jira",
                        bgcolor=ft.Colors.BLUE_600,
                        color=ft.Colors.WHITE,
                        on_click=go_to_review,
                        visible=on_navigate is not None and state.current_meeting_id is not None,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        ),
    )

    if not analysis:
        empty = ft.Container(
            padding=ft.padding.all(18),
            content=ft.Container(
                width=1100,
                bgcolor=ft.Colors.WHITE,
                border_radius=16,
                border=ft.border.all(1, ft.Colors.GREY_200),
                padding=ft.padding.all(18),
                content=ft.Text("No analysis yet. Run Analyze in New meeting first.", color=ft.Colors.GREY_700),
            ),
        )
        return ft.Column([header, empty], spacing=0, expand=True)

    summary_card = (
        ft.Container(
            width=1100,
            bgcolor=ft.Colors.WHITE,
            border_radius=16,
            border=ft.border.all(1, ft.Colors.GREY_200),
            padding=ft.padding.all(18),
            content=ft.Column(
                [
                    ft.Text("Summary", size=14, weight=ft.FontWeight.W_700),
                    ft.Text(analysis.summary or "(empty)", size=12, color=ft.Colors.GREY_800),
                ],
                spacing=8,
            ),
        )
        if analysis.summary is not None
        else ft.Container()
    )

    epic_controls: list[ft.Control] = []
    for i, epic in enumerate(analysis.epics, 1):
        task_controls: list[ft.Control] = []
        for j, task in enumerate(epic.tasks, 1):
            task_controls.append(
                ft.Container(
                    padding=ft.padding.all(12),
                    bgcolor=ft.Colors.GREY_50,
                    border_radius=12,
                    content=ft.Column(
                        [
                            ft.Row([
                                ft.Text(f"Task {i}.{j}: {task.summary}", weight=ft.FontWeight.W_700, size=12, expand=True),
                                _confidence_badge(task.confidence) if task.confidence > 0 else ft.Container(),
                            ], spacing=6),
                            ft.Text(
                                f"👤 {task.assignee or 'TBD'}  |  📅 {task.deadline or 'N/A'}  |  🔥 {task.priority.value}",
                                size=11,
                                color=ft.Colors.GREY_800,
                            ),
                            ft.Text(task.context, size=11, color=ft.Colors.GREY_700) if task.context else ft.Container(),
                        ],
                        spacing=6,
                    ),
                )
            )
        epic_controls.append(
            ft.Container(
                width=1100,
                bgcolor=ft.Colors.WHITE,
                border_radius=16,
                border=ft.border.all(1, ft.Colors.GREY_200),
                padding=ft.padding.all(18),
                content=ft.Column(
                    [
                        ft.Text(f"Epic {i}: {epic.summary}", size=15, weight=ft.FontWeight.W_800),
                        ft.Text(epic.description, size=12, color=ft.Colors.GREY_700) if epic.description else ft.Container(),
                        ft.Column(task_controls, spacing=10),
                    ],
                    spacing=10,
                ),
            )
        )

    content = ft.Container(
        padding=ft.padding.all(18),
        content=ft.Container(
            alignment=ft.alignment.Alignment(0, -1),
            content=ft.Column(
                [summary_card, ft.Container(height=12), *epic_controls],
                spacing=12,
                scroll=ft.ScrollMode.AUTO,
            ),
        ),
        expand=True,
    )

    return ft.Column([header, content], spacing=0, expand=True)
