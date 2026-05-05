# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview
Ứng dụng chuyển đổi audio trong cuộc họp thành biên bản hoàn chỉnh và action items có cấu trúc (Epic → Task → Subtask) để tích hợp tự động vào Jira. Kiến trúc client-server: backend deploy Docker, frontend đóng gói `.exe`.

## Current Tech Stack
Python 3.11 (server) / Python 3.9+ (shared) / Flet / OpenAI API (GPT-4o + Whisper API + Diarization) / PostgreSQL / Celery + Redis / Jira REST API v3 / `uv` / Pydantic / FastAPI / SQLAlchemy (async).

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
- **Desktop App (Flet)**: `frontend/` — HTTP client gọi FastAPI qua `HttpBackend`. Audio recording chạy local.
- **API Layer**: `src/api/` — FastAPI routers (meetings, transcriptions, analysis, reviews, jira, exports, settings). Health: `/api/v1/health`. Job polling: `/api/v1/jobs/{job_id}`.
- **Worker Layer**: `src/workers/` — Celery tasks xử lý pipeline nặng (transcribe, analyze, jira push). Beat schedule: cleanup mỗi 2h.
- **Service Layer**: `src/services/` — orchestration logic (analysis, transcription, jira, validation).
- **Provider Layer**: `src/providers/` — OpenAI Whisper, GPT-4o analyzer, diarize transcriber. Kế thừa ABC (`BaseAnalyzer`, `BaseTranscriber`).
- **DB Layer**: `src/db/` — SQLAlchemy async models + CRUD + Alembic migrations. Script location: `src/db/migrations/`.
- **Integration Layer**: `src/modules/` — Jira client, audio recorder, exporter, credential vault.
- **Data Contracts**: `src/schema.py` — Pydantic models: MeetingAnalysis, Epic, Task, Subtask, ReviewItem, Priority enum, ReviewStatus enum, MeetingStatus enum.
- **DI Container**: `src/core/container.py` — Lazy initialization of providers. Falls back to `MockAnalyzer` when `OPENAI_API_KEY` empty. `JiraClient` auto-stubs when Jira credentials missing. Use `get_container()` globally, `Container(settings=mock)` for tests.
- **Prompt Assets**: `src/prompts/` — prompt templates (vd: `extract_action_items.md`).

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

### CI/CD
- `.github/workflows/deploy.yml`: On push to `main` → build Docker image → push to `ghcr.io` → trigger Coolify webhook deploy.
- Docker Compose runs Alembic migration as a separate `migrate` service before API/Worker start.

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
Xem `.env.example` cho đầy đủ. Config loading qua `src/config.py` (`pydantic-settings`).

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
