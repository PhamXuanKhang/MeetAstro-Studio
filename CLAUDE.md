# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview
Ứng dụng chuyển đổi audio trong cuộc họp thành biên bản hoàn chỉnh và action items có cấu trúc (Epic → Task → Subtask) để tích hợp tự động vào Jira. Kiến trúc client-server: backend deploy Docker, frontend đóng gói `.exe`.

## Current Tech Stack
- **Backend**: Python 3.11, FastAPI, SQLAlchemy (async + asyncpg), Celery + Redis, Alembic, Pydantic / pydantic-settings.
- **AI**: OpenAI API (GPT-4o + Whisper API + Diarization). Structured JSON output → Jira schema.
- **Database**: PostgreSQL 16. Quota/plan system (UserPlan, UsageRecord, QuotaLimit models).
- **Flet Frontend**: Python 3.9+, Flet desktop app (`frontend/`). HTTP-only client via `httpx`.
- **Electron Frontend**: TypeScript + React + Vite + Electron (`electron-app/`). Axios API client, Zustand store, Supabase auth. Python sidecar for audio recording.
- **Integrations**: Jira REST API v3, Supabase Auth (Electron only, backend enforcement WIP).
- **Tooling**: `uv` package manager, Docker Compose, ffmpeg (audio normalization).

## Commands
```bash
# Package management (uv + pyproject.toml optional groups)
uv venv
source .venv/Scripts/activate         # Windows
uv pip install -e ".[server]"         # Backend: FastAPI + Celery + PostgreSQL
uv pip install -e ".[frontend]"       # Frontend: Flet + audio recording
uv pip install -e ".[dev]"            # Dev tools: pytest + flake8 + mypy
uv pip install -e ".[all]"            # All-in-one (local dev)

# Run server (dev)
uvicorn src.api.main:app --reload --port 8000

# Run Celery worker (dev, requires Redis)
celery -A src.workers.celery_app worker -Q default --loglevel=info

# Run Flet desktop app
python -m frontend.main

# Electron frontend (separate from Flet)
cd electron-app && npm install && npm run dev   # Dev mode (Vite + Electron)
cd electron-app && npm run build                # Production build (.exe via electron-builder)
cd electron-app && npm run lint                  # ESLint
cd electron-app && npm run typecheck             # TypeScript check

# Docker (full backend stack: PostgreSQL + Redis + Alembic migrate + API + Worker)
docker-compose up --build

# Database migrations (Alembic)
alembic upgrade head                          # Apply all pending migrations
alembic revision --autogenerate -m "desc"     # Generate new migration
alembic downgrade -1                          # Rollback last migration

# Tests / Lint / Typecheck
pytest tests/ -v                              # All tests
pytest tests/test_schema.py -v                # Single file
pytest tests/test_schema.py::TestPriority -v  # Single class
pytest tests/test_schema.py::TestPriority::test_values -v  # Single test
flake8 . --max-line-length=100
mypy . --ignore-missing-imports
```

## Verification
Sau mỗi thay đổi: `flake8 . --max-line-length=100 && mypy . --ignore-missing-imports && pytest tests/ -v`

## Architecture (Client-Server)

### Layered View
- **Flet Desktop App**: `frontend/` — HTTP-only client (`HttpBackend` wraps `httpx.Client`, sync). Audio recording chạy local via `src.services.recording_service`. State: in-memory `AppState` dataclass.
- **Electron Desktop App**: `electron-app/` — React + TypeScript + Vite. Axios API client mirrors `HttpBackend`. Zustand store mirrors `AppState`. Supabase email/password auth. Python sidecar cho audio recording via IPC.
- **API Layer**: `src/api/` — FastAPI routers (meetings, transcriptions, analysis, reviews, jira, exports, settings). Health: `/api/v1/health`. Job polling: `/api/v1/jobs/{job_id}`. Rate limiting via `slowapi`. No auth middleware currently enforced.
- **Worker Layer**: `src/workers/` — Celery tasks xử lý pipeline nặng (transcribe, analyze, jira push). `pipeline.py` orchestrates sequentially within one task. Beat schedule: cleanup mỗi 2h.
- **Service Layer**: `src/services/` — orchestration logic (analysis, transcription, jira, validation, audio ingestion, summarization, cleanup).
- **Audio Ingestion**: `src/services/audio_ingestion_service.py` — upload validation, ffmpeg normalization (→ WAV 16kHz mono), video-to-audio extraction. Supports mp3/wav/m4a/ogg + mp4/mkv/webm. Canonical storage under `AUDIO_STORAGE_BASE`.
- **Provider Layer**: `src/providers/` — OpenAI Whisper, GPT-4o analyzer, diarize transcriber. Kế thừa ABC (`BaseAnalyzer`, `BaseTranscriber`).
- **DB Layer**: `src/db/` — SQLAlchemy async models (Meeting, Transcript, AnalysisResult, ReviewItem, ProviderConfig, UserPlan, UsageRecord, QuotaLimit) + CRUD + Alembic migrations. Script location: `src/db/migrations/`.
- **Integration Layer**: `src/modules/` — Jira client, audio recorder, exporter, credential vault.
- **Data Contracts**: `src/schema.py` — Pydantic models: MeetingAnalysis, Epic, Task, Subtask, ReviewItem, Priority enum, ReviewStatus enum, MeetingStatus enum.
- **DI Container**: `src/core/container.py` — Lazy initialization of providers. Falls back to `MockAnalyzer` when `OPENAI_API_KEY` empty. `JiraClient` auto-stubs when Jira credentials missing. Use `get_container()` globally, `Container(settings=mock)` for tests.
- **Prompt Assets**: `src/prompts/` — prompt templates (vd: `extract_action_items.md`).
- **Design System**: `DESIGN.md` — Notion-based design tokens (colors, typography, spacing, components). Tham chiếu khi build/style frontend components.

