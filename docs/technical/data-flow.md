# Data Flow

Luồng dữ liệu end-to-end từ audio input đến output cuối cùng.

---

## Pipeline tổng quan

```
┌────────────────────────────────────────┐
│ 0. AUDIO INPUT (2 options)             │
│                                        │
│  Option A: Upload file                 │
│    Flet file dialog → audio path       │
│                                        │
│  Option B: Record system audio (local) │
│    recording_service.start_recording() │
│         │                              │
│    AudioRecorder (background thread)   │
│    • System audio capture (pysysaudio) │
│    • Optional mic mixing (sounddevice) │
│    • Chunk rotation every N seconds    │
│         │                              │
│    recording_service.stop_recording()  │
│         │                              │
│    WAV file path (local)               │
└────────────────────────────────────────┘
                     │
                     ▼
Audio File (.wav/.mp3/.m4a)
    │
    │  POST /meetings/{id}/audio (multipart upload)
    ▼
┌────────────────────────────────────────┐
│ 1. TRANSCRIPTION (Celery Worker)       │
│                                        │
│    transcribe_task                     │
│         │                              │
│    if diarize:                         │
│    ┌────▼──────────────────────┐       │
│    │ WhisperLiveKit (C10)       │       │
│    │  • WebSocket streaming     │       │
│    │  • ffmpeg → PCM → WS      │       │
│    │  • SSE → Frontend         │       │
│    └────┬──────────────────────┘       │
│         │ ❌ fail / no URL → fallback   │
│    ┌────▼──────────────────────┐       │
│    │ OpenAIDiarizeTranscriber  │       │
│    │  • gpt-4o-transcribe-    │       │
│    │    diarize model           │       │
│    └────┬──────────────────────┘       │
│         │ ❌ fail → fallback           │
│    else / fallback:                    │
│    ┌────▼──────────────────────┐       │
│    │ OpenAITranscriber         │       │
│    │  • Whisper API            │       │
│    └────┬──────────────────────┘       │
│         │                              │
│    → lưu Transcript vào PostgreSQL     │
│    → update Meeting.status=transcribed │
└────────────────────┬───────────────────┘
                     │ transcript (str)
                     ▼
          ┌─── User edits text area ───┐
          │  PATCH /meetings/{id}/     │
          │  transcript (optional)     │
          └────────────┬───────────────┘
                       │ transcript (str, possibly edited)
                       ▼
┌────────────────────────────────────────┐
│ 2. ANALYSIS (Celery Worker)            │
│                                        │
│    analyze_task                        │
│         │                              │
│    analysis_service.analyze()          │
│    ┌────▼──────────────┐               │
│    │ OpenAIAnalyzer     │              │
│    │  • system prompt   │              │
│    │  • GPT-4o JSON mode│              │
│    │  • retry 3x        │              │
│    └────┬──────────────┘               │
│         │                              │
│    raw JSON → MeetingAnalysis          │
│         │                              │
│    extraction_service (rule-based)     │
│    validation_service (confidence)     │
│    summarization_service (summary)     │
│         │                              │
│    → lưu AnalysisResult vào PostgreSQL │
│    → flatten → ReviewItem[] (draft)    │
│    → update Meeting.status=draft       │
└────────────────────┬───────────────────┘
                     │ ReviewItem[] (status=draft)
                     ▼
┌────────────────────────────────────────┐
│ 3. HUMAN-IN-THE-LOOP REVIEW            │
│                                        │
│    GET /meetings/{id}/review           │
│         │                              │
│    Frontend: review_view               │
│    • Hiển thị từng ReviewItem          │
│    • User approve / edit / reject      │
│    • is_flagged items nổi bật          │
│         │                              │
│    PATCH /meetings/{id}/review/{item}  │
│    POST  /meetings/{id}/review/{item}  │
│          /approve                      │
│    POST  /meetings/{id}/review/        │
│          approve_all                   │
└────────────────────┬───────────────────┘
                     │ approved ReviewItem[]
                     ▼
┌────────────────────────────────────────┐
│ 4. OUTPUT (user chọn)                  │
│                                        │
│  ┌──────────┐  ┌───────────────────┐   │
│  │ Export    │  │ Push to Jira      │   │
│  │ MD/JSON/ │  │ (approved items   │   │
│  │ CSV      │  │  only)            │   │
│  └────┬─────┘  └──────┬────────────┘   │
│       │               │               │
│  File download   jira_push_task        │
│  (browser/disk)  (Celery worker)       │
│                       │               │
│                  Jira REST API v3      │
│                  (stub if no creds)    │
└────────────────────────────────────────┘
```

---

## Data Transformations

