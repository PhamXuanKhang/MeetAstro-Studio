# Agent Guidelines — AI Meeting Assistant

> Đây là tài liệu hướng dẫn cho AI coding agents (Claude Code, Cursor, Copilot, Codex, Gemini, v.v.).
> Nội dung được đồng bộ từ `CLAUDE.md`. Khi hai file mâu thuẫn, `CLAUDE.md` là source of truth.

---

## 1. Project Overview

Ứng dụng chuyển đổi audio cuộc họp thành biên bản và action items (Epic → Task → Subtask) để tích hợp tự động vào Jira.

**Kiến trúc**: FastAPI backend (REST server) + Flet desktop app (HTTP client).

- **Backend**: FastAPI + Celery + Redis + PostgreSQL — chạy trong Docker.
- **Frontend**: Flet desktop app — đóng gói `.exe`, giao tiếp qua HTTP.
- **AI**: OpenAI GPT-4o (analysis) + Whisper API + Diarization (transcription).

---

## 2. Workflow của Pipeline

```
Audio (upload/record) → Celery task: Whisper API transcribe (+ diarize option)
→ Celery task: GPT-4o analysis → Review items (Human-in-the-loop)
→ User approve/edit → Celery task: push approved items lên Jira
```

---

## 3. Architecture Map (Key Paths)

| Layer | Path | Vai trò |
|---|---|---|
| API entrypoint | `src/api/main.py` | FastAPI app factory |
| API routers | `src/api/routers/` | meetings, transcriptions, analysis, reviews, jira, exports, settings |
| Celery workers | `src/workers/` | transcribe_task, analyze_task, jira_push_task, pipeline |
| Services | `src/services/` | analysis, transcription, recording, jira, validation, extraction, summarization |
| Providers | `src/providers/` | openai_analyzer, openai_transcriber, openai_diarize_transcriber |
| DB models | `src/db/models.py` | Meeting, Transcript, AnalysisResult, ReviewItem, ProviderConfig |
| DB CRUD | `src/db/crud/` | meeting_crud, review_crud, provider_crud |
| Schema | `src/schema.py` | Pydantic models: MeetingAnalysis, Epic, Task, Subtask, ReviewItem |
| Frontend core | `frontend/core/` | http_backend.py (HTTP client), state.py (AppState) |
| Frontend views | `frontend/views/` | dashboard, new_meeting, results, review, history, settings |

---

## 4. Rules Bắt Buộc

- LUÔN chạy `pytest tests/ -v` sau khi sửa logic trong `providers/` hoặc `services/`.
- LUÔN verify structured output match Jira schema (Epic/Task/Subtask) sau khi sửa prompts.
- KHÔNG commit `.env`, API keys, hoặc credentials.
- KHÔNG sửa files trong `.claude/` mà không hỏi trước.
- Provider mới PHẢI kế thừa ABC (`base_analyzer.py`, `base_transcriber.py`) + có test file riêng.
- External API calls PHẢI có error handling + retry logic.
- Prompt changes PHẢI test với ≥2 sample transcripts trước khi commit.
- Dùng `from src.config import get_logger` — không dùng `print`.
- KHÔNG dùng Local Whisper. Chỉ dùng OpenAI Whisper API (+ diarization option).
- KHÔNG dùng SQLite. Database duy nhất là PostgreSQL (qua `src/db/`).

---

## 5. Verification Sau Mỗi Thay Đổi

```bash
flake8 . --max-line-length=100 && mypy . --ignore-missing-imports && pytest tests/ -v
```

---

## 6. Code Style

- snake_case functions/variables, PascalCase classes, UPPER_CASE constants.
- Type hints đầy đủ (Python 3.9+ style: `list[str]`, không `List[str]`; không dùng `str | int` — dùng `Union`).
- Docstrings tiếng Việt, tên biến + kỹ thuật tiếng Anh.
- Pure functions khi có thể. Không global state ngoài config.

---

## 7. Dependencies

Quản lý qua `pyproject.toml` optional groups:
```bash
uv pip install -e ".[server]"   # Backend server + worker
uv pip install -e ".[frontend]" # Flet desktop app
uv pip install -e ".[dev]"      # Dev tools: pytest, flake8, mypy
uv pip install -e ".[all]"      # All-in-one (local dev)
```

---


## 9. Pull Request Requirements

- **Title**: Ngắn gọn, mô tả thay đổi.
- **Description** phải có: Summary + danh sách files thay đổi.

```
## Summary
<mô tả thay đổi>

## Changes
- <file đã thay đổi>
```

---

## 10. Secrets & Scope

- **KHÔNG** commit API keys, passwords. Dùng `.env` local (gitignored). Document trong `.env.example`.
- **Giữ scope nhỏ**: chỉ thay đổi những gì user yêu cầu. Không refactor code lân cận không liên quan.
- Khi thay đổi entrypoint hoặc setup commands: cập nhật `README.md` và docs liên quan trong cùng PR.
