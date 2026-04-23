# AI Meeting Assistant

## Overview
Ứng dụng chuyển đổi audio trong cuộc họp thành biên bản hoàn chỉnh và action items có cấu trúc (Epic → Task → Subtask) để tích hợp tự động vào Jira.

## Goals
- Tự động hóa quy trình ghi biên bản và trích xuất action items.
- Đảm bảo output có cấu trúc phù hợp Jira schema để push trực tiếp.
- Hỗ trợ Human-in-the-loop review trước khi đồng bộ Jira.
- Kiến trúc client-server: backend deploy Docker, frontend đóng gói `.exe`.

## Current Tech Stack
Python 3.11 (server) / Python 3.9+ (shared) / Flet / OpenAI API (GPT-4o + Whisper API + Diarization) / PostgreSQL / Celery + Redis / Jira REST API v3 / `uv` / Pydantic / FastAPI / SQLAlchemy (async).

## Workflow (Current)

```
[Desktop App]
  ↓ record audio (local) hoặc upload file
  ↓ POST /meetings/{id}/audio → [FastAPI Server]
        ↓ Celery task: Whisper API transcribe (+ diarize option)
        ↓ Celery task: GPT-4o analyze → extract Epic/Task/Subtask
        ↓ store review_items (status=draft) → PostgreSQL
  ↓ GET /meetings/{id}/review → user rà soát, chỉnh sửa, approve
  ↓ POST /meetings/{id}/jira/push → [FastAPI Server]
        ↓ Celery task: push approved items → Jira REST API
```

## Commands
```bash
# Quản lý package qua uv + pyproject.toml optional groups
uv venv
source .venv/Scripts/activate         # Windows

uv pip install -e ".[server]"         # Backend: FastAPI + Celery + PostgreSQL
uv pip install -e ".[frontend]"       # Frontend: Flet + audio recording
uv pip install -e ".[dev]"            # Dev tools: pytest + flake8 + mypy
uv pip install -e ".[all]"            # All-in-one (local dev)

# Chạy server (dev)
uvicorn src.api.main:app --reload --port 8000

# Chạy Celery worker (dev, cần Redis running)
celery -A src.workers.celery_app worker -Q default --loglevel=info

# Docker (backend stack: PostgreSQL + Redis + API + Worker)
docker-compose up --build

# Tests / Lint / Typecheck
pytest tests/ -v
flake8 . --max-line-length=100
mypy . --ignore-missing-imports
```

## Architecture (Client-Server)

### Layered View
- **Desktop App (Flet)**: `frontend/` — HTTP client gọi FastAPI qua `HttpBackend`. Audio recording chạy local.
- **API Layer**: `src/api/` — FastAPI routers cho meetings, transcriptions, analysis, reviews, jira, exports, settings.
- **Worker Layer**: `src/workers/` — Celery tasks xử lý pipeline nặng (transcribe, analyze, jira push).
- **Service Layer**: `src/services/` — orchestration logic (analysis, transcription, jira, validation).
- **Provider Layer**: `src/providers/` — OpenAI Whisper, GPT-4o analyzer, diarize transcriber.
- **DB Layer**: `src/db/` — SQLAlchemy async models + CRUD + Alembic migrations (PostgreSQL).
- **Integration Layer**: `src/modules/` — Jira client, audio recorder, exporter, credential vault.
- **Data Contracts**: `src/schema.py` — Pydantic models: MeetingAnalysis, Epic, Task, Subtask, ReviewItem.
- **Prompt Assets**: `src/prompts/` — prompt templates (vd: `extract_action_items.md`).
- **Tests**: `tests/` — unit + integration, tất cả external calls đều mock.

### Module Map (Key Paths)
- `src/api/main.py` — FastAPI app factory, lifespan PostgreSQL init.
- `src/api/routers/` — meetings, transcriptions, analysis, reviews, jira, exports, settings.
- `src/workers/pipeline.py` — Celery pipeline: transcribe → analyze.
- `src/workers/tasks/` — transcribe_task, analyze_task, jira_push_task.
- `src/db/models.py` — ORM: Meeting, Transcript, AnalysisResult, ReviewItem, ProviderConfig.
- `src/db/crud/meeting_crud.py` — async CRUD cho Meeting + Transcript + AnalysisResult.
- `src/db/crud/review_crud.py` — async CRUD cho ReviewItem (approve/reject/bulk).
- `src/services/analysis_service.py` — GPT-4o analysis + extraction + summarization.
- `src/services/transcription_service.py` — OpenAI Whisper API + diarize.
- `src/services/jira_service.py` — orchestrate push lên Jira.
- `src/modules/jira_client.py` — Jira REST API v3 client (stub mode nếu thiếu credentials).
- `src/modules/credential_vault.py` — Fernet encryption cho provider credentials.
- `src/modules/exporter.py` — export MD/JSON/CSV từ MeetingAnalysis.
- `frontend/core/http_backend.py` — HTTP client singleton cho Flet views.
- `frontend/core/state.py` — AppState dataclass (route, transcript, analysis, review_items).
- `frontend/views/` — dashboard, new_meeting, results, review (human-in-the-loop), history, settings.