| Stage | Input | Transform | Output |
|-------|-------|-----------|--------|
| Record | User action | `recording_service.start/stop()` → `AudioRecorder` | `audio_path: str` (WAV, local) |
| Upload | File path (Flet) | File dialog | `audio_path: str` |
| Transcribe (batch) | `audio_path` (multipart) | Whisper API / OpenAIDiarizeTranscriber | `Transcript` (PostgreSQL) |
| Transcribe (stream) | `audio_path` | WhisperLiveKit WS → `stream_to_callback()` | `segments[]` via SSE |
| User edit | `transcript.raw_text` | PATCH /transcript | `transcript.raw_text` (updated) |
| Analyze | `transcript.raw_text` | GPT-4o JSON mode → `from_dict()` | `AnalysisResult` (PostgreSQL) |
| Rule extract | `transcript.raw_text` | `extraction_service.rule_based_extraction()` | `list[dict]` (rule_items) |
| Validate | AI items + rule items + transcript | `validation_service.validate_action_items()` | confidence scores + validation_notes |
| Summarize | `transcript.raw_text` | `summarization_service.generate_summary()` | summary, key_decisions, parking_lot |
| Review | `AnalysisResult` | flatten Epic/Task/Subtask | `ReviewItem[]` (status=draft) |
| Approve | `ReviewItem` | PATCH/POST approve | `ReviewItem` (status=approved, edited_* if edited) |
| Export MD | `AnalysisResult.analysis_json` | `export_markdown()` | `str` (Markdown) |
| Export JSON | `AnalysisResult.analysis_json` | `export_json()` | `str` (JSON) |
| Export CSV | `AnalysisResult.analysis_json` | `export_csv()` → flatten | `str` (CSV) |
| Push Jira | approved `ReviewItem[]` | `jira_push_task` → `JiraClient.create_*()` → REST POST | `JiraPushResult` |

---

## State Management

AppState trong `frontend/core/state.py`:

| Key | Type | Updated when |
|-----|------|-------------|
| `transcript` | `str` | Sau transcription hoặc user edit |
| `analysis` | `MeetingAnalysis \| None` | Sau analyze hoàn thành |
| `audio_path` | `str \| None` | Sau upload hoặc recording |
| `current_meeting_id` | `str \| None` | Sau create meeting (UUID) |
| `review_items` | `list[ReviewItem]` | Sau load review items |
| `meeting_status` | `str` | Realtime poll từ server |

`AudioRecorder` là module-level singleton trong `recording_service.py` — chạy local trên desktop.

---

## Database Schema (Supabase)

8 tables — UUID primary keys, TIMESTAMPTZ timestamps:

| Table | Columns key | Quan hệ |
|-------|-------------|---------|
| `meetings` | id, title, audio_path, status, user_id, celery_task_id | parent |
| `transcript_segments` | id, meeting_id, speaker, start_time, end_time, content | belongs to meeting |
| `analysis_results` | id, meeting_id, raw_response (JSONB), summary, overall_confidence | belongs to meeting |
| `action_items` | id, meeting_id, item_type, parent_id, summary, assignee, deadline, priority, context, confidence, review_status, is_flagged, jira_issue_key | belongs to meeting |
| `provider_configs` | id, user_id, provider_name, config_json (encrypted), active | standalone |
| `user_plans` | id, user_id, plan_type, plan_started_at, plan_expires_at, is_active | quota management |
| `usage_records` | id, user_plan_id, usage_type, usage_count, period_start, period_end | usage tracking |
| `quota_limits` | id, plan_type, limit_type, limit_value, period_type, is_active | quota rules |

Database access via Supabase SDK (`src/db/supabase_client.py`).

---

## External API Calls

| API | Endpoint | Auth | Payload | Response |
|-----|----------|------|---------|----------|
| OpenAI Whisper | `audio.transcriptions.create` | Bearer `OPENAI_API_KEY` | audio file + `model="whisper-1"` | `str` (transcript) |
| OpenAI Diarize | `audio.transcriptions.create` | Bearer `OPENAI_API_KEY` | audio file + `model="gpt-4o-transcribe-diarize"` | `str` (với speaker labels) |
| OpenAI GPT-4o | `chat.completions.create` | Bearer `OPENAI_API_KEY` | system prompt + transcript, `response_format=json_object` | JSON → parse |
| Jira REST v3 | `POST /rest/api/3/issue` | Basic Auth | Issue fields (project, summary, type, priority, parent) | `{"key": "MEET-1"}` |

Tất cả API calls có error handling. Celery tasks có retry logic (`max_retries`, `default_retry_delay`).

---

## Jira Upload Flow

Xem chi tiết: [workflows/jira-upload-flow.md](workflows/jira-upload-flow.md)

Tóm tắt: Chỉ approved `ReviewItem[]` (từ human review) mới được push. Task reconstruct `MeetingAnalysis` từ approved items, ưu tiên `edited_*` fields nếu user đã chỉnh sửa.
