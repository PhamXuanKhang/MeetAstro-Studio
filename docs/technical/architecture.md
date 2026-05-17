# System Architecture

**Cập nhật:** 11/05/2026

---

## High-level overview

```
┌──────────────────────────────────────────────────────────────┐
│                 Electron Desktop App                         │
│              React + TypeScript + Supabase SDK               │
└──────────────────────────────┬───────────────────────────────┘
                               │ HTTP / Supabase SDK
                               ▼
┌──────────────────────────────────────────────────────────────┐
│                  FastAPI Server (src/api/)                   │
│  /meetings  /audio  /transcript  /analysis  /review  /jira │
└──────┬─────────────────────────────────────────┬────────────┘
       │ enqueue task                          │ query/write
       ▼                                       ▼
┌─────────────────────┐               ┌──────────────────────┐
│   Celery Workers    │               │     Supabase          │
│  (src/workers/)    │               │  (Supabase tables)    │
│                     │               │                       │
│  run_pipeline      │───────────────│  meetings            │
│  transcribe_task   │               │  transcript_segments  │
│  analyze_task      │               │  analysis_results     │
│  jira_push_task    │               │  action_items        │
│  cleanup_task      │               │  provider_configs     │
└──────┬──────────────┘               └──────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ Providers (Strategy Pattern)                                 │
│                                                              │
│  BaseAnalyzer (ABC) → OpenAIAnalyzer (GPT-4o JSON mode)    │
│  BaseTranscriber (ABC) → OpenAITranscriber (Whisper API)    │
│                       → OpenAIDiarizeTranscriber             │
│                       → WhisperLiveKitTranscriber            │
│  MockAnalyzer (testing/offline)                              │
└──────────────────────────────────────────────────────────────┘
```

**Infrastructure:** Supabase + Redis 7 + FastAPI + Celery Worker
**Frontend:** Electron desktop app (`MeetAstro-Setup-*.exe`)

---

## Frontend Architecture

### Electron Desktop App
- **Tech:** TypeScript + React + Vite + Electron
- **Entry:** `cd electron-app && npm run dev`
- **Build:** `cd electron-app && npm run build`
- **Auth:** Supabase JS SDK (email/password + Google OAuth)
- **State:** Zustand store

Flet was an early prototype path and is not the active submission frontend.

---

## Layer Architecture

| Layer | Path | Vai trò | Phụ thuộc |
|-------|------|---------|-----------|
| **Frontend (Electron)** | `electron-app/` | React + TypeScript — UI + Supabase auth | FastAPI + Supabase |
| **API** | `src/api/` | FastAPI routers + request validation | Services, Supabase |
| **Worker** | `src/workers/` | Celery tasks — transcribe, analyze, jira push | Services, Supabase |
| **Services** | `src/services/` | Orchestration logic | Providers, Modules |
| **Providers** | `src/providers/` | Strategy pattern — OpenAI API calls | External APIs |
| **DB** | `src/db/supabase_client.py` | Supabase client (SERVICE_ROLE_KEY) | Supabase |
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
| `whisper_livekit_transcriber.py` | `WhisperLiveKitTranscriber` | extends BaseTranscriber | `transcribe()` | LiveKit WebSocket streaming |
| `mock_analyzer.py` | `MockAnalyzer` | extends BaseAnalyzer | `analyze()` | Testing / offline fallback |

**Thêm provider mới:** Kế thừa ABC tương ứng + tạo test file riêng.

### `src/api/routers/` — FastAPI Endpoints

| Router | Prefix | Key endpoints |
|--------|--------|---------------|
| `meetings.py` | `/meetings` | CRUD meetings, upload audio |
| `transcriptions.py` | `/meetings/{id}` | get/update transcript |
| `analysis.py` | `/meetings/{id}` | trigger analysis, get analysis |
| `reviews.py` | `/meetings/{id}/review` | list, patch, approve, reject items |
| `jira.py` | `/meetings/{id}/jira` | push approved items |
| `exports.py` | `/meetings/{id}/export` | markdown, json, csv |
| `settings.py` | `/settings` | provider config CRUD |
| `stream.py` | `/meetings/{id}/transcribe/stream` | real-time SSE streaming |

### `src/workers/` — Celery Tasks

