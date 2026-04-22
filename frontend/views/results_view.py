from __future__ import annotations

import flet as ft

from frontend.core.state import AppState


def build_results_view(
    *,
    page: ft.Page,
    state: AppState,
    toast,
    set_busy,
) -> ft.Control:
    rec = state.selected_meeting
    analysis = state.analysis

    header = ft.Container(
        padding=ft.padding.all(18),
        content=ft.Container(
            width=1100,
            content=ft.Column(
                [
                    ft.Text(rec.title if rec else "Results", size=20, weight=ft.FontWeight.W_700),
                    ft.Text(
                        "Hiển thị kết quả phân tích (Epic/Task/Subtask).",
                        size=12,
                        color=ft.Colors.GREY_700,
                    ),
                ],
                spacing=6,
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
                content=ft.Text("Chưa có analysis. Hãy Analyze ở New meeting trước.", color=ft.Colors.GREY_700),
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
                    ft.Text("Tóm tắt", size=14, weight=ft.FontWeight.W_700),
                    ft.Text(analysis.summary or "(trống)", size=12, color=ft.Colors.GREY_800),
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
                            ft.Text(f"Task {i}.{j}: {task.summary}", weight=ft.FontWeight.W_700, size=12),
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

