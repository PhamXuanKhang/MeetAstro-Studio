# System Architecture

---

## High-level overview

```
┌──────────────────────────────────────────────────────────────┐
│                  Flet Desktop App (HTTP Client)              │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌─────────┐  │
│  │ Upload / │  │  Transcript  │  │  Review  │  │ History │  │
│  │ Record   │→ │  Editor      │→ │  Items   │→ │ + Jira  │  │
│  └──────────┘  └──────────────┘  └──────────┘  └─────────┘  │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP (httpx)
                           ▼
┌──────────────────────────────────────────────────────────────┐
│               FastAPI Server (src/api/)                      │
│  POST /meetings  POST /audio  GET /review  POST /jira/push   │
└──────┬─────────────────────────────────────────┬────────────┘
       │ enqueue task                             │ query/write
       ▼                                         ▼
┌─────────────────────┐               ┌──────────────────────┐
│   Celery Workers    │               │   PostgreSQL DB       │
│  (src/workers/)     │               │  meetings             │
│                     │               │  transcripts          │
│  transcribe_task    │──────────────→│  analysis_results     │
│  analyze_task       │               │  review_items         │
│  jira_push_task     │               │  provider_configs     │
└──────┬──────────────┘               └──────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ Providers (Strategy Pattern)                                 │
│                                                              │
│  BaseAnalyzer (ABC) → OpenAIAnalyzer (GPT-4o JSON mode)     │
│  BaseTranscriber (ABC) → OpenAITranscriber (Whisper API)    │
│                       → OpenAIDiarizeTranscriber            │
│  MockAnalyzer (testing/offline)                              │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ External APIs                                                │
│  • OpenAI Whisper API (transcription)                        │
│  • OpenAI GPT-4o (analysis, JSON mode)                       │
│  • Jira REST API v3 (push issues)                            │
└──────────────────────────────────────────────────────────────┘
```

**Infrastructure** (Docker): PostgreSQL 16 + Redis 7 + FastAPI + Celery Worker.
**Frontend**: Flet desktop app (`.exe`), connect tới server qua `API_BASE_URL`.

---

## Layer Architecture

| Layer | Path | Vai trò | Phụ thuộc |
|-------|------|---------|-----------|
| **Desktop App** | `frontend/` | Flet HTTP client — UI + local audio recording | FastAPI server |
| **API** | `src/api/` | FastAPI routers + request validation | Services, DB |
| **Worker** | `src/workers/` | Celery tasks — transcribe, analyze, jira push | Services, DB |
| **Services** | `src/services/` | Orchestration logic | Providers, Modules |
| **Providers** | `src/providers/` | Strategy pattern — OpenAI API calls | External APIs |
| **DB** | `src/db/` | SQLAlchemy async models + CRUD + Alembic | PostgreSQL |
| **Modules** | `src/modules/` | Jira client, audio recorder, exporter, vault | External APIs |
| **Core** | `src/schema.py`, `src/config.py` | Data models, configuration | stdlib |

---

## Module Map

### `src/schema.py` — Pydantic Models

```
Priority (Enum) ─── Critical | High | Medium | Low
    │
ActionItem (BaseModel) ─── summary, assignee, deadline, priority, context
    ├── Subtask (extends ActionItem) ─── confidence, validation_notes
    └── Task (extends ActionItem) ─── subtasks: list[Subtask], confidence, validation_notes

Epic (BaseModel) ─── summary, description, tasks: list[Task]

MeetingAnalysis (BaseModel) ─── epics, summary, key_decisions, discussion_points, parking_lot, created_at
    └── to_dict() / from_dict() / to_json() / from_json()

MeetingRecord (BaseModel) ─── id, title, audio_path, transcript, analysis, created_at, updated_at

ReviewItem (BaseModel) ─── id, meeting_id, item_type, item_index, summary, assignee, deadline,
                            priority, context, confidence, is_flagged, review_status,
                            edited_summary, edited_assignee, edited_deadline, edited_priority
```

### `src/providers/` — Strategy Pattern

| File | Class | ABC | Method | Notes |
|------|-------|-----|--------|-------|
| `base_analyzer.py` | `BaseAnalyzer` | ✅ | `analyze(transcript) → MeetingAnalysis` | Interface |
| `base_transcriber.py` | `BaseTranscriber` | ✅ | `transcribe(audio_path, language) → str` | Interface |
| `openai_analyzer.py` | `OpenAIAnalyzer` | extends BaseAnalyzer | `analyze()` | GPT-4o JSON mode, retry 3x |
| `openai_transcriber.py` | `OpenAITranscriber` | extends BaseTranscriber | `transcribe()` | Whisper API |
| `openai_diarize_transcriber.py` | `OpenAIDiarizeTranscriber` | extends BaseTranscriber | `transcribe()` | Whisper + speaker labels |
| `mock_analyzer.py` | `MockAnalyzer` | extends BaseAnalyzer | `analyze()` | Testing / offline fallback |

