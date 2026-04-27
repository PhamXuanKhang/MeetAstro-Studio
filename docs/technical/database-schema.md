# Database Schema

PostgreSQL database schema for AI Meeting Assistant.

---

## Overview

The database uses **PostgreSQL 16** with **SQLAlchemy async** + **asyncpg**. Migrations are managed by **Alembic**.

Database: `ai_meeting_db`
Connection: `POSTGRES_URL` environment variable

---

## Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    meetings     │       │   transcripts   │       │ analysis_results│
│─────────────────│       │─────────────────│       │─────────────────│
│ id (UUID, PK)   │───┐   │ id (UUID, PK)   │   ┌───│ id (UUID, PK)   │
│ title           │   │   │ meeting_id (FK) │◄──┤   │ meeting_id (FK) │
│ audio_path      │   │   │ raw_text        │   │   │ analysis_json   │
│ status          │   │   │ diarized_text   │   │   │ summary         │
│ user_id         │   │   │ language        │   │   │ overall_conf.   │
│ celery_task_id  │   │   │ char_count      │   │   │ created_at      │
│ created_at      │   └───│ created_at      │   │   └─────────────────┘
│ updated_at      │       └─────────────────┘   │
└─────────────────┘                             │   ┌─────────────────┐
        │                                       │   │  review_items   │
        │                                       │   │─────────────────│
        │                                       └───│ id (UUID, PK)   │
        │                                           │ meeting_id (FK) │
        │                                           │ item_type       │
        │                                           │ item_index      │
        │                                           │ summary         │
        │                                           │ assignee        │
        │                                           │ deadline        │
        │                                           │ priority        │
        │                                           │ context         │
        │                                           │ confidence      │
        │                                           │ is_flagged      │
        │                                           │ review_status   │
        │                                           │ edited_*        │
        │                                           │ created_at      │
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
| `audio_path` | TEXT | Yes | NULL | Path to audio file on server |
| `status` | TEXT | No | `'pending'` | Status: `pending`, `transcribing`, `transcribed`, `analyzing`, `draft`, `reviewed`, `pushed` |
| `user_id` | TEXT | No | `'default_user'` | User identifier |
| `celery_task_id` | TEXT | Yes | NULL | Active Celery task ID for polling |
| `error_message` | TEXT | Yes | NULL | Last pipeline error message |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last update timestamp |

Indexes:
- None in migration `0001_initial.py`.

### transcripts

Stores transcription results from Whisper API.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `meeting_id` | UUID | No | - | FK to `meetings.id` |
| `raw_text` | TEXT | No | - | Plain transcript text |
| `diarized_text` | TEXT | Yes | NULL | Transcript with speaker labels |
| `language` | TEXT | Yes | `'en'` | Transcription language code |
| `char_count` | INTEGER | Yes | NULL | Character count |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |

Constraints:
- FK `meeting_id` -> `meetings.id` ON DELETE CASCADE

### analysis_results

Stores GPT-4o analysis output.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `meeting_id` | UUID | No | - | FK to `meetings.id` |
| `analysis_json` | JSONB | No | - | Full `MeetingAnalysis` as JSON |
| `summary` | TEXT | Yes | NULL | Extracted summary text |
| `overall_confidence` | FLOAT | Yes | NULL | Overall confidence score (0.0-1.0) |
| `validation_metrics` | JSONB | Yes | NULL | Validation metrics from analysis pipeline |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last update timestamp |

Constraints:
- FK `meeting_id` -> `meetings.id` ON DELETE CASCADE

`analysis_json` structure:
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

### review_items

Flattened action items for human review (Human-in-the-Loop).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `meeting_id` | UUID | No | - | FK to `meetings.id` |
| `item_type` | TEXT | No | - | `'epic'`, `'task'`, or `'subtask'` |
| `item_index` | TEXT | No | - | Hierarchical index (e.g., `"0.1.2"`) |
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
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last update timestamp |

Constraints:
- FK `meeting_id` -> `meetings.id` ON DELETE CASCADE

Indexes:
- `ix_review_items_meeting_id` on `meeting_id`
- `ix_review_items_is_flagged` on `is_flagged`

### provider_configs

Stores encrypted provider credentials (Fernet encryption).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `user_id` | TEXT | No | `'default_user'` | User identifier |
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
| `user_id` | TEXT | No | - | User identifier |
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

Migrations are managed by Alembic.

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply all migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# View current state
alembic current
```

Migration files: `src/db/migrations/versions/`

---

## CRUD Operations

Async CRUD functions are in `src/db/crud/`:

### meeting_crud.py

```python
async def create_meeting(db: AsyncSession, title: str, user_id: str) -> Meeting
async def get_meeting(db: AsyncSession, meeting_id: UUID) -> Meeting | None
async def list_meetings(db: AsyncSession, user_id: str) -> list[Meeting]
async def update_meeting_status(db: AsyncSession, meeting_id: UUID, status: str) -> Meeting
async def update_meeting_audio_path(db: AsyncSession, meeting_id: UUID, path: str) -> Meeting

async def create_transcript(db: AsyncSession, meeting_id: UUID, raw_text: str, ...) -> Transcript
async def get_transcript(db: AsyncSession, meeting_id: UUID) -> Transcript | None

async def create_analysis_result(db: AsyncSession, meeting_id: UUID, ...) -> AnalysisResult
async def get_analysis_result(db: AsyncSession, meeting_id: UUID) -> AnalysisResult | None
```

### review_crud.py

```python
async def bulk_create_review_items(db: AsyncSession, items: list[dict]) -> None
async def list_review_items(db: AsyncSession, meeting_id: UUID, status: str | None) -> list[ReviewItem]
async def get_review_item(db: AsyncSession, item_id: UUID) -> ReviewItem | None
async def update_review_item(db: AsyncSession, item_id: UUID, **fields) -> ReviewItem
async def approve_review_item(db: AsyncSession, item_id: UUID) -> ReviewItem
async def reject_review_item(db: AsyncSession, item_id: UUID) -> ReviewItem
async def approve_all_review_items(db: AsyncSession, meeting_id: UUID) -> int
```

### provider_crud.py

```python
async def get_provider_config(db: AsyncSession, user_id: str, provider_name: str) -> ProviderConfig | None
async def set_provider_config(db: AsyncSession, user_id: str, provider_name: str, config: dict) -> ProviderConfig
async def list_provider_configs(db: AsyncSession, user_id: str) -> list[ProviderConfig]
async def delete_provider_config(db: AsyncSession, user_id: str, provider_name: str) -> None
```

---

## Connection

Connection is managed via `src/db/session.py`:

```python
from src.db.session import get_async_session, async_engine

# In FastAPI dependency
async def get_db():
    async with get_async_session() as session:
        yield session
```

Environment variable:
- `POSTGRES_URL`: PostgreSQL connection string
  - Format: `postgresql+asyncpg://user:password@host:port/dbname`
  - Example: `postgresql+asyncpg://ai_meeting:password@localhost:5432/ai_meeting_db`
