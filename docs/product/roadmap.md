# Roadmap & Milestones

**Cập nhật lần cuối:** 11/05/2026

---

## Tổng quan

| Phase | Mục tiêu | Timeline | Trạng thái |
|-------|----------|----------|------------|
| **Phase 1 — MVP Core** | Transcribe + Analyze + Export | Sprint 1 (02/04 → 12/04) | ✅ Done |
| **Phase 2 — Integration** | Jira thật + E2E test + Deploy | Sprint 2 (13/04 → 26/04) | ✅ Done |
| **Phase 3 — Quality** | Eval pipeline + Prompt tuning + UX polish | Sprint 3 (27/04 → 10/05) | 🔄 In Progress |
| **Phase 4 — Scale** | Multi-user + Analytics + Feedback loop | Backlog | ⬜ Backlog |

---

## Phase 1 — MVP Core ✅

> **Goal:** Chạy được full pipeline: Audio → Transcript → Analysis → Export

| Deliverable | Status |
|-------------|--------|
| Pydantic models (Priority, ActionItem, Task, Epic, MeetingAnalysis, MeetingRecord) | ✅ |
| Strategy Pattern: ABC base + providers (OpenAI Analyzer, Mock Analyzer, OpenAI Transcriber, OpenAI Diarize Transcriber) | ✅ |
| OpenAI Whisper API transcription + diarization fallback về plain OpenAI transcription | ✅ |
| Supabase CRUD + provider_configs encrypted | ✅ |
| Export Markdown / JSON / CSV (exporter.py) | ✅ |
| Jira stub client (mock mode khi thiếu credentials) | ✅ |
| Vietnamese prompt cho GPT-4o structured output | ✅ |
| Electron desktop app HTTP client | ✅ |
| Unit tests (14 test files), mock external APIs | ✅ |
| pyproject.toml + editable install | ✅ |
| Config với pydantic-settings | ✅ |

**ADRs liên quan:** ADR-1 (xóa legacy, build mới), ADR-3 (pyproject.toml), ADR-5 (Jira stub)
→ Xem chi tiết: [WORKLOG.md](../../WORKLOG.md)

---

## Phase 2 — Integration ✅

> **Goal:** Kết nối hệ thống thật, deploy được, test end-to-end

| Deliverable | Owner | Status |
|-------------|-------|--------|
| Audio recording (system audio + mic mixing) | Vthuc | ✅ |
| Recording service orchestration cho Electron desktop | Vthuc | ✅ |
| Chunked transcription (chunk rotation mỗi N giây) | Vthuc | ✅ |
| Rule-based extraction service (cross-validate với AI) | Khang | ✅ |
| Validation service (confidence scores) | Khang | ✅ |
| Async summarization service (streaming) | Khang | ✅ |
| Credential vault (Fernet encryption) | Khang | ✅ |
| Provider configs CRUD | Khang | ✅ |
| Schema mở rộng (key_decisions, discussion_points, parking_lot) | Khang | ✅ |
| Jira upload flow documentation | Duypt | ✅ |
| Smoke test Electron app E2E với audio thật | Khang | ✅ |
| Test Jira integration với Atlassian sandbox | Khang | ✅ |
| Chạy flake8 + mypy clean | Khang | ✅ |
| Deploy backend lên VPS/Docker, distribute Electron EXE build | [TBD] | ⬜ |
| CI/CD pipeline (GitHub Actions: lint + test + deploy) | [TBD] | ⬜ |

---

## Phase 3 — Quality 🔄

> **Goal:** Đo lường chất lượng AI, tune prompt, polish UX

| Deliverable | Owner | Status |
|-------------|-------|--------|
| Confidence scoring (cross-validation AI vs rule-based) | Khang | ✅ |
| Eval pipeline: so sánh AI output vs human-labeled ground truth | [TBD] | ⬜ |
| Thu thập ≥ 5 sample transcripts để eval | [TBD] | ⬜ |
| Prompt tuning dựa trên eval results (target recall ≥ 85%) | [TBD] | ⬜ |
| UX: cho phép edit analysis trực tiếp trước export | [TBD] | ⬜ |
| Speaker diarization (detect giọng từng người) | [TBD] | ⬜ |
| Unit tests mở rộng (14 files) | Khang | ✅ |
| E2E test script (`test_e2e.sh`) | Khang | ✅ |
| Eval documentation (`docs/evaluation/`) | Khang | ✅ |

---

## Phase 4 — Scale ⬜ (Backlog)

> **Goal:** Multi-user, analytics, data flywheel

| Deliverable | Notes |
|-------------|-------|
| Quota enforcement + usage analytics | `user_plans`, `usage_records`, `quota_limits` đã có migration |
| User authentication (login/session) | FastAPI auth hoặc external OAuth |
| Analytics dashboard (track adoption, correction rate) | Learning signal từ Canvas |
| Feedback loop: log corrections → improve prompt | Data flywheel |
| Real-time transcription (chunking + streaming) | ✅ Chunking đã có (AudioRecorder) — còn streaming UI |
| Multi-provider support (Gemini, Claude, etc.) | Credential vault + provider_configs đã sẵn sàng |

---

## Dependency graph

```
Phase 1 (MVP Core)
    ↓
Phase 2 (Integration) ←── cần Jira sandbox + cloud hosting
    ↓
Phase 3 (Quality) ←── cần sample transcripts + eval labels
    ↓
Phase 4 (Scale) ←── cần user feedback data
```

---

## Current Architecture

### Submit Frontend

| Frontend | Tech Stack | Status |
|----------|------------|--------|
| **Electron Desktop** | TypeScript + React + Vite + Electron | ✅ Submit frontend |

Flet was an early prototype path and is not the active submission frontend.

### Backend Stack

| Component | Technology |
|-----------|------------|
| API | FastAPI + Pydantic |
| Database/Auth | Supabase SDK + Supabase Auth |
| Task Queue | Celery + Redis |
| AI Providers | OpenAI Whisper, GPT-4o, optional WhisperLiveKit |
| Storage | Local filesystem for uploaded/normalized audio |

### Key Features Implemented

- [x] Audio upload + validation (mp3, wav, m4a, ogg, mp4, mkv, webm)
- [x] Audio normalization via ffmpeg (→ WAV 16kHz mono)
- [x] Video-to-audio extraction
- [x] Transcription (Whisper API + Diarization fallback)
- [x] Analysis (GPT-4o structured output → Epic/Task/Subtask)
- [x] Review workflow (approve/reject/edit action items)
- [x] Export (Markdown/JSON/CSV)
- [x] Jira integration (Epic → Task → Subtask)
- [x] Streaming transcription session management
- [x] Celery pipeline orchestration
- [x] Cleanup service (periodic task every 2h)
