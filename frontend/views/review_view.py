"""
Review View: Human-in-the-Loop review screen.

Hiển thị danh sách ReviewItem với confidence badges.
User có thể edit, approve, reject từng item trước khi push Jira.
"""
from __future__ import annotations

import threading
from typing import Callable

import flet as ft

from frontend.core.state import AppState


def build_review_view(
    *,
    page: ft.Page,
    state: AppState,
    toast: Callable,
    set_busy: Callable,
    on_navigate: Callable,
) -> ft.Control:
    meeting_id = state.current_meeting_id
    if not meeting_id:
        return ft.Column([
            ft.Container(
                padding=ft.padding.all(24),
                content=ft.Text("No meeting selected for review.", color=ft.Colors.GREY_700),
            )
        ])

    # ── Header ──────────────────────────────────────────────────────────────
    header = ft.Container(
        padding=ft.padding.symmetric(horizontal=24, vertical=16),
        content=ft.Row(
            [
                ft.Column(
                    [
                        ft.Text("Review action items", size=20, weight=ft.FontWeight.W_700),
                        ft.Text(
                            "Approve or reject each item before pushing to Jira.",
                            size=12,
                            color=ft.Colors.GREY_600,
                        ),
                    ],
                    spacing=4,
                    expand=True,
                ),
                ft.ElevatedButton(
                    "← Back",
                    on_click=lambda _: on_navigate("results"),
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.GREY_100,
                        color=ft.Colors.GREY_800,
                    ),
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
    )

    # ── Summary bar + list (reactive) ────────────────────────────────────────
    summary_text = ft.Text("Loading...", size=12, color=ft.Colors.GREY_700)
    list_col = ft.Column(spacing=10)
    push_btn = ft.ElevatedButton(
        "Push to Jira",
        disabled=True,
        bgcolor=ft.Colors.BLUE_600,
        color=ft.Colors.WHITE,
    )
    approve_all_btn = ft.ElevatedButton(
        "Approve all",
        bgcolor=ft.Colors.GREEN_600,
        color=ft.Colors.WHITE,
    )

    def reload_items():
        from frontend.core.backend_factory import get_backend
        backend = get_backend()
        try:
            items = backend.list_review_items(meeting_id)
            review_summary = backend.get_review_summary(meeting_id)
        except Exception as exc:
            toast(f"Failed to load review items: {exc}", error=True)
            return

        state.review_items = items
        summary_text.value = (
            f"Total: {review_summary['total']}  |  "
            f"Approved: {review_summary['approved']}  |  "
            f"Needs review: {review_summary['flagged']}  |  "
            f"Pending: {review_summary['pending']}"
        )

        # Kích hoạt push button khi tất cả items đã review
        push_btn.disabled = review_summary["pending"] > 0 or review_summary["approved"] == 0
        list_col.controls.clear()

        flagged = [i for i in items if i.is_flagged and i.review_status == "draft"]
        normal = [i for i in items if not (i.is_flagged and i.review_status == "draft")]

        if flagged:
            list_col.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(vertical=4),
                    content=ft.Text(
                        f"⚠️ Needs review ({len(flagged)} items — low confidence)",
                        size=13,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.ORANGE_700,
                    ),
                )
            )
            for item in flagged:
                list_col.controls.append(
                    _build_item_card(item, page, meeting_id, reload_items, toast, highlight=True)
                )

        if normal:
            list_col.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(vertical=4),
                    content=ft.Text(
                        f"Other items ({len(normal)})",
                        size=13,
                        weight=ft.FontWeight.W_700,
                        color=ft.Colors.GREY_700,
                    ),
                )
            )
            for item in normal:
                list_col.controls.append(
                    _build_item_card(item, page, meeting_id, reload_items, toast, highlight=False)
                )

        page.update()

    def on_approve_all(_):
        def _run():
            from frontend.core.backend_factory import get_backend
            backend = get_backend()
            try:
                count = backend.approve_all_review_items(meeting_id)
                toast(f"Approved {count} items.")
                reload_items()
            except Exception as exc:
                toast(f"Error: {exc}", error=True)

        threading.Thread(target=_run, daemon=True).start()

    def on_push_jira(_):
        def _run():
            set_busy(True, "Pushing to Jira...")
            from frontend.core.backend_factory import get_backend
            backend = get_backend()
            try:
                backend.push_to_jira(None, meeting_id=meeting_id)
                toast("Jira push completed!")
                state.meeting_status = "pushed"
                reload_items()
            except Exception as exc:
                toast(f"Failed to push Jira: {exc}", error=True)
            finally:
                set_busy(False)

        threading.Thread(target=_run, daemon=True).start()

    approve_all_btn.on_click = on_approve_all
    push_btn.on_click = on_push_jira

    # Load lần đầu
    threading.Thread(target=reload_items, daemon=True).start()

    content = ft.Container(
        padding=ft.padding.symmetric(horizontal=24, vertical=8),
        expand=True,
        content=ft.Column(
            [
                # Summary bar
                ft.Container(
                    bgcolor=ft.Colors.BLUE_50,
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=16, vertical=10),
                    content=summary_text,
                ),
                ft.Container(height=8),
                # Action bar
                ft.Row(
                    [approve_all_btn, push_btn],
                    spacing=12,
                ),
                ft.Container(height=8),
                # Items list
                ft.Container(
                    expand=True,
                    content=ft.Column(
                        [list_col],
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    ),
                ),
            ],
            spacing=4,
            expand=True,
        ),
    )

    return ft.Column([header, content], spacing=0, expand=True)


