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

### `src/schema.py` — Data Models

```
Priority (Enum) ─── Critical | High | Medium | Low
    │
ActionItem (dataclass) ─── summary, assignee, deadline, priority, context
    ├── Subtask (extends ActionItem)
    └── Task (extends ActionItem) ─── subtasks: list[Subtask]

Epic (dataclass) ─── summary, description, tasks: list[Task]

MeetingAnalysis (dataclass) ─── epics: list[Epic], summary, created_at
    └── to_dict() / from_dict() / to_json() / from_json()

MeetingRecord (dataclass) ─── id, title, audio_path, transcript, analysis, timestamps
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

**Thêm provider mới:** Tạo class kế thừa ABC tương ứng + test file riêng.

### `src/services/` — Orchestration

| File | Function | Logic |
|------|----------|-------|
| `transcription_service.py` | `transcribe(audio_path, language)` | Fallback chain: `OpenAITranscriber` → (nếu fail + log warning) → `LocalTranscriber` → (nếu cả hai fail) → raise `RuntimeError` |
| `analysis_service.py` | `analyze(transcript)` | Validate input → `OpenAIAnalyzer().analyze()` → log kết quả |
| `jira_service.py` | `push_analysis_to_jira(analysis)` | Orchestrate Jira push theo thứ tự Epic → Task → Subtask, trả về summary counts |

### `src/modules/` — Persistence & Integration

| File | Functions | Notes |
|------|-----------|-------|
| `database.py` | `init_db()`, `create_meeting()`, `get_meeting()`, `list_meetings()`, `update_meeting()`, `delete_meeting()` | SQLite stdlib, analysis serialize → JSON column |
| `exporter.py` | `export_markdown()`, `export_json()`, `export_csv()` | Stateless pure functions |
| `jira_client.py` | `JiraClient.create_epic()`, `.create_task()`, `.create_subtask()` | REST API v3, auto stub mode khi thiếu credentials |

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
