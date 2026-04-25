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
| `id` | UUID | No | `uuid_generate_v4()` | Primary key |
| `title` | VARCHAR(255) | No | - | Meeting title |
| `audio_path` | VARCHAR(500) | Yes | NULL | Path to audio file on server |
| `status` | VARCHAR(50) | No | `'pending'` | Status: `pending`, `transcribing`, `transcribed`, `analyzing`, `draft`, `reviewed`, `pushed` |
| `user_id` | VARCHAR(100) | No | `'default_user'` | User identifier |
| `celery_task_id` | VARCHAR(100) | Yes | NULL | Active Celery task ID for polling |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last update timestamp |

Indexes:
- `ix_meetings_user_id` on `user_id`
- `ix_meetings_status` on `status`

### transcripts

Stores transcription results from Whisper API.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `uuid_generate_v4()` | Primary key |
| `meeting_id` | UUID | No | - | FK to `meetings.id` |
| `raw_text` | TEXT | No | - | Plain transcript text |
| `diarized_text` | TEXT | Yes | NULL | Transcript with speaker labels |
| `language` | VARCHAR(10) | No | `'vi'` | Transcription language code |
| `char_count` | INTEGER | No | 0 | Character count |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |

Constraints:
- FK `meeting_id` -> `meetings.id` ON DELETE CASCADE

### analysis_results

Stores GPT-4o analysis output.

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `uuid_generate_v4()` | Primary key |
| `meeting_id` | UUID | No | - | FK to `meetings.id` |
| `analysis_json` | JSONB | No | - | Full `MeetingAnalysis` as JSON |
| `summary` | TEXT | Yes | NULL | Extracted summary text |
| `overall_confidence` | FLOAT | No | 0.0 | Overall confidence score (0.0-1.0) |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |

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
| `id` | UUID | No | `uuid_generate_v4()` | Primary key |
| `meeting_id` | UUID | No | - | FK to `meetings.id` |
| `item_type` | VARCHAR(20) | No | - | `'epic'`, `'task'`, or `'subtask'` |
| `item_index` | VARCHAR(50) | No | - | Hierarchical index (e.g., `"0.1.2"`) |
| `summary` | VARCHAR(500) | No | - | AI-generated summary |
| `assignee` | VARCHAR(100) | Yes | NULL | AI-extracted assignee |
| `deadline` | DATE | Yes | NULL | AI-extracted deadline |
| `priority` | VARCHAR(20) | Yes | NULL | `Critical`, `High`, `Medium`, `Low` |
| `context` | TEXT | Yes | NULL | Transcript excerpt |
| `confidence` | FLOAT | No | 0.0 | Validation confidence score |
| `is_flagged` | BOOLEAN | No | FALSE | Flagged for user attention |
| `review_status` | VARCHAR(20) | No | `'draft'` | `draft`, `approved`, `rejected` |
| `edited_summary` | VARCHAR(500) | Yes | NULL | User-edited summary |
| `edited_assignee` | VARCHAR(100) | Yes | NULL | User-edited assignee |
| `edited_deadline` | DATE | Yes | NULL | User-edited deadline |
| `edited_priority` | VARCHAR(20) | Yes | NULL | User-edited priority |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last update timestamp |

Constraints:
- FK `meeting_id` -> `meetings.id` ON DELETE CASCADE

Indexes:
- `ix_review_items_meeting_id` on `meeting_id`
- `ix_review_items_review_status` on `review_status`

### provider_configs

Stores encrypted provider credentials (Fernet encryption).

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `uuid_generate_v4()` | Primary key |
| `user_id` | VARCHAR(100) | No | `'default_user'` | User identifier |
| `provider_name` | VARCHAR(100) | No | - | Provider name (e.g., `'jira'`, `'openai'`) |
| `config_json` | TEXT | No | - | **Fernet-encrypted** JSON config |
| `active` | BOOLEAN | No | TRUE | Whether config is active |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last update timestamp |

Constraints:
- UNIQUE (`user_id`, `provider_name`)

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