### Data Flow
```
[Desktop App] record/upload audio
  → POST /meetings/{id}/audio → [FastAPI]
    → Celery pipeline (src/workers/pipeline.py):
      1. transcribe_task: Whisper API (+diarize) → Transcript → PostgreSQL
      2. analyze_task: GPT-4o → AnalysisResult + ReviewItem[] (status=draft) → PostgreSQL
  → Frontend poll /jobs/{job_id} → load review items
  → User approve/edit/reject in review_view
  → POST /meetings/{id}/jira/push → jira_push_task → push approved items → Jira
```

### Non-Obvious Patterns

**Dual Engine (API vs Worker)**: `src/db/session.py` maintains two separate SQLAlchemy engines. The API engine uses connection pooling (`init_engine()`). The Celery worker engine uses `NullPool` (`get_session_factory()`) because each Celery task runs in its own `asyncio.run()` — reusing pooled connections across event loops causes asyncpg errors.

**Strategy Pattern for Providers**: `BaseAnalyzer` and `BaseTranscriber` are ABCs. New providers MUST implement the corresponding ABC. `Container` handles provider selection based on config.

**Validation Pipeline**: AI extraction (GPT-4o) is cross-validated with rule-based regex (`extraction_service.py` + `validation_service.py`) → confidence score → flagged items highlighted in review.

**Structured Output**: OpenAI JSON mode for action items extraction. Output maps to Jira schema: Epic → Task → Subtask with assignee, deadline, priority.

**Two Frontends, One API**: Both Flet and Electron call the same FastAPI `/api/v1` endpoints. Flet uses sync `httpx`, Electron uses `axios`. Audio recording is local in both (Flet: Python in-process, Electron: Python sidecar via IPC/JSON-lines).

**Supabase Auth (In-Progress)**: Electron has Supabase email/password auth + session tracking. DB model uses UUID `Meeting.user_id` (zero UUID fallback for local/dev, migration 0003). Backend does NOT currently enforce JWT auth — no middleware or `Authorization` header injection in either frontend's API client. Supabase env vars are in `.env` but not declared in `src/config.py`.

**Quota System**: `UserPlan` / `UsageRecord` / `QuotaLimit` models support plan-based usage limits. Migration 0002.

### CI/CD
- `.github/workflows/deploy.yml`: On push to `main` → build Docker image → push to `ghcr.io` → trigger Coolify webhook deploy. No test/lint CI workflow — only deployment.
- Docker Compose runs Alembic migration as a separate `migrate` service before API/Worker start.
- Docker Compose is backend-only (Postgres, Redis, migrate, API, worker). Does NOT run Flet or Electron frontend.

## Action Items Schema (Jira integration target)
- **Epic**: Chủ đề lớn / quyết định chính
- **Task**: Action item cụ thể (assignee, deadline, priority)
- **Subtask**: Bước nhỏ trong task
- Mỗi item cần: `summary`, `assignee`, `deadline`, `priority` (Critical/High/Medium/Low), `context` (trích dẫn từ transcript)

## Code Style
- snake_case functions/variables, PascalCase classes, UPPER_CASE constants.
- Type hints đầy đủ (Python 3.9+ style: `list[str]`, `Optional[str]`, `Union[str, int]` — không dùng `str | int` trên Python 3.9).
- Docstrings tiếng Việt, tên biến + kỹ thuật tiếng Anh.
- Logging (không print). Dùng `from src.config import get_logger`.
- Pure functions khi có thể. Không global state ngoài config.

## Environment Variables
Config loading qua `src/config.py` (`pydantic-settings`, `@lru_cache` singleton). Xem `.env.example` cho đầy đủ.

**Electron-only env vars** (Vite, in `electron-app/.env`): `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.

**Supabase env vars** (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`) are in `.env` but NOT yet declared in `src/config.py` — backend doesn't read them.

## Agent Behavior

**Think Before Coding** — Đọc kĩ `docs/` trước khi implement. Nêu rõ assumptions. Nếu có nhiều cách, trình bày tất cả. Nếu có hướng đơn giản hơn, nói ra.

**Simplicity First** — Code tối thiểu giải quyết đúng vấn đề. Không over-engineer.

**Surgical Changes** — Chỉ chạm vào những gì cần thiết. Không refactor code lân cận không liên quan.

**Goal-Driven Execution** — Với task nhiều bước, nêu kế hoạch:
```text
1. [Bước] → verify: [kiểm tra]
2. [Bước] → verify: [kiểm tra]
```

## Rules
- LUÔN chạy `pytest tests/ -v` sau khi sửa logic trong `providers/` hoặc `services/`.
- LUÔN verify structured output match Jira schema (Epic/Task/Subtask) sau khi sửa prompts hoặc analyzer.
- KHÔNG commit `.env`, API keys, hoặc credentials.
- KHÔNG sửa files trong `.claude/` mà không hỏi trước.
- Provider mới PHẢI kế thừa ABC + có test file riêng.
- External API calls PHẢI có error handling + retry logic.
- Prompt changes PHẢI test với ≥2 sample transcripts trước khi commit.
- KHÔNG dùng Local Whisper — chỉ OpenAI Whisper API.
- KHÔNG dùng SQLite — database duy nhất là PostgreSQL qua `src/db/`.

## Recurring Mistakes
<!-- Thêm lỗi mới vào đây mỗi khi AI mắc lỗi lặp. Format: -->
<!-- - [Ngày] Lỗi: ... → Fix: ... -->
