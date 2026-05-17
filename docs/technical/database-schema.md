# Database Schema

Supabase table schema reference for AI Meeting Assistant.

---

## Overview

The active runtime uses **Supabase** with the **Supabase SDK** for backend access.

Database: Supabase project tables
Connection: `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` environment variables

Supabase ownership/RLS foundation is documented in
[`supabase-schema.md`](supabase-schema.md). Revision `0003` changes user-owned
rows to `user_id uuid references auth.users(id)`, enables RLS, and adds
foundation tables for Jira configs, AI jobs, Jira push records, audit logs, and
direct per-user usage ownership.

---

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────────┐       ┌─────────────────┐
│    meetings     │       │ transcript_segments │       │ analysis_results │
│─────────────────│       │─────────────────────│       │─────────────────│
│ id (UUID, PK)   │───┐   │ id (UUID, PK)       │   ┌───│ id (UUID, PK)   │
│ title           │   │   │ meeting_id (FK)     │◄──┤   │ meeting_id (FK) │
│ audio_path      │   │   │ speaker             │   │   │ raw_response    │
│ status          │   │   │ start_time          │   │   │ summary         │
│ user_id         │   │   │ end_time            │   │   │ overall_conf.   │
│ celery_task_id  │   │   │ content             │   │   └─────────────────┘
│ created_at      │   └───│ created_at          │   │
│ updated_at      │       └─────────────────────┘   │
└─────────────────┘                             │   ┌─────────────────┐
        │                                       │   │  action_items   │
        │                                       │   │─────────────────│
        │                                       └───│ id (UUID, PK)   │
        │                                           │ meeting_id (FK) │
        │                                           │ item_type       │
        │                                           │ parent_id       │
        │                                           │ summary         │
        │                                           │ assignee        │
        │                                           │ deadline        │
        │                                           │ priority        │
        │                                           │ context         │
        │                                           │ confidence      │
        │                                           │ review_status   │
        │                                           │ is_flagged      │
        │                                           │ jira_issue_key  │
        │                                           └─────────────────┘
        │
        │
