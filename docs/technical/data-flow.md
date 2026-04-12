# Data Flow

Luồng dữ liệu end-to-end từ audio input đến output cuối cùng.

---

## Pipeline tổng quan

```
Audio File (.wav/.mp3/.m4a)
    │
    │  st.file_uploader → tempfile
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
│      ├── epics: list[Epic]             │
│      │    └── tasks: list[Task]        │
│      │         └── subtasks: list      │
│      └── created_at: datetime          │
└────────────────────┬───────────────────┘
                     │ MeetingAnalysis
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
| Upload | `UploadedFile` (Streamlit) | `tempfile.NamedTemporaryFile` | `audio_path: str` |
| Transcribe | `audio_path: str` | Whisper API / Local Whisper | `transcript: str` |
| User edit | `transcript: str` | `st.text_area` | `transcript: str` (edited) |
| Analyze | `transcript: str` | GPT-4o JSON mode → `from_dict()` | `MeetingAnalysis` |
| Export MD | `MeetingAnalysis` | `export_markdown()` | `str` (Markdown) |
| Export JSON | `MeetingAnalysis` | `export_json()` → `to_dict()` + `json.dumps` | `str` (JSON) |
| Export CSV | `MeetingAnalysis` | `export_csv()` → flatten Epic/Task/Subtask | `str` (CSV) |
| Save DB | `MeetingRecord` | `create_meeting()` → `analysis.to_json()` → INSERT | `int` (new id) |
| Push Jira | `MeetingAnalysis` | `JiraClient.create_epic/task/subtask()` → REST POST | `str` (issue keys) |

---

## State management

Streamlit `session_state` giữ 3 biến xuyên suốt session:

| Key | Type | Khởi tạo | Cập nhật khi |
|-----|------|----------|-------------|
| `transcript` | `str` | `""` | Sau transcribe, hoặc user edit text area |
| `analysis` | `MeetingAnalysis \| None` | `None` | Sau analyze thành công |
| `audio_path` | `str \| None` | `None` | Sau upload file |

> **Lưu ý:** Streamlit re-run toàn bộ script mỗi khi user tương tác. `session_state` là cách duy nhất giữ data giữa các re-runs.

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
| Jira REST v3 | `POST /rest/api/3/issue` | Bearer `JIRA_API_TOKEN` | Issue fields (project, summary, type, priority, parent) | `{"key": "MEET-1"}` |

Tất cả API calls có error handling + retry logic (xem [architecture.md](architecture.md)).
