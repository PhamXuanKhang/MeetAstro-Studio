# API Reference

FastAPI endpoints, data models, and service interfaces.

---

## Base URL

```
http://localhost:8000/api/v1
```

---

## REST Endpoints

### Health Check

```
GET /api/v1/health
```

Check API and database connectivity.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected"
}
```

---

### Meetings

#### List Meetings

```
GET /api/v1/meetings
```

Query params:
- `user_id` (optional): Filter by user

**Response:**
```json
{
  "meetings": [
    {
      "id": "uuid",
      "title": "Sprint Planning",
      "status": "draft",
      "created_at": "2026-04-24T10:00:00Z"
    }
  ]
}
```

#### Create Meeting

```
POST /api/v1/meetings
```

**Request:**
```json
{
  "title": "Sprint Planning",
  "user_id": "default_user"
}
```

**Response:**
```json
{
  "id": "uuid",
  "title": "Sprint Planning",
  "status": "pending"
}
```

#### Get Meeting

```
GET /api/v1/meetings/{meeting_id}
```

**Response:**
```json
{
  "id": "uuid",
  "title": "Sprint Planning",
  "audio_path": "/data/recordings/uuid.wav",
  "status": "draft",
  "celery_task_id": "task-uuid",
  "created_at": "2026-04-24T10:00:00Z"
}
```

#### Upload Audio

```
POST /api/v1/meetings/{meeting_id}/audio
```

**Request:** `multipart/form-data`
- `file`: Audio file (.wav, .mp3, .m4a)

Query params:
- `diarize` (bool, default: false): Enable speaker diarization
- `language` (str, default: "vi"): Transcription language

**Response:**
```json
{
  "meeting_id": "uuid",
  "audio_path": "/data/recordings/uuid.wav",
  "task_id": "celery-task-uuid",
  "status": "transcribing"
}
```

#### Delete Meeting

```
DELETE /api/v1/meetings/{meeting_id}
```

**Response:** `204 No Content`

---

### Transcriptions

#### Get Transcript

```
GET /api/v1/meetings/{meeting_id}/transcript
```

**Response:**
```json
{
  "id": "uuid",
  "meeting_id": "uuid",
  "raw_text": "Transcript content here...",
  "diarized_text": "[Speaker 0]: Hello...",
  "language": "vi",
  "char_count": 1234
}
```

#### Update Transcript

```
PATCH /api/v1/meetings/{meeting_id}/transcript
```

**Request:**
```json
{
  "raw_text": "Corrected transcript content..."
}
```

**Response:**
```json
{
  "id": "uuid",
  "raw_text": "Corrected transcript content...",
  "char_count": 1234
}
```

---

### Analysis

#### Trigger Analysis

```
POST /api/v1/meetings/{meeting_id}/analyze
```

Triggers Celery task to analyze transcript.

**Response:**
```json
{
  "meeting_id": "uuid",
  "task_id": "celery-task-uuid",
  "status": "analyzing"
}
```

#### Get Analysis Result

```
GET /api/v1/meetings/{meeting_id}/analysis
```

**Response:**
```json
{
  "id": "uuid",
  "meeting_id": "uuid",
  "summary": "Meeting summary...",
  "analysis_json": {
    "epics": [...],
    "summary": "...",
    "key_decisions": [...],
    "discussion_points": [...],
    "parking_lot": [...]
  },
  "overall_confidence": 0.85
}
```

---

### Review Items

#### List Review Items

```
GET /api/v1/meetings/{meeting_id}/review
```

Query params:
- `status` (optional): `draft`, `approved`, `rejected`

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "item_type": "task",
      "item_index": "0.1",
      "summary": "Implement API endpoint",
      "assignee": "John",
      "deadline": "2026-04-30",
      "priority": "High",
      "context": "Quoted from transcript...",
      "confidence": 0.85,
      "is_flagged": false,
      "review_status": "draft"
    }
  ]
}
```

#### Update Review Item

```
PATCH /api/v1/meetings/{meeting_id}/review/{item_id}
```

**Request:**
```json
{
  "edited_summary": "Updated summary",
  "edited_assignee": "Jane",
  "edited_deadline": "2026-05-01",
  "edited_priority": "Critical"
}
```

#### Approve Item

```
POST /api/v1/meetings/{meeting_id}/review/{item_id}/approve
```

**Response:**
```json
{
  "id": "uuid",
  "review_status": "approved"
}
```

#### Reject Item

```
POST /api/v1/meetings/{meeting_id}/review/{item_id}/reject
```