┌───────────────────┐
│ provider_configs  │
│───────────────────│
│ id (UUID, PK)     │
│ user_id           │
│ provider_name     │
│ config_json (enc) │
│ active            │
│ created_at        │
│ updated_at        │
└───────────────────┘
```

---

## Tables

### meetings

Core table storing meeting metadata.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `title` | TEXT | No | - | Meeting title |
| `audio_storage_path` | TEXT | Yes | NULL | file:// URI of audio on user's machine |
| `audio_duration_seconds` | INTEGER | Yes | NULL | Duration of audio |
| `status` | TEXT | No | `'pending'` | Status: `pending`, `transcribing`, `transcribed`, `analyzing`, `draft`, `reviewed`, `pushed` |
| `user_id` | UUID | No | - | FK to `auth.users(id)` |
| `celery_task_id` | TEXT | Yes | NULL | Active Celery task ID for polling |
| `error_message` | TEXT | Yes | NULL | Last pipeline error message |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last update timestamp |

### transcript_segments

Stores transcription results from Whisper API.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `meeting_id` | UUID | No | - | FK to `meetings.id` |
| `speaker` | TEXT | Yes | NULL | Speaker label (e.g., "Speaker 1") |
| `start_time` | FLOAT | Yes | NULL | Start time in seconds |
| `end_time` | FLOAT | Yes | NULL | End time in seconds |
| `content` | TEXT | No | - | Transcript text for this segment |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |

Constraints:
- FK `meeting_id` -> `meetings.id` ON DELETE CASCADE

### analysis_results

Stores GPT-4o analysis output.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `meeting_id` | UUID | No | - | FK to `meetings.id` |
| `raw_response` | JSONB | No | - | Full `MeetingAnalysis` as JSON |
| `summary` | TEXT | Yes | NULL | Extracted summary text |
| `overall_confidence` | FLOAT | Yes | NULL | Overall confidence score (0.0-1.0) |
| `validation_metrics` | JSONB | Yes | NULL | Validation metrics from analysis pipeline |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last update timestamp |

Constraints:
- FK `meeting_id` -> `meetings.id` ON DELETE CASCADE

`raw_response` structure:
```json
{
  "summary": "...",
  "epics": [
    {
      "summary": "...",
      "description": "...",
      "tasks": [
        {
          "summary": "...",
          "assignee": "...",
          "deadline": "YYYY-MM-DD",
          "priority": "High",
          "context": "...",
          "subtasks": [...]
        }
      ]
    }
  ],
  "key_decisions": ["..."],
  "discussion_points": ["..."],
  "parking_lot": ["..."]
}
```

### action_items

Flattened action items for human review (Human-in-the-Loop).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `meeting_id` | UUID | No | - | FK to `meetings.id` |
| `item_type` | TEXT | No | - | `'epic'`, `'task'`, or `'subtask'` |
| `parent_id` | UUID | Yes | NULL | FK to parent action_item (for Task/Subtask hierarchy) |
| `summary` | TEXT | No | - | AI-generated summary |
| `assignee` | TEXT | Yes | NULL | AI-extracted assignee |
| `deadline` | TEXT | Yes | NULL | AI-extracted deadline |
| `priority` | TEXT | Yes | NULL | `Critical`, `High`, `Medium`, `Low` |
| `context` | TEXT | Yes | NULL | Transcript excerpt |
| `confidence` | FLOAT | No | 0.0 | Validation confidence score |
| `is_flagged` | BOOLEAN | No | FALSE | Flagged for user attention |
| `review_status` | TEXT | No | `'draft'` | `draft`, `approved`, `rejected` |
| `edited_summary` | TEXT | Yes | NULL | User-edited summary |
| `edited_assignee` | TEXT | Yes | NULL | User-edited assignee |
| `edited_deadline` | TEXT | Yes | NULL | User-edited deadline |
| `edited_priority` | TEXT | Yes | NULL | User-edited priority |
| `validation_notes` | JSONB | No | `[]` | Reasons for confidence/flagging decisions |
| `jira_issue_key` | TEXT | Yes | NULL | Jira issue key if pushed |
| `jira_issue_url` | TEXT | Yes | NULL | Jira issue URL if pushed |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last update timestamp |

Constraints:
- FK `meeting_id` -> `meetings.id` ON DELETE CASCADE
- FK `parent_id` -> `action_items.id` ON DELETE SET NULL

Indexes:
- `ix_action_items_meeting_id` on `meeting_id`
- `ix_action_items_is_flagged` on `is_flagged`

### provider_configs

Stores encrypted provider credentials (Fernet encryption).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `user_id` | UUID | No | - | FK to `auth.users(id)` |
| `provider_name` | TEXT | No | - | Provider name (e.g., `'jira'`, `'openai'`) |
| `config_json` | TEXT | No | - | **Fernet-encrypted** JSON config |
| `active` | BOOLEAN | No | TRUE | Whether config is active |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last update timestamp |

Constraints:
- UNIQUE (`user_id`, `provider_name`)

### user_plans

Stores the current quota plan for each user.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `user_id` | UUID | No | - | FK to `auth.users(id)` |
| `plan_type` | TEXT | No | `'free'` | Plan type: `free`, `basic`, `pro`, `enterprise` |
| `plan_started_at` | TIMESTAMPTZ | No | `NOW()` | Start timestamp |
| `plan_expires_at` | TIMESTAMPTZ | Yes | NULL | Expiration timestamp |
| `is_active` | BOOLEAN | Yes | TRUE | Whether plan is active |
| `extra_data` | JSONB | Yes | NULL | Provider-specific or future metadata |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last update timestamp |

Constraints:
- UNIQUE (`user_id`)

Indexes:
- `ix_user_plans_user_id` on `user_id`

### usage_records

Tracks daily/monthly usage for quota enforcement.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `user_plan_id` | UUID | No | - | FK to `user_plans.id` |
| `usage_type` | TEXT | No | - | Usage type, e.g. `transcription_tokens`, `analysis_tokens`, `jira_pushes`, `meetings` |
| `usage_count` | BIGINT | No | 0 | Count for this usage period |
| `period_start` | TIMESTAMPTZ | No | - | Period start |
| `period_end` | TIMESTAMPTZ | No | - | Period end |
| `extra_data` | JSONB | Yes | NULL | Additional usage metadata |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last update timestamp |

Constraints:
- FK `user_plan_id` -> `user_plans.id` ON DELETE CASCADE
- UNIQUE (`user_plan_id`, `usage_type`, `period_start`)

Indexes:
- `ix_usage_user_type_period` on (`user_plan_id`, `usage_type`, `period_start`)

### quota_limits

Defines maximum usage for each plan and period.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `plan_type` | TEXT | No | - | Plan type |
| `limit_type` | TEXT | No | - | Usage type this limit applies to |
| `limit_value` | BIGINT | No | - | Maximum allowed usage |
| `period_type` | TEXT | No | `'monthly'` | Period type, e.g. `daily`, `monthly` |
| `is_active` | BOOLEAN | Yes | TRUE | Whether limit is active |
| `description` | TEXT | Yes | NULL | Human-readable description |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last update timestamp |

Constraints:
- UNIQUE (`plan_type`, `limit_type`, `period_type`)

Indexes:
- `ix_quota_limits_plan_type` on `plan_type`

---

## Migrations

The active submit runtime uses Supabase project tables. Historical Alembic notes are legacy/prototype context and are not part of the current local submit workflow.

Migration files: `src/db/migrations/versions/`

---

## CRUD Operations

Async CRUD functions are in `src/db/crud/`:

### meeting_crud.py

```python
def create_meeting(title: str, user_id: str) -> dict
def get_meeting(meeting_id: str) -> dict | None
def list_meetings(user_id: str, status: str | None, page: int, page_size: int) -> tuple[list[dict], int]
def update_meeting(meeting_id: str, **fields) -> dict
def update_meeting_status(meeting_id: str, status: str) -> dict
def delete_meeting(meeting_id: str) -> bool