def _confidence_badge(conf: float) -> ft.Container:
    """Badge màu theo confidence score."""
    if conf < 0.4:
        color = ft.Colors.RED_400
        label = f"{conf:.0%} ⚠"
    elif conf < 0.7:
        color = ft.Colors.ORANGE_400
        label = f"{conf:.0%}"
    else:
        color = ft.Colors.GREEN_500
        label = f"{conf:.0%} ✓"
    return ft.Container(
        content=ft.Text(label, size=11, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600),
        bgcolor=color,
        padding=ft.padding.symmetric(horizontal=6, vertical=2),
        border_radius=4,
    )


def _status_badge(status: str) -> ft.Container:
    color_map = {
        "approved": ft.Colors.GREEN_100,
        "rejected": ft.Colors.RED_100,
        "edited": ft.Colors.BLUE_100,
        "draft": ft.Colors.GREY_100,
    }
    text_map = {
        "approved": "✓ Approved",
        "rejected": "✗ Rejected",
        "edited": "✎ Edited",
        "draft": "⏳ Draft",
    }
    return ft.Container(
        content=ft.Text(text_map.get(status, status), size=11),
        bgcolor=color_map.get(status, ft.Colors.GREY_100),
        padding=ft.padding.symmetric(horizontal=6, vertical=2),
        border_radius=4,
    )