| File | Task name | Input | Output |
|------|-----------|-------|--------|
| `pipeline.py` | `run_pipeline` | meeting_id, audio_path, diarize, language | transcribe + analyze results |
| `transcribe_task.py` | `transcribe_audio` | meeting_id, audio_path, diarize | `{transcript_id, char_count}` |
| `analyze_task.py` | `analyze_transcript` | meeting_id, transcript_id | `{analysis_id, review_item_count, flagged_count}` |
| `jira_push_task.py` | `push_to_jira` | meeting_id | `{epic_keys, task_count, subtask_count, is_stub}` |
| `cleanup_task.py` | `cleanup_old_recordings` | days | `{deleted_count, freed_bytes}` |

### `src/db/supabase_client.py` — Supabase Access

| Function | Description |
|----------|-------------|
| `get_supabase_client()` | Singleton Supabase client (SERVICE_ROLE_KEY) |
| `insert(table, data)` | Insert row, return record |
| `upsert(table, data)` | Upsert row, return record |
| `update_by_id(table, id, data)` | Update row by ID |
| `delete_by_id(table, id)` | Delete row |
| `fetch_one(table, filters)` | Fetch single row |
| `fetch_all(table, filters)` | Fetch all matching rows |

### `src/services/` — Orchestration

| File | Function | Logic |
|------|----------|-------|
| `transcription_service.py` | `transcribe()`, `transcribe_diarized()` | OpenAI Whisper API; diarize fallback |
| `analysis_service.py` | `analyze(transcript)` | Validate → OpenAIAnalyzer → extraction → validation → summarization |
| `audio_ingestion_service.py` | `process_upload()` | Validate, normalize (ffmpeg → WAV 16kHz mono), extract from video |
| `jira_service.py` | `push_analysis_to_jira()` | Orchestrate Jira push: Epic → Task → Subtask |
| `recording_service.py` | `start_recording()`, `stop_recording()` | Orchestrate `AudioRecorder` (local desktop) |
| `extraction_service.py` | `rule_based_extraction()` | Regex-based extraction để cross-validate AI |
| `validation_service.py` | `validate_action_items()` | Cross-validate AI vs rule-based, trả về confidence scores |
| `summarization_service.py` | `generate_summary()` | OpenAI call — summary, key_decisions, parking_lot |
| `stream_session_manager.py` | `StreamSessionManager` | Manage real-time transcription sessions |

### `src/modules/` — Persistence & Integration

| File | Vai trò |
|------|---------|
| `exporter.py` | `export_markdown()`, `export_json()`, `export_csv()` |
| `jira_client.py` | Jira REST API v3, auto stub mode khi thiếu credentials |
| `audio_recorder.py` | System audio capture + mic mixing, chunk rotation |
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
    ├─ transcribe_audio → Whisper API → lưu TranscriptSegment[]
    │
    └─ analyze_transcript → GPT-4o → lưu AnalysisResult + ActionItem[]
```

### 3. Human-in-the-Loop Review

```
ActionItem (status=draft)
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

### 6. Dual Database Access

- **Backend (FastAPI/Celery):** Uses `src/db/supabase_client.py` with `SERVICE_ROLE_KEY` for all operations
- **Electron Frontend:** Uses Supabase JS SDK with `ANON_KEY` for auth and client-side queries

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes (backend) | Backend database access |
| `SUPABASE_ANON_KEY` | Yes (Electron) | Frontend auth |
| `OPENAI_API_KEY` | Yes | GPT-4o + Whisper API |
| `APP_SECRET_KEY` | Yes | Fernet key cho credential encryption |
| `CELERY_BROKER_URL` | No | Redis broker (default: `redis://localhost:6379/0`) |
| `CELERY_RESULT_BACKEND` | No | Redis result backend (default: `redis://localhost:6379/1`) |
| `WHISPER_LIVEKIT_URL` | No | LiveKit WebSocket URL for real-time transcription |
| `JIRA_BASE_URL` | No | Jira instance URL (stub mode nếu thiếu) |
| `JIRA_EMAIL` | No | Jira Basic Auth email |
| `JIRA_API_TOKEN` | No | Jira API token |
| `JIRA_PROJECT_KEY` | No | Jira project key |
