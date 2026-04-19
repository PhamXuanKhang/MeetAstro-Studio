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

| Field | Type | Description |
|-------|------|-------------|
| *(kế thừa ActionItem)* | | |
| `confidence` | `float` | Confidence score từ validation (0.0–1.0) |
| `validation_notes` | `list[str]` | Ghi chú từ validation service |

Methods: `to_dict() → dict`, `from_dict(data: dict) → Subtask`

### Task (extends ActionItem)

| Field | Type | Description |
|-------|------|-------------|
| *(kế thừa ActionItem)* | | |
| `subtasks` | `list[Subtask]` | Danh sách subtasks (default: `[]`) |
| `confidence` | `float` | Confidence score từ validation (0.0–1.0) |
| `validation_notes` | `list[str]` | Ghi chú từ validation service |

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
| `key_decisions` | `list[str]` | Các quyết định chính đã chốt |
| `discussion_points` | `list[str]` | Các điểm thảo luận chính |
| `parking_lot` | `list[str]` | Các vấn đề tạm gác, chưa giải quyết |
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

### jira_service

```python
def push_analysis_to_jira(
  analysis: MeetingAnalysis,
  client: JiraClient | None = None,
) -> JiraPushResult
```

- Orchestrate theo thứ tự: Epic → Task → Subtask
- Trả về `JiraPushResult` gồm: `is_stub`, `epic_keys`, `epic_count`, `task_count`, `subtask_count`
- Raises: `ValueError` (analysis không có epics), `RuntimeError` (lỗi khi tạo issue)

### recording_service

```python
def start_recording(output_path: str | None = None) -> str
def stop_recording() -> str
def is_recording() -> bool
def elapsed_seconds() -> float
def get_completed_chunks() -> list[str]
```

- Orchestrate `AudioRecorder` singleton cho Streamlit
- `start_recording()` trả về WAV output path
- `get_completed_chunks()` trả về list đường dẫn các chunk đã hoàn thành

### extraction_service

```python
def rule_based_extraction(transcript: str) -> list[dict[str, Any]]
```

- Regex-based extraction để cross-validate với AI output
- Trả về list dicts với keys: `title`, `description`, `assignee`, `deadline`, `priority`, `context`

### validation_service

```python
def validate_action_items(
  ai_items: list[dict[str, Any]],
  rule_items: list[dict[str, Any]],
  transcript: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]
```

- Cross-validate AI items vs rule-based items
- Trả về `(validated_items_with_confidence, metrics_dict)`
- Metrics: `cross_validation_score`, `context_coherence_score`, `structural_validation_score`, `overall_confidence`

### summarization_service

```python
async def generate_summary(
  transcript: str,
  api_key: str = OPENAI_API_KEY,
  model: str = OPENAI_MODEL,
) -> dict[str, Any]

async def generate_summary_stream(
  transcript: str,
  api_key: str = OPENAI_API_KEY,
  model: str = OPENAI_MODEL,
) -> AsyncIterator[str]
```

- Async OpenAI call để sinh summary
- `generate_summary()` trả về dict: `summary`, `key_decisions`, `discussion_points`, `parking_lot_items`
- `generate_summary_stream()` yield từng token cho streaming UI

---

## Modules — `src/modules/`

### database

```python
# Meeting CRUD
def init_db(db_path: str | None = None) -> None
def create_meeting(record: MeetingRecord, db_path: str | None = None) -> int
def get_meeting(meeting_id: int, db_path: str | None = None) -> MeetingRecord | None
def list_meetings(db_path: str | None = None) -> list[MeetingRecord]
def update_meeting(record: MeetingRecord, db_path: str | None = None) -> None
def delete_meeting(meeting_id: int, db_path: str | None = None) -> None

# Provider Configs CRUD (encrypted)
def get_provider_config(provider_name: str, user_id: str = "default_user", db_path: str | None = None) -> dict | None
def set_provider_config(provider_name: str, config_dict: dict, user_id: str = "default_user", db_path: str | None = None) -> None
def list_provider_configs(user_id: str = "default_user", db_path: str | None = None) -> list[str]
def delete_provider_config(provider_name: str, user_id: str = "default_user", db_path: str | None = None) -> None
```

- SQLite stdlib (`sqlite3`)
- `db_path` parameter cho testing (override `DATABASE_URL`)
- `analysis` column: JSON string via `MeetingAnalysis.to_json()`
- Provider configs được encrypt bằng Fernet trước khi lưu

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
  def __init__(self, base_url: str, email: str, token: str, project_key: str) -> None
    @property
    def is_stub(self) -> bool
    def create_epic(self, epic: Epic) -> str        # returns issue key
    def create_task(self, task: Task, epic_key: str) -> str
    def create_subtask(self, subtask: Subtask, task_key: str) -> str
```

- Auto stub mode: nếu thiếu credentials → `is_stub = True`, return `"STUB-001"`
- Jira REST API v3: `POST /rest/api/3/issue`
- Auth: Basic Auth (`JIRA_EMAIL` + `JIRA_API_TOKEN`)
- Luồng runtime từ UI + sequence Epic → Task → Subtask: xem `jira-upload-flow.md`

### audio_recorder

```python
class AudioRecorder:
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        mic_enabled: bool = True,
        mic_gain: float = 3.0,
        sys_gain: float = 0.5,
        output_dir: str = "data/recordings",
        chunk_seconds: int = 60,
        on_chunk_complete: Callable[[str], None] | None = None,
    ) -> None

    @property
    def is_recording(self) -> bool
    @property
    def elapsed_seconds(self) -> float
    @property
    def output_path(self) -> str | None
    @property
    def error(self) -> str | None

    def start(self, output_path: str | None = None) -> str
    def stop(self) -> str
    def get_completed_chunks(self) -> list[str]
```

- Capture system audio via `pysysaudio`
- Optional mic mixing via `sounddevice`
- Chunk rotation mỗi `chunk_seconds` giây
- Background thread recording

### credential_vault

```python
def encrypt(plaintext: str) -> str
def decrypt(ciphertext: str) -> str
```

- Fernet symmetric encryption
- Key từ `APP_SECRET_KEY` trong config
- Dùng để encrypt provider credentials trong database

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
| `JIRA_EMAIL` | `""` | No* | Jira account email (for Basic Auth) |
| `JIRA_API_TOKEN` | `""` | No* | Jira API token |
| `JIRA_PROJECT_KEY` | `""` | No* | Jira project key |
| `AUDIO_SAMPLE_RATE` | `16000` | No | Sample rate cho audio recording |
| `AUDIO_CHANNELS` | `1` | No | Số kênh audio (mono/stereo) |
| `AUDIO_MIC_ENABLED` | `true` | No | Bật/tắt mic mixing |
| `AUDIO_MIC_GAIN` | `3.0` | No | Gain cho mic input |
| `AUDIO_SYS_GAIN` | `0.5` | No | Gain cho system audio |
| `AUDIO_OUTPUT_DIR` | `"data/recordings"` | No | Thư mục lưu file recording |
| `APP_SECRET_KEY` | `None` | No** | Fernet key cho credential encryption |
| `TRANSCRIPTION_CHUNK_SECONDS` | `60` | No | Độ dài chunk audio (giây) |
| `LOG_LEVEL` | `"INFO"` | No | Logging level |

*\* Thiếu Jira vars → JiraClient chạy stub mode.*
*\*\* Thiếu APP_SECRET_KEY → credential_vault raise ValueError.*

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
