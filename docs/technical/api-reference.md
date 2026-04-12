# API Reference

Public interfaces, function signatures, và schemas.

---

## Data Models — `src/schema.py`

### Priority (Enum)

```python
class Priority(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
```

### ActionItem (dataclass)

Base class cho Task và Subtask.

| Field | Type | Description |
|-------|------|-------------|
| `summary` | `str` | Mô tả ngắn gọn action item |
| `assignee` | `str \| None` | Người chịu trách nhiệm |
| `deadline` | `str \| None` | Ngày hạn (ISO: `YYYY-MM-DD`) |
| `priority` | `Priority` | Mức độ ưu tiên |
| `context` | `str` | Trích dẫn từ transcript |

### Subtask (extends ActionItem)

Kế thừa toàn bộ fields từ ActionItem.

Methods: `to_dict() → dict`, `from_dict(data: dict) → Subtask`

### Task (extends ActionItem)

| Field | Type | Description |
|-------|------|-------------|
| *(kế thừa ActionItem)* | | |
| `subtasks` | `list[Subtask]` | Danh sách subtasks (default: `[]`) |

Methods: `to_dict() → dict`, `from_dict(data: dict) → Task`

### Epic

| Field | Type | Description |
|-------|------|-------------|
| `summary` | `str` | Tên Epic ngắn gọn |
| `description` | `str` | Mô tả chi tiết |
| `tasks` | `list[Task]` | Danh sách tasks (default: `[]`) |

Methods: `to_dict() → dict`, `from_dict(data: dict) → Epic`

### MeetingAnalysis

| Field | Type | Description |
|-------|------|-------------|
| `epics` | `list[Epic]` | Các chủ đề / quyết định lớn |
| `summary` | `str` | Tóm tắt cuộc họp |
| `created_at` | `datetime` | Thời điểm phân tích |

Methods:
- `to_dict() → dict` / `from_dict(data: dict) → MeetingAnalysis`
- `to_json() → str` / `from_json(s: str) → MeetingAnalysis`

### MeetingRecord

| Field | Type | Description |
|-------|------|-------------|
| `title` | `str` | Tên cuộc họp |
| `transcript` | `str` | Nội dung transcript |
| `id` | `int \| None` | DB primary key |
| `audio_path` | `str \| None` | Đường dẫn file audio |
| `analysis` | `MeetingAnalysis \| None` | Kết quả phân tích |
| `created_at` | `datetime` | Thời điểm tạo |
| `updated_at` | `datetime` | Thời điểm cập nhật |

Methods: `to_dict() → dict`

---

## Providers — `src/providers/`

### BaseAnalyzer (ABC)

```python
class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, transcript: str) -> MeetingAnalysis: ...
```

### BaseTranscriber (ABC)

```python
class BaseTranscriber(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str, language: str = "vi") -> str: ...
```

### OpenAIAnalyzer

```python
class OpenAIAnalyzer(BaseAnalyzer):
    def __init__(self, api_key: str = OPENAI_API_KEY, model: str = OPENAI_MODEL) -> None
    def analyze(self, transcript: str) -> MeetingAnalysis
```

- GPT-4o với `response_format={"type": "json_object"}`
- System prompt từ `src/prompts/extract_action_items.md`
- Retry: 3 lần, exponential backoff (2s, 4s, 8s)
- Raises: `ValueError` (JSON parse fail), `RuntimeError` (3 lần đều fail)

### OpenAITranscriber

```python
class OpenAITranscriber(BaseTranscriber):
    def __init__(self, api_key: str = OPENAI_API_KEY) -> None
    def transcribe(self, audio_path: str, language: str = "vi") -> str
```

- Whisper API `model="whisper-1"`

### LocalTranscriber

```python
class LocalTranscriber(BaseTranscriber):
    def __init__(self, model_name: str = WHISPER_LOCAL_MODEL) -> None
    def transcribe(self, audio_path: str, language: str = "vi") -> str
```

