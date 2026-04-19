# System Architecture

---

## High-level overview

```
┌──────────────────────────────────────────────────────────────┐
│                    Streamlit UI (app.py)                      │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │ Upload   │  │  Transcript  │  │  Analysis (Epic/Task/   │ │
│  │ Audio    │→ │  Text Area   │→ │  Subtask) + Actions     │ │
│  └──────────┘  └──────────────┘  └─────────────────────────┘ │
└──────────┬───────────┬───────────────────┬───────────────────┘
           │           │                   │
     ┌─────▼─────┐ ┌───▼────────┐   ┌─────▼──────────────┐
     │ Services  │ │ Modules    │   │ Modules            │
     │           │ │            │   │                    │
     │ transcr.  │ │ database   │   │ exporter + jira    │
     │ analysis  │ │ (SQLite)   │   │ (MD/JSON/CSV/Jira) │
     └─────┬─────┘ └────────────┘   └────────────────────┘
           │
     ┌─────▼──────────────────────┐
     │ Providers (Strategy)       │
     │                            │
     │ ┌────────────────────────┐ │
     │ │ BaseAnalyzer (ABC)     │ │
     │ │  └─ OpenAIAnalyzer     │ │
     │ ├────────────────────────┤ │
     │ │ BaseTranscriber (ABC)  │ │
     │ │  ├─ OpenAITranscriber  │ │
     │ │  └─ LocalTranscriber   │ │
     │ └────────────────────────┘ │
     └─────┬──────────────────────┘
           │
     ┌─────▼──────────────────────┐
     │ External APIs              │
     │  • OpenAI Whisper API      │
     │  • OpenAI GPT-4o           │
     │  • Jira REST API v3        │
     │  • Local Whisper model     │
     └────────────────────────────┘
```

---

## Layer architecture

Hệ thống chia thành 4 layers, mỗi layer chỉ phụ thuộc layer dưới:

| Layer | Thư mục | Vai trò | Phụ thuộc |
|-------|---------|---------|-----------|
| **UI** | `src/app.py` | Streamlit frontend, session state management | Services, Modules |
| **Services** | `src/services/` | Orchestration logic, fallback chain | Providers |
| **Modules** | `src/modules/` | Persistence (DB), export (file), integration (Jira) | Schema, Config |
| **Providers** | `src/providers/` | Strategy Pattern — gọi external AI APIs | External APIs |
| **Core** | `src/schema.py`, `src/config.py` | Data models, configuration | stdlib |

---

## Module map

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
    └── to_dict()
