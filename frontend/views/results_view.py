from __future__ import annotations

from typing import Any, Callable

import flet as ft

from frontend.core.state import AppState
from frontend.mock_data import get_mock_meeting_detail


def build_results_view(
    *,
    page: ft.Page,
    state: AppState,
    toast: Callable,
    set_busy: Callable,
    on_navigate: Callable | None = None,
) -> ft.Control:
    _ensure_mock_detail(state)
    meeting = state.selected_meeting or {}

    header = ft.Container(
        padding=ft.padding.symmetric(horizontal=22, vertical=16),
        bgcolor=ft.Colors.WHITE,
        border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.GREY_200)),
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text(
                            meeting.get("title", "Meeting Detail"),
                            size=20,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Text(
                            f"Status: {meeting.get('status', 'draft')} | "
                            f"Storage: {meeting.get('storage_provider', 'local')}",
                            size=12,
                            color=ft.Colors.GREY_700,
                        ),
                    ],
                    spacing=4,
                    expand=True,
                ),
                ft.OutlinedButton(
                    "History",
                    icon=ft.Icons.HISTORY,
                    on_click=lambda _: on_navigate("history") if on_navigate else None,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
    )

    summary_tab = _summary_tab(state)
    transcript_tab = _transcript_tab(state)
    action_items_tab = _action_items_tab(state)
    summary_tab.visible = True
    transcript_tab.visible = False
    action_items_tab.visible = False

    def show_tab(name: str) -> None:
        summary_tab.visible = name == "summary"
        transcript_tab.visible = name == "transcript"
        action_items_tab.visible = name == "action_items"
        summary_button.disabled = name == "summary"
        transcript_button.disabled = name == "transcript"
        action_items_button.disabled = name == "action_items"
        page.update()

    summary_button = ft.ElevatedButton(
        "Summary",
        icon=ft.Icons.SUMMARIZE_OUTLINED,
        disabled=True,
        on_click=lambda _: show_tab("summary"),
    )
    transcript_button = ft.OutlinedButton(
        "Transcript",
        icon=ft.Icons.SUBTITLES_OUTLINED,
        on_click=lambda _: show_tab("transcript"),
    )
    action_items_button = ft.OutlinedButton(
        "Action Items",
        icon=ft.Icons.ACCOUNT_TREE_OUTLINED,
        on_click=lambda _: show_tab("action_items"),
    )
    tabs = ft.Column(
        [
            ft.Container(
                padding=ft.padding.symmetric(horizontal=22, vertical=10),
                bgcolor=ft.Colors.WHITE,
                border=ft.border.only(bottom=ft.BorderSide(1, ft.Colors.GREY_200)),
                content=ft.Row(
                    [summary_button, transcript_button, action_items_button],
                    spacing=8,
                ),
            ),
            summary_tab,
            transcript_tab,
            action_items_tab,
        ],
        spacing=0,
        expand=True,
    )

    return ft.Column([header, tabs], spacing=0, expand=True)


def _ensure_mock_detail(state: AppState) -> None:
    if state.selected_meeting and state.analysis_result and state.transcript_segments:
        return
    detail = get_mock_meeting_detail()
    state.selected_meeting = detail["meeting"]
    state.current_meeting_id = detail["meeting"]["id"]
    state.meeting_status = detail["meeting"]["status"]
    state.audio_storage_path = detail["meeting"]["audio_storage_path"]
    state.analysis_result = detail["analysis_result"]
    state.transcript_segments = detail["transcript_segments"]
    state.action_items = detail["action_items"]


def _summary_tab(state: AppState) -> ft.Control:
    analysis = state.analysis_result or {}
    decisions = analysis.get("key_decisions") or []
    parking = analysis.get("parking_lot") or []

    return _tab_shell(
        ft.Column(
            [
                _section_title("Meeting Summary"),
                ft.Text(analysis.get("summary_text") or "No summary yet.", size=13),
                ft.Divider(height=22),
                _section_title("Key Decisions"),
                _bullet_list(decisions),
                ft.Divider(height=22),
                _section_title("Parking Lot"),
                _bullet_list(parking),
                ft.Divider(height=22),
                ft.Row(
                    [
                        _meta_tile("AI model", analysis.get("ai_model", "N/A")),
                        _meta_tile("Input tokens", str(analysis.get("input_tokens", 0))),
                        _meta_tile("Output tokens", str(analysis.get("output_tokens", 0))),
                    ],
                    spacing=10,
                ),
            ],
            spacing=10,
        )
    )


