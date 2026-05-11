# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Overview
Ứng dụng chuyển đổi audio trong cuộc họp thành biên bản hoàn chỉnh và action items có cấu trúc (Epic → Task → Subtask) để tích hợp tự động vào Jira. Kiến trúc hiện tại: Electron desktop app + FastAPI backend + Celery worker + Redis + Supabase.

## Current Tech Stack
- **Backend**: Python 3.11, FastAPI, Celery + Redis, Pydantic / pydantic-settings, Supabase Python client.
- **AI**: OpenAI API (GPT-4o + Whisper API + optional WhisperLiveKit diarization). Structured JSON output → Jira schema.
- **Database/Auth**: Supabase tables + Supabase Auth. Backend uses `SUPABASE_SERVICE_ROLE_KEY` through `src.db.supabase_client`.
- **Frontend**: TypeScript + React + Vite + Electron (`electron-app/`). Axios API client, Zustand store, Supabase auth. Python sidecar for audio recording.
- **Integrations**: Jira REST API v3.
- **Tooling**: `uv` package manager, Docker Compose, ffmpeg for audio normalization.

## Commands
```bash
# Package management (uv + pyproject.toml optional groups)
uv venv
source .venv/Scripts/activate         # Windows bash-style shell
uv pip install -e ".[server]"         # Backend: FastAPI + Celery + Supabase + Redis
uv pip install -e ".[dev]"            # Dev tools: pytest + flake8 + mypy
uv pip install -e ".[all]"            # Backend + dev tools

# Run server (dev)
uvicorn src.api.main:app --reload --port 8000

# Run Celery worker (dev, requires Redis)
celery -A src.workers.celery_app worker -Q default --loglevel=info

# Electron frontend
cd electron-app && npm install && npm run dev   # Dev mode
cd electron-app && npm run build                # Production desktop build
cd electron-app && npm run typecheck            # TypeScript check

# Docker backend stack: Redis + API + Worker
docker compose up --build

# Tests / Lint / Typecheck
pytest tests/ -v
flake8 . --max-line-length=100
mypy . --ignore-missing-imports
```

## Verification
Sau mỗi thay đổi logic backend: `pytest tests/ -v`. Sau thay đổi deploy/package: verify theo task spec, tối thiểu `docker compose config` và import smoke nếu được yêu cầu.

## Architecture (Client-Server)

### Layered View
- **Electron Desktop App**: `electron-app/` — React + TypeScript + Vite. Uses Supabase email/password auth and Axios for FastAPI calls. Python sidecar records audio via IPC.
- **API Layer**: `src/api/` — FastAPI routers (meetings, transcriptions, analysis, reviews, jira, exports, settings, stream). Health: `/api/v1/health`. Job polling: `/api/v1/jobs/{job_id}`. Rate limiting via `slowapi`.
- **Worker Layer**: `src/workers/` — Celery tasks for transcribe, analyze, Jira push, and cleanup. Redis is broker/result backend.
- **Service Layer**: `src/services/` — orchestration logic for analysis, transcription, Jira, validation, audio ingestion, summarization, cleanup.
- **Audio Ingestion**: `src/services/audio_ingestion_service.py` — upload validation, ffmpeg normalization to WAV 16kHz mono, video-to-audio extraction.
- **Provider Layer**: `src/providers/` — OpenAI Whisper/GPT-4o and WhisperLiveKit integrations. New providers must implement the corresponding ABC.
- **DB Layer**: `src/db/` — Supabase client and CRUD helpers. Do not add SQLAlchemy/Alembic/PostgreSQL direct-access code.
- **Integration Layer**: `src/modules/` — Jira client, audio recorder, exporter, credential vault.
- **Data Contracts**: `src/schema.py` — Pydantic models: MeetingAnalysis, Epic, Task, Subtask, ReviewItem, Priority enum, ReviewStatus enum, MeetingStatus enum.
- **DI Container**: `src/core/container.py` — Lazy initialization of providers. Falls back to `MockAnalyzer` when `OPENAI_API_KEY` is empty. `JiraClient` auto-stubs when Jira credentials are missing.
- **Design System**: `DESIGN.md` — Notion-based design tokens for frontend components.

### Data Flow
```
[Electron App] record/upload audio
  → POST /meetings/{id}/audio → [FastAPI]
    → Redis/Celery pipeline:
      1. transcribe_task → transcript segments → Supabase
      2. analyze_task → analysis result + action items → Supabase
  → Electron polls /jobs/{job_id} and/or reads Supabase data
  → User approve/edit/reject action items
  → POST /meetings/{id}/jira/push → jira_push_task → Jira + Supabase sync status
```

### Non-Obvious Patterns

**Supabase-first DB access**: Backend database operations go through `src.db.supabase_client` and CRUD helpers. There is no local PostgreSQL service or Alembic migration flow in the active runtime.

**Strategy Pattern for Providers**: `BaseAnalyzer` and `BaseTranscriber` are ABCs. New providers must implement the corresponding ABC. `Container` handles provider selection based on config.

**Validation Pipeline**: AI extraction is cross-validated with rule-based regex (`extraction_service.py` + `validation_service.py`) → confidence score → flagged items highlighted in review.

**Structured Output**: OpenAI JSON mode maps action items to Jira schema: Epic → Task → Subtask with assignee, deadline, priority.

**Electron + FastAPI split**: Electron uses Supabase SDK for auth/data paths and FastAPI for upload, jobs, AI processing, streaming, and Jira push.

### CI/CD
- `.github/workflows/deploy.yml`: mirrors source for deploy workflow.
- Docker Compose is backend-only (Redis, API, worker). Electron is built separately as a desktop app.

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

**Backend env vars**: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `OPENAI_API_KEY`, `APP_SECRET_KEY`, Redis/Celery URLs, optional Jira env vars.

**Electron-only env vars** (Vite, in `electron-app/.env`): `VITE_API_BASE_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.

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
- KHÔNG sửa files trong `.claude/` ngoài các file spec/progress của task hiện tại.
- Provider mới PHẢI kế thừa ABC + có test file riêng.
- External API calls PHẢI có error handling + retry logic.
- Prompt changes PHẢI test với ≥2 sample transcripts trước khi commit.
- KHÔNG dùng Local Whisper — chỉ OpenAI Whisper API hoặc WhisperLiveKit khi được cấu hình.
- KHÔNG dùng SQLite/PostgreSQL local — database runtime là Supabase qua `src/db/`.

## Recurring Mistakes
<!-- Thêm lỗi mới vào đây mỗi khi AI mắc lỗi lặp. Format: -->
<!-- - [Ngày] Lỗi: ... → Fix: ... -->
