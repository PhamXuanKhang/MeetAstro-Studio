# Data Flow

Luồng dữ liệu end-to-end từ audio input đến output cuối cùng.

---

## Pipeline tổng quan

```
┌────────────────────────────────────────┐
│ 0. AUDIO INPUT (2 options)             │
│                                        │
│  Option A: Upload file                 │
│    st.file_uploader → tempfile         │
│                                        │
│  Option B: Record system audio         │
│    recording_service.start_recording() │
│         │                              │
│    AudioRecorder (background thread)   │
│    • System audio capture (pysysaudio) │
│    • Optional mic mixing (sounddevice) │
│    • Chunk rotation mỗi N giây         │
│         │                              │
│    recording_service.stop_recording()  │
│         │                              │
│    WAV file path                       │
└────────────────────────────────────────┘
                     │
                     ▼
Audio File (.wav/.mp3/.m4a)
    │
    │  (from upload or recording)
    ▼
┌────────────────────────────────────────┐
│ 1. TRANSCRIPTION                       │
│                                        │
│    audio_path (str)                    │
│         │                              │
│    transcription_service.transcribe()  │
│         │                              │
│    ┌────▼─────────────┐                │
│    │ OpenAITranscriber │───✅──→ text  │
│    └────┬─────────────┘        (str)   │
│         │ ❌ fail                       │
│    ┌────▼──────────────┐               │
│    │ LocalTranscriber   │───✅──→ text │
│    └────┬──────────────┘               │
│         │ ❌ fail                       │
│         └──→ RuntimeError              │
└────────────────────┬───────────────────┘
                     │ transcript (str)
                     ▼
          ┌─── User edits text area ───┐
          │  (optional correction)     │
          └────────────┬───────────────┘
                       │ transcript (str, possibly edited)
                       ▼
┌────────────────────────────────────────┐
│ 2. ANALYSIS                            │
│                                        │
│    analysis_service.analyze()          │
│         │                              │
│    ┌────▼──────────────┐               │
│    │ OpenAIAnalyzer     │              │
│    │  • system prompt   │              │
│    │  • GPT-4o JSON mode│              │
│    │  • retry 3x        │              │
│    └────┬──────────────┘               │
│         │                              │
│    raw JSON → MeetingAnalysis.from_dict│
│         │                              │
│    MeetingAnalysis                     │
│      ├── summary: str                  │
│      ├── key_decisions: list[str]      │
│      ├── discussion_points: list[str]  │
│      ├── parking_lot: list[str]        │
│      ├── epics: list[Epic]             │
│      │    └── tasks: list[Task]        │
│      │         └── subtasks: list      │
│      └── created_at: datetime          │
└────────────────────┬───────────────────┘
                     │ MeetingAnalysis
                     ▼
┌────────────────────────────────────────┐
│ 2.5 VALIDATION (optional)              │
│                                        │
│    extraction_service.rule_based_      │
│         extraction(transcript)         │
│         │                              │
│    rule_items: list[dict]              │
│         │                              │
│    validation_service.validate_        │
│         action_items(ai_items,         │
│                      rule_items,       │
│                      transcript)       │
│         │                              │
│    validated_items với confidence      │
│    scores + validation_notes           │
│         │                              │
│    metrics: cross_validation_score,    │
│             context_coherence_score,   │
│             structural_validation_score│
│    (Xem workflows/validation-logic.md) │
└────────────────────┬───────────────────┘
                     │ MeetingAnalysis (với confidence)
                     ▼
┌────────────────────────────────────────┐
│ 3. OUTPUT (user chọn)                  │
│                                        │
│  ┌──────────┐  ┌───────┐  ┌─────────┐ │
│  │ Export    │  │ Save  │  │ Push    │ │
│  │ MD/JSON/ │  │ to DB │  │ to Jira │ │
│  │ CSV      │  │       │  │         │ │
│  └────┬─────┘  └───┬───┘  └────┬────┘ │
│       │            │           │       │
│  File download  SQLite      Jira API   │
│  (browser)     insert       POST       │
│                             (or stub)  │
└────────────────────────────────────────┘
```

---

## Data transformations