def _build_item_card(
    item,
    page: ft.Page,
    meeting_id: str,
    reload_items,
    toast,
    highlight: bool,
) -> ft.Container:
    """Tạo card cho một review item với edit/approve/reject."""
    item_id = str(item.id) if item.id else ""

    # Edit form (hidden by default)
    edit_summary = ft.TextField(
        value=item.edited_summary or item.summary,
        label="Summary",
        dense=True,
        multiline=True,
        min_lines=2,
    )
    edit_assignee = ft.TextField(
        value=item.edited_assignee or item.assignee or "",
        label="Assignee",
        dense=True,
    )
    edit_deadline = ft.TextField(
        value=item.edited_deadline or item.deadline or "",
        label="Deadline (YYYY-MM-DD)",
        dense=True,
    )
    edit_priority = ft.Dropdown(
        value=item.edited_priority or (
            item.priority.value if hasattr(item.priority, "value") else str(item.priority)
        ),
        label="Priority",
        dense=True,
        options=[
            ft.dropdown.Option("Critical"),
            ft.dropdown.Option("High"),
            ft.dropdown.Option("Medium"),
            ft.dropdown.Option("Low"),
        ],
    )
    edit_form = ft.Container(visible=False, content=ft.Column([
        ft.Row([edit_summary], expand=True),
        ft.Row([edit_assignee, edit_deadline, edit_priority], spacing=8),
    ], spacing=8))

    def toggle_edit(_):
        edit_form.visible = not edit_form.visible
        page.update()

    def save_edit(_):
        def _run():
            from frontend.core.backend_factory import get_backend
            backend = get_backend()
            try:
                backend.patch_review_item(
                    meeting_id,
                    item_id,
                    edited_summary=edit_summary.value or None,
                    edited_assignee=edit_assignee.value or None,
                    edited_deadline=edit_deadline.value or None,
                    edited_priority=edit_priority.value or None,
                )
                toast("Đã lưu chỉnh sửa.")
                reload_items()
            except Exception as exc:
                toast(f"Lỗi lưu: {exc}", error=True)

        threading.Thread(target=_run, daemon=True).start()

    def approve(_):
        def _run():
            from frontend.core.backend_factory import get_backend
            backend = get_backend()
            try:
                backend.approve_review_item(meeting_id, item_id)
                reload_items()
            except Exception as exc:
                toast(f"Lỗi approve: {exc}", error=True)

        threading.Thread(target=_run, daemon=True).start()

    def reject(_):
        def _run():
            from frontend.core.backend_factory import get_backend
            backend = get_backend()
            try:
                backend.reject_review_item(meeting_id, item_id)
                reload_items()
            except Exception as exc:
                toast(f"Lỗi reject: {exc}", error=True)

        threading.Thread(target=_run, daemon=True).start()

    effective_summary = item.edited_summary or item.summary
    effective_assignee = item.edited_assignee or item.assignee
    effective_deadline = item.edited_deadline or item.deadline
    _prio = item.priority
    effective_priority = _prio.value if hasattr(_prio, "value") else str(_prio)
    type_label = {"epic": "EPIC", "task": "TASK", "subtask": "SUBTASK"}.get(
        item.item_type, item.item_type.upper()
    )

    border_color = ft.Colors.ORANGE_300 if highlight else ft.Colors.GREY_200
    bgcolor = ft.Colors.ORANGE_50 if highlight else ft.Colors.WHITE

    return ft.Container(
        bgcolor=bgcolor,
        border_radius=12,
        border=ft.border.all(1, border_color),
        padding=ft.padding.all(14),
        content=ft.Column(
            [
                # Header row
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(type_label, size=10, weight=ft.FontWeight.W_700),
                            bgcolor=ft.Colors.BLUE_50,
                            padding=ft.padding.symmetric(horizontal=6, vertical=2),
                            border_radius=4,
                        ),
                        ft.Text(
                            f"[{item.item_index}]",
                            size=10,
                            color=ft.Colors.GREY_500,
                        ),
                        _confidence_badge(item.confidence),
                        _status_badge(item.review_status),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.EDIT_NOTE,
                            tooltip="Chỉnh sửa",
                            icon_size=16,
                            on_click=toggle_edit,
                        ),
                    ],
                    spacing=6,
                    alignment=ft.MainAxisAlignment.START,
                ),
                # Summary
                ft.Text(effective_summary, size=13, weight=ft.FontWeight.W_600),
                # Meta
                ft.Text(
                    (
                        f"👤 {effective_assignee or 'TBD'}  |  "
                        f"📅 {effective_deadline or 'N/A'}  |  "
                        f"🔥 {effective_priority}"
                    ),
                    size=11,
                    color=ft.Colors.GREY_700,
                ),
                # Validation notes nếu có
                    ft.Text(
                        " | ".join(item.validation_notes),
                        size=10,
                        color=ft.Colors.ORANGE_700,
                    ) if item.validation_notes else ft.Container(),
                # Edit form (toggle)
                edit_form,
                # Action buttons
                ft.Row(
                    [
                        ft.TextButton(
                            "Save edits",
                            on_click=save_edit,
                            visible=True,
                        ) if edit_form.visible else ft.Container(),
                        ft.ElevatedButton(
                            "✓ Approve",
                            on_click=approve,
                            bgcolor=ft.Colors.GREEN_100,
                            color=ft.Colors.GREEN_800,
                            disabled=item.review_status == "approved",
                        ),
                        ft.ElevatedButton(
                            "✗ Reject",
                            on_click=reject,
                            bgcolor=ft.Colors.RED_100,
                            color=ft.Colors.RED_800,
                            disabled=item.review_status == "rejected",
                        ),
                    ],
                    spacing=8,
                ),
            ],
            spacing=6,
        ),
    )
