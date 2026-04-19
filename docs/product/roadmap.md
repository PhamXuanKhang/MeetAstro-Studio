# Roadmap & Milestones

**Cập nhật lần cuối:** 19/04/2026

---

## Tổng quan

| Phase | Mục tiêu | Timeline | Trạng thái |
|-------|----------|----------|------------|
| **Phase 1 — MVP Core** | Transcribe + Analyze + Export | Sprint 1 (02/04 → 12/04) | ✅ Done |
| **Phase 2 — Integration** | Jira thật + E2E test + Deploy | Sprint 2 (13/04 → 26/04) | 🔄 In Progress |
| **Phase 3 — Quality** | Eval pipeline + Prompt tuning + UX polish | Sprint 3 (27/04 → 10/05) | ⬜ Planned |
| **Phase 4 — Scale** | Multi-user + Analytics + Feedback loop | Backlog | ⬜ Backlog |

---

## Phase 1 — MVP Core ✅

> **Goal:** Chạy được full pipeline: Audio → Transcript → Analysis → Export

| Deliverable | Status |
|-------------|--------|
| Pydantic models (Priority, ActionItem, Task, Epic, MeetingAnalysis, MeetingRecord) | ✅ |
| Strategy Pattern: ABC base + 4 providers (OpenAI Analyzer, Mock Analyzer, OpenAI Transcriber, Local Transcriber) | ✅ |
| Fallback chain transcription (Whisper API → Local Whisper) | ✅ |
| SQLite CRUD (database.py) + provider_configs | ✅ |
| Export Markdown / JSON / CSV (exporter.py) | ✅ |
| Jira stub client (mock mode khi thiếu credentials) | ✅ |
| Vietnamese prompt cho GPT-4o structured output | ✅ |
| Streamlit UI 3-column layout | ✅ |
| Unit tests (14 test files), all passing | ✅ |
| pyproject.toml + editable install | ✅ |
| Config với pydantic-settings | ✅ |

**ADRs liên quan:** ADR-1 (xóa legacy, build mới), ADR-2 (SQLite cho MVP), ADR-3 (pyproject.toml), ADR-5 (Jira stub)
→ Xem chi tiết: [WORKLOG.md](../../WORKLOG.md)

---

## Phase 2 — Integration 🔄

> **Goal:** Kết nối hệ thống thật, deploy được, test end-to-end

| Deliverable | Owner | Status |
|-------------|-------|--------|
| Audio recording (system audio + mic mixing) | Vthuc | ✅ |
| Recording service orchestration cho Streamlit | Vthuc | ✅ |
| Chunked transcription (chunk rotation mỗi N giây) | Vthuc | ✅ |
| Rule-based extraction service (cross-validate với AI) | Khang | ✅ |
| Validation service (confidence scores) | Khang | ✅ |
| Async summarization service (streaming) | Khang | ✅ |
| Credential vault (Fernet encryption) | Khang | ✅ |
| Provider configs CRUD | Khang | ✅ |
| Schema mở rộng (key_decisions, discussion_points, parking_lot) | Khang | ✅ |
| Jira upload flow documentation | Duypt | ✅ |
| Smoke test Streamlit app E2E với audio thật | Khang | ⬜ |
| Test Jira integration với Atlassian sandbox | Khang | ⬜ |
| Chạy flake8 + mypy clean | Khang | ⬜ |
| Deploy lên cloud (Streamlit Community Cloud hoặc VPS) | [TBD] | ⬜ |
| CI/CD pipeline (GitHub Actions: lint + test + deploy) | [TBD] | ⬜ |

---

## Phase 3 — Quality ⬜

> **Goal:** Đo lường chất lượng AI, tune prompt, polish UX

| Deliverable | Owner | Status |
|-------------|-------|--------|
| Confidence scoring (cross-validation AI vs rule-based) | Khang | ✅ |
| Eval pipeline: so sánh AI output vs human-labeled ground truth | [TBD] | ⬜ |
| Thu thập ≥ 5 sample transcripts để eval | [TBD] | ⬜ |
| Prompt tuning dựa trên eval results (target recall ≥ 85%) | [TBD] | ⬜ |
| UX: cho phép edit analysis trực tiếp trước export | [TBD] | ⬜ |
| Speaker diarization (detect giọng từng người) | [TBD] | ⬜ |

---

## Phase 4 — Scale ⬜ (Backlog)

> **Goal:** Multi-user, analytics, data flywheel

| Deliverable | Notes |
|-------------|-------|
| PostgreSQL thay SQLite (multi-user concurrent writes) | ADR-2 đã thiết kế interface abstract sẵn |
| User authentication (login/session) | Streamlit auth hoặc external OAuth |
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