| Stage | Input | Transform | Output |
|-------|-------|-----------|--------|
| Record | User action | `recording_service.start/stop()` → `AudioRecorder` | `audio_path: str` (WAV) |
| Upload | `UploadedFile` (Streamlit) | `tempfile.NamedTemporaryFile` | `audio_path: str` |
| Transcribe | `audio_path: str` | Whisper API / Local Whisper | `transcript: str` |
| User edit | `transcript: str` | `st.text_area` | `transcript: str` (edited) |
| Analyze | `transcript: str` | GPT-4o JSON mode → `from_dict()` | `MeetingAnalysis` |
| Rule extract | `transcript: str` | `extraction_service.rule_based_extraction()` | `list[dict]` (rule_items) |
| Validate | AI items + rule items + transcript | `validation_service.validate_action_items()` | `(validated_items, metrics)` |
| Summarize | `transcript: str` | `summarization_service.generate_summary()` | `dict` (summary, key_decisions, etc.) |
| Export MD | `MeetingAnalysis` | `export_markdown()` | `str` (Markdown) |
| Export JSON | `MeetingAnalysis` | `export_json()` → `to_dict()` + `json.dumps` | `str` (JSON) |
| Export CSV | `MeetingAnalysis` | `export_csv()` → flatten Epic/Task/Subtask | `str` (CSV) |
| Save DB | `MeetingRecord` | `create_meeting()` → `analysis.to_json()` → INSERT | `int` (new id) |
| Push Jira | `MeetingAnalysis` | `jira_service.push_analysis_to_jira()` → `JiraClient.create_*()` → REST POST | `JiraPushResult` |

---

## State management

Streamlit `session_state` giữ các biến xuyên suốt session:

| Key | Type | Khởi tạo | Cập nhật khi |
|-----|------|----------|-------------|
| `transcript` | `str` | `""` | Sau transcribe, hoặc user edit text area |
| `analysis` | `MeetingAnalysis \| None` | `None` | Sau analyze thành công |
| `audio_path` | `str \| None` | `None` | Sau upload file hoặc recording |
| `is_recording` | `bool` | `False` | Khi start/stop recording |
| `validation_metrics` | `dict \| None` | `None` | Sau validation service chạy |

> **Lưu ý:** Streamlit re-run toàn bộ script mỗi khi user tương tác. `session_state` là cách duy nhất giữ data giữa các re-runs.

> **Recording state:** `AudioRecorder` là module-level singleton trong `recording_service.py` để giữ state giữa Streamlit reruns.

---

## Database schema

```sql
CREATE TABLE meetings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    audio_path  TEXT,
    transcript  TEXT    NOT NULL DEFAULT '',
    analysis    TEXT,           -- JSON string (MeetingAnalysis.to_json())
    created_at  TEXT    NOT NULL,  -- ISO 8601
    updated_at  TEXT    NOT NULL   -- ISO 8601
);
```

`analysis` column lưu JSON string, deserialize bằng `MeetingAnalysis.from_json()`.

---

## External API calls

| API | Endpoint | Auth | Payload | Response |
|-----|----------|------|---------|----------|
| OpenAI Whisper | `audio.transcriptions.create` | Bearer `OPENAI_API_KEY` | audio file + `model="whisper-1"` | `str` (transcript) |
| OpenAI GPT-4o | `chat.completions.create` | Bearer `OPENAI_API_KEY` | system prompt + transcript, `response_format=json_object` | JSON string → parse |
| Jira REST v3 | `POST /rest/api/3/issue` | Basic Auth (`JIRA_EMAIL` + `JIRA_API_TOKEN`) | Issue fields (project, summary, type, priority, parent) | `{"key": "MEET-1"}` |

Tất cả API calls có error handling + retry logic (xem [architecture.md](architecture.md)).

---

## Jira upload flow (chi tiết)

Luồng đẩy Jira đã được nối trực tiếp trong UI tại `src/app.py` (nút `🚀 Đẩy lên Jira`).

Đọc chi tiết thứ tự gọi API, payload mapping, STUB mode, và các rủi ro vận hành tại:

- [workflows/jira-upload-flow.md](workflows/jira-upload-flow.md)