- Local Whisper model (default: `base`)

---

## Services — `src/services/`

### transcription_service

```python
def transcribe(audio_path: str, language: str = "vi") -> str
```

Fallback chain: OpenAITranscriber → LocalTranscriber → RuntimeError.

### analysis_service

```python
def analyze(transcript: str) -> MeetingAnalysis
```

Validate input → OpenAIAnalyzer → return MeetingAnalysis.
Raises: `ValueError` (empty transcript).

---

## Modules — `src/modules/`

### database

```python
def init_db(db_path: str | None = None) -> None
def create_meeting(record: MeetingRecord, db_path: str | None = None) -> int
def get_meeting(meeting_id: int, db_path: str | None = None) -> MeetingRecord | None
def list_meetings(db_path: str | None = None) -> list[MeetingRecord]
def update_meeting(record: MeetingRecord, db_path: str | None = None) -> None
def delete_meeting(meeting_id: int, db_path: str | None = None) -> None
```

- SQLite stdlib (`sqlite3`)
- `db_path` parameter cho testing (override `DATABASE_URL`)
- `analysis` column: JSON string via `MeetingAnalysis.to_json()`

### exporter

```python
def export_markdown(analysis: MeetingAnalysis) -> str
def export_json(analysis: MeetingAnalysis) -> str
def export_csv(analysis: MeetingAnalysis) -> str
```

- Pure functions, stateless
- CSV: mỗi Task/Subtask = 1 row, columns: type, epic, task, summary, assignee, deadline, priority, context

### jira_client

```python
class JiraClient:
    def __init__(self, base_url: str, token: str, project_key: str) -> None
    @property
    def is_stub(self) -> bool
    def create_epic(self, epic: Epic) -> str        # returns issue key
    def create_task(self, task: Task, epic_key: str) -> str
    def create_subtask(self, subtask: Subtask, task_key: str) -> str
```

- Auto stub mode: nếu thiếu credentials → `is_stub = True`, return `"STUB-001"`
- Jira REST API v3: `POST /rest/api/3/issue`
- Auth: Bearer token

---

## Configuration — `src/config.py`

### Environment Variables

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `OPENAI_API_KEY` | `""` | Yes | OpenAI API key |
| `OPENAI_MODEL` | `"gpt-4o"` | No | Model cho analysis |
| `WHISPER_LOCAL_MODEL` | `"base"` | No | Local Whisper model size |
| `DEFAULT_TRANSCRIPTION_LANGUAGE` | `"vi"` | No | Ngôn ngữ transcription |
| `DATABASE_URL` | `"sqlite:///data/meetings.db"` | No | SQLite connection URL |
| `JIRA_BASE_URL` | `""` | No* | Jira instance URL |
| `JIRA_API_TOKEN` | `""` | No* | Jira API token |
| `JIRA_PROJECT_KEY` | `""` | No* | Jira project key |
| `LOG_LEVEL` | `"INFO"` | No | Logging level |

*\* Thiếu Jira vars → JiraClient chạy stub mode.*

### Logger

```python
def get_logger(name: str) -> logging.Logger
```

Format: `2026-04-12 10:30:00 [INFO] src.services.transcription_service — message`

---

## GPT-4o JSON Schema (Output)

Schema mà OpenAI GPT-4o trả về (xem `src/prompts/extract_action_items.md`):

```json
{
  "summary": "string — tóm tắt cuộc họp",
  "epics": [
    {
      "summary": "string",
      "description": "string",
      "tasks": [
        {
          "summary": "string",
          "assignee": "string | null",
          "deadline": "YYYY-MM-DD | null",
          "priority": "Critical | High | Medium | Low",
          "context": "string — trích dẫn transcript",
          "subtasks": [
            {
              "summary": "string",
              "assignee": "string | null",
              "deadline": "YYYY-MM-DD | null",
              "priority": "Critical | High | Medium | Low",
              "context": "string"
            }
          ]
        }
      ]
    }
  ]
}
```