def _transcript_tab(state: AppState) -> ft.Control:
    rows: list[ft.Control] = []
    for segment in state.transcript_segments:
        rows.append(
            ft.Container(
                bgcolor=ft.Colors.WHITE,
                border=ft.border.all(1, ft.Colors.GREY_200),
                border_radius=8,
                padding=ft.padding.all(12),
                content=ft.Row(
                    [
                        ft.Container(
                            width=94,
                            content=ft.Column(
                                [
                                    ft.Text(
                                        segment.get("speaker", "Speaker"),
                                        size=12,
                                        weight=ft.FontWeight.W_700,
                                    ),
                                    ft.Text(
                                        _time_range(segment),
                                        size=10,
                                        color=ft.Colors.GREY_600,
                                    ),
                                ],
                                spacing=2,
                            ),
                        ),
                        ft.Text(segment.get("content", ""), size=13, expand=True),
                    ],
                    spacing=14,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            )
        )

    return _tab_shell(ft.Column(rows, spacing=10))


def _action_items_tab(state: AppState) -> ft.Control:
    tree = build_action_item_tree(state.action_items)
    controls = [_action_item_node(node, depth=0) for node in tree]
    return _tab_shell(ft.Column(controls, spacing=10))


def build_action_item_tree(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {item["id"]: {**item, "children": []} for item in items}
    roots: list[dict[str, Any]] = []
    for item in by_id.values():
        parent_id = item.get("parent_id")
        parent = by_id.get(parent_id) if parent_id else None
        if parent:
            parent["children"].append(item)
        else:
            roots.append(item)
    return roots


def _action_item_node(item: dict[str, Any], *, depth: int) -> ft.Control:
    children = item.get("children") or []
    checkbox = ft.Checkbox(value=bool(item.get("is_selected")), disabled=True)
    type_color = {
        "epic": ft.Colors.BLUE_50,
        "task": ft.Colors.TEAL_50,
        "subtask": ft.Colors.GREY_100,
    }.get(item.get("item_type"), ft.Colors.GREY_100)

    body = ft.Container(
        bgcolor=ft.Colors.WHITE,
        border=ft.border.all(1, ft.Colors.GREY_200),
        border_radius=8,
        padding=ft.padding.all(12),
        margin=ft.margin.only(left=depth * 24),
        content=ft.Column(
            [
                ft.Row(
                    [
                        checkbox,
                        ft.Container(
                            bgcolor=type_color,
                            border_radius=4,
                            padding=ft.padding.symmetric(horizontal=7, vertical=3),
                            content=ft.Text(
                                str(item.get("item_type", "item")).upper(),
                                size=10,
                                weight=ft.FontWeight.W_700,
                            ),
                        ),
                        ft.Text(
                            item.get("title", "Untitled"),
                            weight=ft.FontWeight.W_700,
                            expand=True,
                        ),
                        _status_badge(item.get("review_status", "draft")),
                        _confidence_badge(float(item.get("confidence_score") or 0)),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Text(item.get("description") or "", size=12, color=ft.Colors.GREY_700),
                ft.Text(
                    (
                        f"Assignee: {item.get('assignee') or 'TBD'} | "
                        f"Deadline: {item.get('deadline') or 'N/A'} | "
                        f"Priority: {item.get('priority') or 'medium'} | "
                        f"Sync: {item.get('sync_status') or 'pending'}"
                    ),
                    size=11,
                    color=ft.Colors.GREY_700,
                ),
            ],
            spacing=7,
        ),
    )
    if not children:
        return body
    return ft.Column([body, *[_action_item_node(child, depth=depth + 1) for child in children]])


def _tab_shell(content: ft.Control) -> ft.Control:
    return ft.Container(
        padding=ft.padding.all(18),
        expand=True,
        bgcolor=ft.Colors.GREY_50,
        content=ft.Container(
            width=1120,
            content=ft.Column([content], scroll=ft.ScrollMode.AUTO, expand=True),
        ),
    )


def _section_title(text: str) -> ft.Text:
    return ft.Text(text, size=15, weight=ft.FontWeight.W_700)


def _bullet_list(items: list[str]) -> ft.Control:
    if not items:
        return ft.Text("None", size=12, color=ft.Colors.GREY_600)
    return ft.Column(
        [
            ft.Row(
                [ft.Icon(ft.Icons.CIRCLE, size=7), ft.Text(item, size=12, expand=True)]
            )
            for item in items
        ],
        spacing=6,
    )


def _meta_tile(label: str, value: str) -> ft.Control:
    return ft.Container(
        bgcolor=ft.Colors.WHITE,
        border=ft.border.all(1, ft.Colors.GREY_200),
        border_radius=8,
        padding=ft.padding.all(10),
        expand=True,
        content=ft.Column(
            [ft.Text(label, size=11, color=ft.Colors.GREY_600), ft.Text(value, size=13)],
            spacing=3,
        ),
    )


def _status_badge(status: str) -> ft.Container:
    color = {
        "approved": ft.Colors.GREEN_100,
        "rejected": ft.Colors.RED_100,
        "edited": ft.Colors.BLUE_100,
        "draft": ft.Colors.GREY_100,
    }.get(status, ft.Colors.GREY_100)
    return ft.Container(
        bgcolor=color,
        border_radius=4,
        padding=ft.padding.symmetric(horizontal=7, vertical=3),
        content=ft.Text(status, size=10, weight=ft.FontWeight.W_600),
    )


def _confidence_badge(score: float) -> ft.Container:
    color = ft.Colors.GREEN_500 if score >= 0.8 else ft.Colors.ORANGE_400
    return ft.Container(
        bgcolor=color,
        border_radius=4,
        padding=ft.padding.symmetric(horizontal=7, vertical=3),
        content=ft.Text(f"{score:.0%}", size=10, color=ft.Colors.WHITE),
    )


def _time_range(segment: dict[str, Any]) -> str:
    return f"{segment.get('start_time', 0):.1f}s - {segment.get('end_time', 0):.1f}s"
