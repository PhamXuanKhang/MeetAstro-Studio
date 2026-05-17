# Glossary

Terms and concepts used in the AI Meeting Assistant project.

---

## Project-Specific Terms

### Action Item
A concrete task extracted from a meeting transcript. Has assignee, deadline, priority, and context. Maps to Jira issues.

### Analysis
The process of extracting structured information (Epics, Tasks, Subtasks) from a transcript using GPT-4o.

### Confidence Score
A numerical score (0.0 to 1.0) indicating how reliable an extracted action item is. Calculated by cross-validating AI output with rule-based extraction.

### Diarization
Speaker identification in audio transcription. Output format: `[Speaker 0]: Hello...`

### Epic
A high-level theme or major decision from a meeting. Contains multiple Tasks. Maps to Jira Epic issue type.

### Flagged Item
A ReviewItem with low confidence score that requires user attention. Threshold: `CONFIDENCE_LOW_THRESHOLD` (default: 0.4).

### Human-in-the-Loop (HITL)
The review step where users approve, edit, or reject AI-extracted action items before pushing to Jira.

### Meeting Analysis
The complete structured output from GPT-4o containing: summary, epics (with tasks/subtasks), key_decisions, discussion_points, parking_lot.

### Meeting Record
A stored meeting with metadata: title, audio_path, transcript, analysis, timestamps.

### Parking Lot
Items mentioned in a meeting but deferred for later discussion.

### Provider
An implementation of a specific AI capability (analyzer, transcriber). Uses Strategy Pattern with ABC base classes.

### Review Item
A flattened action item (Epic/Task/Subtask) stored in the database for human review. Has status: draft, approved, rejected.

### Review Status
The state of a ReviewItem: `draft` (pending review), `approved` (ready for Jira), `rejected` (excluded from Jira).

### Stub Mode
JiraClient behavior when credentials are missing. Returns fake keys (`STUB-001`) without making real API calls.

### Subtask
A smaller action within a Task. Has same fields as Task but is a child item.

### Task
A specific action item assigned to someone. Has: summary, assignee, deadline, priority, context, subtasks.

### Transcript
Text output from speech-to-text conversion of audio. Can be plain text or diarized (with speaker labels).

### Validation
Cross-checking AI-extracted items against rule-based extraction to compute confidence scores.

---

## Technical Terms

### ABC (Abstract Base Class)
Python pattern for defining interfaces. Used for BaseAnalyzer and BaseTranscriber.

### Alembic
Database migration tool for SQLAlchemy. Manages PostgreSQL schema changes.

### asyncpg
Async PostgreSQL driver for Python. Used with SQLAlchemy async.

### Celery
Distributed task queue for Python. Handles background processing of transcription, analysis, and Jira push.

### Fernet
Symmetric encryption algorithm from cryptography library. Used for encrypting provider credentials.

### FastAPI
Modern Python web framework. Powers the backend API.

### Flet
Python UI framework for building desktop apps. Powers the frontend.

### httpx
Modern HTTP client for Python. Used by frontend to call backend API.

### JSON Mode
OpenAI API feature that forces structured JSON output. Used with GPT-4o for reliable parsing.

### pysysaudio
Library for capturing system audio on Windows. Used for meeting recording.

### Redis
In-memory data store. Used as Celery broker and result backend.

### sounddevice
Python library for audio I/O. Used for microphone capture.

### SQLAlchemy
Python ORM (Object-Relational Mapping). Used for PostgreSQL database operations.

### Strategy Pattern
Design pattern where algorithms are encapsulated in interchangeable classes. Providers implement this.

### Whisper API
OpenAI's speech-to-text API. Used for transcription.

---

## API & Integration Terms

### Basic Auth
HTTP authentication using username:password. Used for Jira API (email + API token).

### Bearer Token
HTTP authentication using `Authorization: Bearer <token>`. Used for OpenAI API.

### CRUD
Create, Read, Update, Delete - standard database operations.

### Endpoint
A specific URL path in the API (e.g., `/api/v1/meetings`).

### Jira REST API v3
Atlassian's API for programmatic Jira access. Used for creating issues.

### Rate Limiting
Restricting the number of API requests per time period.

---

## Data Model Terms

### UUID
Universally Unique Identifier. Used as primary keys in all tables.

### JSONB
PostgreSQL binary JSON type. Used for storing analysis_json.

### TIMESTAMPTZ
PostgreSQL timestamp with timezone. Used for created_at, updated_at.

### FK (Foreign Key)
Database constraint linking tables. All child tables FK to meetings.

---

## Process Terms

### Pipeline
The sequence: audio upload -> transcription -> analysis -> review -> Jira push.

### Polling
Frontend technique of repeatedly checking task status until completion.

### Retry
Automatic re-execution of failed tasks after a delay.

### Worker
A Celery process that executes background tasks.

---

## Abbreviations

| Abbrev | Full Term |
|--------|-----------|
| API | Application Programming Interface |
| CRUD | Create, Read, Update, Delete |
| DB | Database |
| E2E | End-to-End |
| FK | Foreign Key |
| HITL | Human-in-the-Loop |
| JSON | JavaScript Object Notation |
| JWT | JSON Web Token |
| LLM | Large Language Model |
| MVP | Minimum Viable Product |
| ORM | Object-Relational Mapping |
| PK | Primary Key |
| PR | Pull Request |
| REST | Representational State Transfer |
| STT | Speech-to-Text |
| TBD | To Be Determined |
| UI | User Interface |
| UUID | Universally Unique Identifier |
| VPS | Virtual Private Server |
| WER | Word Error Rate |