### Data Flow
1. Desktop app record audio local hoặc user upload file.
2. `POST /meetings/{id}/audio` → server lưu file, enqueue Celery pipeline.
3. `transcribe_task`: Whisper API (+ diarize) → lưu `Transcript` vào PostgreSQL.
4. `analyze_task`: GPT-4o → lưu `AnalysisResult` + flatten `ReviewItem[]` (status=draft).
5. Frontend poll `/jobs/{job_id}` → khi done, load review items.
6. User rà soát trong `review_view`: approve/edit/reject từng item.
7. `POST /meetings/{id}/jira/push` → enqueue `jira_push_task` → push approved items.

### Integration Points
- OpenAI: GPT-4o (analysis/extraction), Whisper API (transcription), diarize transcriber.
- Jira REST API v3 (Basic Auth — stub mode khi thiếu credentials).
- PostgreSQL (qua SQLAlchemy async + asyncpg).
- Redis (Celery broker + result backend).

### Config, Secrets, and Security
- Cấu hình qua `src/config.py` (`pydantic-settings` + `.env` file).
- `credential_vault.py` mã hóa provider secrets bằng Fernet (`APP_SECRET_KEY`).
- Không commit `.env` hoặc credentials. Xem `.env.example`.

### Observability and Reliability
- Logging qua `from src.config import get_logger`, không dùng `print`.
- Celery tasks có retry logic (`max_retries`, `default_retry_delay`).
- External API calls có error handling.
- FastAPI `/api/v1/health` endpoint kiểm tra DB connectivity.

### Claude Kit Best Practices (Applied)
- **Structured Outputs**: JSON mode + schema validation để giảm lỗi parse.
- **Prompt Versioning**: lưu prompt trong `src/prompts/`, dễ theo dõi diff.
- **Evaluation Hooks**: tham chiếu `docs/evaluation/` để mở rộng đánh giá.
- **Guardrails**: `validation_service` cross-validate AI extraction vs rule-based rules trước khi tạo review items.
- **Human-in-the-Loop**: `review_view` cho phép user kiểm soát trước khi push Jira.

## Key Patterns
- **Strategy Pattern**: Provider kế thừa ABC (`base_analyzer.py`, `base_transcriber.py`). Provider mới PHẢI implement ABC tương ứng.
- **Async Worker**: Celery + Redis xử lý pipeline nặng (STT + GPT-4o) để không block API thread.
- **Structured Output**: OpenAI JSON mode cho action items extraction. Output map sang Jira schema: Epic → Task → Subtask với assignee, deadline, priority.
- **Validation**: AI extraction cross-validate với rule-based regex (`validation_service`) → confidence score → flagged items nổi bật trong review.
- **State**: AppState trong `frontend/core/state.py`; persistent storage qua PostgreSQL (không dùng SQLite).
- **Security**: `credential_vault.py` mã hoá provider configs bằng Fernet trước khi lưu PostgreSQL.

## Action Items Schema (Jira integration target)
Mỗi cuộc họp extract ra cấu trúc:
- **Epic**: Chủ đề lớn / quyết định chính của cuộc họp
- **Task**: Action item cụ thể (có assignee, deadline, priority)
- **Subtask**: Bước nhỏ trong task (nếu có)
- Mỗi item cần: `summary`, `assignee`, `deadline`, `priority` (Critical/High/Medium/Low), `context` (trích dẫn từ transcript)

## Code Style
- snake_case functions/variables, PascalCase classes, UPPER_CASE constants.
- Type hints đầy đủ (Python 3.9+ style: `list[str]`, `Optional[str]`, `Union[str, int]` — không dùng `str | int` trên Python 3.9).
- Docstrings tiếng Việt, tên biến + kỹ thuật tiếng Anh.
- Logging (không print). Dùng `from src.config import get_logger`.
- Pure functions khi có thể. Không global state ngoài config.

## Environment Variables
Xem `.env.example`. Keys quan trọng:
- `OPENAI_API_KEY` — GPT-4o + Whisper API + Diarization
- `DEFAULT_TRANSCRIPTION_LANGUAGE` — ngôn ngữ mặc định (mặc định: `vi`)
- `POSTGRES_URL` — PostgreSQL connection string
- `APP_SECRET_KEY` — Fernet key cho mã hoá credential vault
- `AUDIO_*` — config audio recording (sample rate, mic/sys gain, output dir)
- `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` — Redis URLs cho Celery
- `API_BASE_URL` — URL FastAPI server mà Flet desktop kết nối (mặc định: `http://localhost:8000`)
- `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY` — Jira integration (Basic Auth)
- `CONFIDENCE_LOW_THRESHOLD`, `CONFIDENCE_HIGH_THRESHOLD` — ngưỡng flag review items

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

## Verification
Sau mỗi thay đổi: `flake8 . --max-line-length=100 && mypy . --ignore-missing-imports && pytest tests/ -v`

## Recurring Mistakes
<!-- Thêm lỗi mới vào đây mỗi khi AI mắc lỗi lặp. Format: -->
<!-- - [Ngày] Lỗi: ... → Fix: ... -->