#### Approve All

```
POST /api/v1/meetings/{meeting_id}/review/approve_all
```

**Response:**
```json
{
  "approved_count": 5
}
```

---

### Jira Integration

#### Push to Jira

```
POST /api/v1/meetings/{meeting_id}/jira/push
```

Pushes approved review items to Jira.

**Response:**
```json
{
  "is_stub": false,
  "epic_keys": ["PROJ-1", "PROJ-2"],
  "epic_count": 2,
  "task_count": 5,
  "subtask_count": 3
}
```

If Jira credentials are missing:
```json
{
  "is_stub": true,
  "epic_keys": ["STUB-001"],
  "warning": "Jira credentials not configured"
}
```

---

### Exports

#### Export Markdown

```
GET /api/v1/meetings/{meeting_id}/export/markdown
```

**Response:** `text/markdown`

```markdown
# Meeting Summary

## Summary
...

## Epics

### Epic 1: Title
...
```

#### Export JSON

```
GET /api/v1/meetings/{meeting_id}/export/json
```

**Response:** `application/json`

#### Export CSV

```
GET /api/v1/meetings/{meeting_id}/export/csv
```

**Response:** `text/csv`

---

### Settings (Provider Configs)

#### List Providers

```
GET /api/v1/settings/providers
```

**Response:**
```json
{
  "providers": ["jira", "openai"]
}
```

#### Get Provider Config

```
GET /api/v1/settings/providers/{provider_name}
```

**Response:**
```json
{
  "provider_name": "jira",
  "active": true,
  "config": {
    "base_url": "https://company.atlassian.net",
    "project_key": "PROJ"
  }
}
```

Note: Sensitive fields (tokens, keys) are not returned.

#### Update Provider Config

```
PUT /api/v1/settings/providers/{provider_name}
```

**Request:**
```json
{
  "config": {
    "base_url": "https://company.atlassian.net",
    "email": "user@example.com",
    "api_token": "secret",
    "project_key": "PROJ"
  }
}
```

#### Delete Provider Config

```
DELETE /api/v1/settings/providers/{provider_name}
```

---

### Job Status

#### Get Job Status

```
GET /api/v1/jobs/{task_id}
```

Poll Celery task status.

**Response:**
```json
{
  "task_id": "uuid",
  "status": "SUCCESS",
  "result": {
    "transcript_id": "uuid",
    "char_count": 1234
  }
}
```

Status values: `PENDING`, `STARTED`, `SUCCESS`, `FAILURE`, `RETRY`

---

## Data Models

### Priority (Enum)

```python
class Priority(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
```

### ActionItem (Base)

| Field | Type | Description |
|-------|------|-------------|
| `summary` | `str` | Brief description |
| `assignee` | `str \| None` | Responsible person |
| `deadline` | `str \| None` | ISO date (YYYY-MM-DD) |
| `priority` | `Priority` | Priority level |
| `context` | `str` | Transcript excerpt |

### Subtask (extends ActionItem)

| Field | Type | Description |
|-------|------|-------------|
| `confidence` | `float` | Validation score (0.0-1.0) |
| `validation_notes` | `list[str]` | Validation feedback |

### Task (extends ActionItem)

| Field | Type | Description |
|-------|------|-------------|
| `subtasks` | `list[Subtask]` | Child subtasks |
| `confidence` | `float` | Validation score (0.0-1.0) |
| `validation_notes` | `list[str]` | Validation feedback |

### Epic

| Field | Type | Description |
|-------|------|-------------|
| `summary` | `str` | Epic name |
| `description` | `str` | Epic description |
| `tasks` | `list[Task]` | Child tasks |

### MeetingAnalysis

| Field | Type | Description |
|-------|------|-------------|
| `epics` | `list[Epic]` | Extracted epics |
| `summary` | `str` | Meeting summary |
| `key_decisions` | `list[str]` | Decisions made |
| `discussion_points` | `list[str]` | Main topics |
| `parking_lot` | `list[str]` | Deferred items |
| `created_at` | `datetime` | Analysis timestamp |

Methods:
- `to_dict() -> dict`
- `from_dict(data: dict) -> MeetingAnalysis`
- `to_json() -> str`
- `from_json(s: str) -> MeetingAnalysis`

### ReviewItem