```

### `src/providers/` — Strategy Pattern

| File | Class | ABC | Method | Notes |
|------|-------|-----|--------|-------|
| `base_analyzer.py` | `BaseAnalyzer` | ✅ (ABC) | `analyze(transcript) → MeetingAnalysis` | Interface |
| `base_transcriber.py` | `BaseTranscriber` | ✅ (ABC) | `transcribe(audio_path, language) → str` | Interface |
| `openai_analyzer.py` | `OpenAIAnalyzer` | extends BaseAnalyzer | `analyze()` | GPT-4o + JSON mode, retry 3x exponential backoff |
| `openai_transcriber.py` | `OpenAITranscriber` | extends BaseTranscriber | `transcribe()` | Whisper API |
| `local_transcriber.py` | `LocalTranscriber` | extends BaseTranscriber | `transcribe()` | Local Whisper model (`base` default) |
| `mock_analyzer.py` | `MockAnalyzer` | extends BaseAnalyzer | `analyze()` | Mock data cho testing/fallback offline |

**Thêm provider mới:** Tạo class kế thừa ABC tương ứng + test file riêng.

### `src/services/` — Orchestration

| File | Function | Logic |
|------|----------|-------|
| `transcription_service.py` | `transcribe(audio_path, language)` | Fallback chain: `OpenAITranscriber` → (nếu fail + log warning) → `LocalTranscriber` → (nếu cả hai fail) → raise `RuntimeError` |
| `analysis_service.py` | `analyze(transcript)` | Validate input → `OpenAIAnalyzer().analyze()` → log kết quả |
| `jira_service.py` | `push_analysis_to_jira(analysis)` | Orchestrate Jira push theo thứ tự Epic → Task → Subtask, trả về summary counts |
| `recording_service.py` | `start_recording()`, `stop_recording()`, `is_recording()` | Orchestrate `AudioRecorder` singleton cho Streamlit |
| `extraction_service.py` | `rule_based_extraction(transcript)` | Regex-based action item extraction để cross-validate với AI |
| `validation_service.py` | `validate_action_items(ai_items, rule_items, transcript)` | Cross-validate AI vs rule-based, trả về confidence scores |
| `summarization_service.py` | `generate_summary(transcript)`, `generate_summary_stream()` | Async OpenAI call để tạo summary + key_decisions + parking_lot |

### `src/modules/` — Persistence & Integration

| File | Functions | Notes |
|------|-----------|-------|
| `database.py` | `init_db()`, `create_meeting()`, `get_meeting()`, `list_meetings()`, `update_meeting()`, `delete_meeting()` | SQLite stdlib, analysis serialize → JSON column |
| `database.py` | `get_provider_config()`, `set_provider_config()`, `list_provider_configs()`, `delete_provider_config()` | Provider configs CRUD với encryption |
| `exporter.py` | `export_markdown()`, `export_json()`, `export_csv()` | Stateless pure functions |
| `jira_client.py` | `JiraClient.create_epic()`, `.create_task()`, `.create_subtask()` | REST API v3, auto stub mode khi thiếu credentials |
| `audio_recorder.py` | `AudioRecorder.start()`, `.stop()`, `.is_recording`, `.get_completed_chunks()` | System audio capture (pysysaudio) + optional mic mixing, chunk rotation |
| `credential_vault.py` | `encrypt()`, `decrypt()` | Fernet symmetric encryption cho provider credentials |

### `src/config.py` — Configuration

Centralized config từ `.env` + logging setup. Một `get_logger(name)` function cho tất cả modules.

### `src/prompts/` — Prompt Templates

| File | Vai trò |
|------|---------|
| `extract_action_items.md` | System prompt tiếng Việt cho GPT-4o — output JSON schema Epic/Task/Subtask |

---

## Key design patterns

### 1. Strategy Pattern (Providers)

```python
# Thêm provider mới:
class GeminiAnalyzer(BaseAnalyzer):
    def analyze(self, transcript: str) -> MeetingAnalysis:
        # ... implement
```

Tất cả providers implement cùng ABC interface → services chọn provider tại runtime.

### 2. Fallback Chain (Transcription)

```
User upload audio
    │
    ▼
OpenAITranscriber.transcribe()
    │
    ├── ✅ Success → return transcript
    │
    └── ❌ Exception → log warning
                           │
                           ▼
                    LocalTranscriber.transcribe()
                           │
                           ├── ✅ Success → return transcript
                           │
                           └── ❌ Exception → raise RuntimeError
```

### 3. Structured Output (JSON Mode)

GPT-4o nhận system prompt (tiếng Việt) + transcript → trả JSON theo schema:
```json
{
  "summary": "...",
  "epics": [{
    "summary": "...", "description": "...",
    "tasks": [{
      "summary": "...", "assignee": "...", "deadline": "YYYY-MM-DD",
      "priority": "High", "context": "trích dẫn transcript",
      "subtasks": [...]
    }]
  }]
}
```
Parse bằng `MeetingAnalysis.from_dict()`.

### 4. Stub Pattern (Jira)

`JiraClient` tự detect thiếu credentials → `is_stub = True` → trả fake key `"STUB-001"` + log warning. Code production-ready, chỉ cần fill `.env`.
