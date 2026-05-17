"""Seed demo Jira tasks and mirror them into Supabase action_items.

Usage:
    python scripts/seed_demo_jira_tasks.py
    python scripts/seed_demo_jira_tasks.py --user-id <supabase-user-uuid>
    python scripts/seed_demo_jira_tasks.py --dry-run

The status-update feature matches existing tasks from Supabase, not directly
from Jira. This script therefore creates Jira issues first, then mirrors them
as synced action_items under a seed meeting owned by the target user.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DEMO_TASKS = [
    {
        "title": "Sửa lỗi đăng nhập bằng tài khoản Google",
        "description": "Khắc phục lỗi người dùng không thể đăng nhập bằng tài khoản Google.",
        "assignee": "Bình",
        "priority": "Medium",
        "work_status": "todo",
    },
    {
        "title": "Thiết kế giao diện màn hình báo cáo",
        "description": "Thiết kế giao diện màn hình báo cáo để người dùng theo dõi số liệu chính.",
        "assignee": "Bình",
        "priority": "Medium",
        "work_status": "todo",
    },
    {
        "title": "Cấu hình phân quyền bảo mật Supabase",
        "description": "Cấu hình phân quyền bảo mật Supabase để kiểm soát quyền truy cập dữ liệu.",
        "assignee": "Bình",
        "priority": "High",
        "work_status": "todo",
    },
]


def env(name: str, *, required: bool = True) -> str:
    value = (os.getenv(name) or "").strip().strip('"').strip("'")
    if required and not value:
        raise SystemExit(f"Missing required env: {name}")
    return value


def jira_adf(text: str) -> dict[str, Any]:
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text or " "}],
            }
        ],
    }


def create_jira_task(client: httpx.Client, task: dict[str, str]) -> dict[str, str]:
    base_url = env("JIRA_BASE_URL").rstrip("/")
    project_key = env("JIRA_PROJECT_KEY")
    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": task["title"],
            "description": jira_adf(task["description"]),
            "issuetype": {"name": "Task"},
            "priority": {"name": task["priority"]},
            "labels": ["ai-meeting-demo", "status-update-demo"],
        }
    }
    response = client.post(f"{base_url}/rest/api/3/issue", json=payload)
    if response.status_code >= 400:
        raise RuntimeError(f"Jira create failed for '{task['title']}': {response.status_code} {response.text[:500]}")
    data = response.json()
    key = data["key"]
    return {
        "key": key,
        "url": f"{base_url}/browse/{key}",
    }


def supabase_headers() -> dict[str, str]:
    service_key = env("SUPABASE_SERVICE_ROLE_KEY")
    return {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def supabase_url(path: str) -> str:
    return f"{env('SUPABASE_URL').rstrip('/')}/rest/v1/{path.lstrip('/')}"


def get_latest_user_id(client: httpx.Client) -> str | None:
    response = client.get(
        supabase_url("meetings?select=user_id&order=updated_at.desc&limit=1"),
        headers=supabase_headers(),
    )
    response.raise_for_status()
    data = response.json()
    if not data:
        return None
    return data[0].get("user_id")


def create_seed_meeting(client: httpx.Client, user_id: str) -> dict[str, Any]:
    title = "Demo existing Jira tasks - status updates"
    payload = {
        "user_id": user_id,
        "title": title,
        "status": "draft",
        "storage_provider": "local",
    }
    response = client.post(
        supabase_url("meetings"),
        headers=supabase_headers(),
        json=payload,
    )
    response.raise_for_status()
    return response.json()[0]


def create_action_items(
    client: httpx.Client,
    *,
    meeting_id: str,
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    now = datetime.now(timezone.utc).isoformat()
    for task in tasks:
        rows.append({
            "meeting_id": meeting_id,
            "parent_id": None,
            "item_type": "task",
            "title": task["title"],
            "description": task["description"],
            "context": task["description"],
            "assignee": task["assignee"],
            "deadline": None,
            "priority": task["priority"].lower(),
            "confidence_score": 1.0,
            "review_status": "approved",
            "is_selected": True,
            "sync_status": "synced",
            "sync_error": None,
            "jira_issue_key": task["jira_issue_key"],
            "jira_issue_url": task["jira_issue_url"],
            "work_status": task["work_status"],
            "work_status_note": "Seeded demo task for status-update testing.",
            "work_status_updated_at": now,
        })

    response = client.post(
        supabase_url("action_items"),
        headers=supabase_headers(),
        json=rows,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo Jira + Supabase tasks for status-update testing.")
    parser.add_argument("--user-id", default="", help="Supabase user_id owner. Defaults to latest meetings.user_id.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned tasks without creating Jira/Supabase rows.")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env", override=True)

    print("Demo tasks:")
    for task in DEMO_TASKS:
        print(f"- {task['title']} [{task['work_status']}]")

    if args.dry_run:
        return

    with httpx.Client(timeout=20.0) as client:
        jira_client = httpx.Client(
            timeout=20.0,
            auth=(env("JIRA_EMAIL"), env("JIRA_API_TOKEN")),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        try:
            seeded_tasks = []
            for task in DEMO_TASKS:
                issue = create_jira_task(jira_client, task)
                seeded_tasks.append({
                    **task,
                    "jira_issue_key": issue["key"],
                    "jira_issue_url": issue["url"],
                })
                print(f"Created Jira issue {issue['key']}: {task['title']}")
        finally:
            jira_client.close()

        user_id = args.user_id.strip() or get_latest_user_id(client)
        if not user_id:
            raise SystemExit("Cannot infer user_id. Pass --user-id <supabase-user-uuid>.")

        meeting = create_seed_meeting(client, user_id)
        rows = create_action_items(client, meeting_id=meeting["id"], tasks=seeded_tasks)

    print("")
    print(f"Seed meeting: {meeting['id']}")
    print(f"Mirrored Supabase action_items: {len(rows)}")
    print("Done. Restart API/worker if needed, then record/upload the Vietnamese demo meeting.")


if __name__ == "__main__":
    main()