**Thêm provider mới:** Kế thừa ABC tương ứng + tạo test file riêng.

### `src/api/routers/` — FastAPI Endpoints

| Router | Prefix | Key endpoints |
|--------|--------|---------------|
| `meetings.py` | `/meetings` | CRUD meetings, upload audio, get transcript |
| `transcriptions.py` | `/meetings/{id}` | patch transcript |
| `analysis.py` | `/meetings/{id}` | trigger analysis, get analysis |
| `reviews.py` | `/meetings/{id}/review` | list, patch, approve, reject items |
| `jira.py` | `/meetings/{id}/jira` | push approved items |
| `exports.py` | `/meetings/{id}/export` | markdown, json, csv |
| `settings.py` | `/settings` | provider config CRUD |

### `src/workers/` — Celery Tasks

| File | Task name | Input | Output |
|------|-----------|-------|--------|
| `pipeline.py` | `run_pipeline` | meeting_id, audio_path, diarize, language | transcribe + analyze results |
| `transcribe_task.py` | `transcribe_audio` | meeting_id, audio_path, diarize | `{transcript_id, char_count}` |
| `analyze_task.py` | `analyze_transcript` | meeting_id, transcript_id | `{analysis_id, review_item_count, flagged_count}` |
| `jira_push_task.py` | `push_to_jira` | meeting_id | `{epic_keys, task_count, subtask_count, is_stub}` |

### `src/db/` — Database Layer

| Path | Vai trò |
|------|---------|
| `models.py` | SQLAlchemy ORM: Meeting, Transcript, AnalysisResult, ReviewItem, ProviderConfig |
| `base.py` | DeclarativeBase |
| `session.py` | Async engine + session factory |
| `crud/meeting_crud.py` | Async CRUD: Meeting, Transcript, AnalysisResult |
| `crud/review_crud.py` | Async CRUD: ReviewItem (approve/reject/bulk) |
| `crud/provider_crud.py` | Async CRUD: ProviderConfig (encrypted) |
| `migrations/` | Alembic migration scripts |

### `src/services/` — Orchestration

| File | Function | Logic |
|------|----------|-------|
| `transcription_service.py` | `transcribe()`, `transcribe_diarized()`, `transcribe_chunks()` | OpenAI Whisper API; diarize fallback về plain transcribe |
| `analysis_service.py` | `analyze(transcript)` | Validate → OpenAIAnalyzer → extraction → validation → summarization |
| `jira_service.py` | `push_analysis_to_jira(analysis)` | Orchestrate Jira push: Epic → Task → Subtask |
| `recording_service.py` | `start_recording()`, `stop_recording()` | Orchestrate `AudioRecorder` (local desktop) |
| `extraction_service.py` | `rule_based_extraction(transcript)` | Regex-based extraction để cross-validate AI |
| `validation_service.py` | `validate_action_items(...)` | Cross-validate AI vs rule-based, trả về confidence scores |
| `summarization_service.py` | `generate_summary(transcript)` | Async OpenAI call — summary, key_decisions, parking_lot |

### `src/modules/` — Persistence & Integration

| File | Vai trò |
|------|---------|
| `exporter.py` | `export_markdown()`, `export_json()`, `export_csv()` — pure functions |
| `jira_client.py` | Jira REST API v3, auto stub mode khi thiếu credentials |
| `audio_recorder.py` | System audio capture (pysysaudio) + mic mixing, chunk rotation |
| `credential_vault.py` | `encrypt()` / `decrypt()` — Fernet symmetric encryption |

---

## Key Design Patterns

### 1. Strategy Pattern (Providers)

```python
class GeminiAnalyzer(BaseAnalyzer):
    def analyze(self, transcript: str) -> MeetingAnalysis: ...
```

Tất cả providers implement cùng ABC interface → services/tasks chọn provider tại runtime.

### 2. Async Worker Pipeline (Celery)

```
POST /meetings/{id}/audio
    │
    ▼
Celery: run_pipeline.delay(meeting_id, audio_path, diarize)
    │
    ├─ transcribe_audio → Whisper API → lưu Transcript
    │
    └─ analyze_transcript → GPT-4o → lưu AnalysisResult + ReviewItem[]
```

### 3. Human-in-the-Loop Review

```
ReviewItem (status=draft)
    │
    ├─ User approve → status=approved
    ├─ User edit + approve → edited_* fields + status=approved
    └─ User reject → status=rejected

POST /jira/push → chỉ push approved items
```

### 4. Structured Output (JSON Mode)

GPT-4o + JSON mode → `MeetingAnalysis.from_dict()`:
```json
{
  "summary": "...",
  "epics": [{
    "summary": "...", "description": "...",
    "tasks": [{"summary": "...", "assignee": "...", "deadline": "YYYY-MM-DD",
               "priority": "High", "context": "...", "subtasks": [...]}]
  }]
}
```

### 5. Stub Pattern (Jira)

`JiraClient` auto-detect thiếu credentials → `is_stub = True` → fake key `"STUB-001"`.