| Field | Type | Description |
|-------|------|-------------|
| `id` | `UUID` | Primary key |
| `meeting_id` | `UUID` | Parent meeting |
| `item_type` | `str` | `epic`, `task`, `subtask` |
| `item_index` | `str` | Hierarchy index (e.g., "0.1.2") |
| `summary` | `str` | AI-generated summary |
| `assignee` | `str \| None` | AI-extracted assignee |
| `deadline` | `date \| None` | AI-extracted deadline |
| `priority` | `str \| None` | Priority level |
| `context` | `str \| None` | Transcript excerpt |
| `confidence` | `float` | Validation score |
| `is_flagged` | `bool` | Needs attention |
| `review_status` | `str` | `draft`, `approved`, `rejected` |
| `edited_*` | Various | User-edited fields |

---

## Provider Interfaces

### BaseAnalyzer (ABC)

```python
from abc import ABC, abstractmethod
from src.schema import MeetingAnalysis

class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, transcript: str) -> MeetingAnalysis:
        """
        Analyze transcript and extract structured action items.
        
        Args:
            transcript: Meeting transcript text.
            
        Returns:
            MeetingAnalysis with epics, tasks, subtasks.
            
        Raises:
            ValueError: Empty transcript.
            RuntimeError: API failure.
        """
        pass
```

### BaseTranscriber (ABC)

```python
class BaseTranscriber(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str, language: str = "vi") -> str:
        """
        Transcribe audio file to text.
        
        Args:
            audio_path: Path to audio file.
            language: Language code (default: "vi").
            
        Returns:
            Transcript text.
            
        Raises:
            FileNotFoundError: Audio file not found.
            RuntimeError: Transcription failure.
        """
        pass
```

### OpenAIAnalyzer

Implementation using GPT-4o with JSON mode.

```python
class OpenAIAnalyzer(BaseAnalyzer):
    def __init__(self, api_key: str = OPENAI_API_KEY, model: str = OPENAI_MODEL):
        ...
    
    def analyze(self, transcript: str) -> MeetingAnalysis:
        ...
```

Features:
- System prompt from `src/prompts/extract_action_items.md`
- JSON mode: `response_format={"type": "json_object"}`
- Retry: 3 attempts with exponential backoff (2s, 4s, 8s)

### OpenAITranscriber

Implementation using Whisper API.

```python
class OpenAITranscriber(BaseTranscriber):
    def __init__(self, api_key: str = OPENAI_API_KEY):
        ...
    
    def transcribe(self, audio_path: str, language: str = "vi") -> str:
        ...
```

Model: `whisper-1`

### OpenAIDiarizeTranscriber

Transcription with speaker labels.

```python
class OpenAIDiarizeTranscriber(BaseTranscriber):
    def transcribe(self, audio_path: str, language: str = "vi") -> str:
        # Returns: "[Speaker 0]: Hello...\n[Speaker 1]: Hi..."
```

---

## Service Functions

### transcription_service

```python
def transcribe(audio_path: str, language: str = "vi") -> str
def transcribe_diarized(audio_path: str, language: str = "vi") -> str
def transcribe_chunks(chunk_paths: list[str], language: str = "vi") -> str
```

### analysis_service

```python
def analyze(transcript: str) -> MeetingAnalysis
```

Orchestrates: validation -> OpenAIAnalyzer -> extraction -> summarization

### jira_service

```python
def push_analysis_to_jira(
    analysis: MeetingAnalysis,
    client: JiraClient | None = None
) -> JiraPushResult
```

Returns: `JiraPushResult(is_stub, epic_keys, epic_count, task_count, subtask_count)`

### recording_service

```python
def start_recording(output_path: str | None = None) -> str
def stop_recording() -> str
def is_recording() -> bool
def elapsed_seconds() -> float
def get_completed_chunks() -> list[str]
```

### validation_service

```python
def validate_action_items(
    ai_items: list[dict],
    rule_items: list[dict],
    transcript: str
) -> tuple[list[dict], dict]
```

Returns: `(items_with_confidence, metrics_dict)`

---

## GPT-4o JSON Schema

Expected output format from analysis:

```json
{
  "summary": "Meeting summary (2-4 sentences)",
  "epics": [
    {
      "summary": "Epic name",
      "description": "Epic description",
      "tasks": [
        {
          "summary": "Task name",
          "assignee": "Person name | null",
          "deadline": "YYYY-MM-DD | null",
          "priority": "Critical | High | Medium | Low",
          "context": "Transcript excerpt",
          "subtasks": [
            {
              "summary": "Subtask name",
              "assignee": "Person name | null",
              "deadline": "YYYY-MM-DD | null",
              "priority": "Critical | High | Medium | Low",
              "context": "Transcript excerpt"
            }
          ]
        }
      ]
    }
  ]
}
```