def create_transcript_segment(meeting_id: str, speaker: str | None, start_time: float | None, end_time: float | None, content: str) -> dict
def get_transcript_segments(meeting_id: str) -> list[dict]

def create_analysis_result(meeting_id: str, raw_response: dict, summary: str | None, overall_confidence: float | None) -> dict
def get_analysis_result(meeting_id: str) -> dict | None
```

### review_crud.py

```python
def create_action_item(meeting_id: str, item_type: str, **fields) -> dict
def bulk_create_action_items(items: list[dict]) -> list[dict]
def list_action_items(meeting_id: str, status: str | None) -> list[dict]
def get_action_item(item_id: str) -> dict | None
def update_action_item(item_id: str, **fields) -> dict
def approve_action_item(item_id: str) -> dict
def reject_action_item(item_id: str) -> dict
def approve_all_action_items(meeting_id: str) -> int
```

### provider_crud.py

```python
def get_provider_config(user_id: str, provider_name: str) -> dict | None
def set_provider_config(provider_name: str, config: dict, user_id: str) -> dict
def list_provider_configs(user_id: str) -> list[str]
def delete_provider_config(provider_name: str, user_id: str) -> bool
```

---

## Connection

Connection is managed via `src/db/supabase_client.py`:

```python
from src.db.supabase_client import get_supabase_client

# Get Supabase client (SERVICE_ROLE_KEY)
client = get_supabase_client()

# Insert
client.table("meetings").insert(data).execute()

# Query
client.table("meetings").select("*").eq("user_id", user_id).execute()
```

Environment variables:
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Backend database access key
