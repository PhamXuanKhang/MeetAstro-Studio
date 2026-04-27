# Celery Tasks

Documentation for background task processing with Celery.

---

## Overview

AI Meeting Assistant uses **Celery** with **Redis** for asynchronous task processing. Heavy operations (transcription, analysis, Jira push) run as background tasks to avoid blocking the API.

Architecture:
```
FastAPI API  ->  Redis Broker  ->  Celery Worker  ->  PostgreSQL
     |                                   |
     |<---- Poll task status ------------|
```

---

## Setup

### Configuration

```python
# src/workers/celery_app.py
from celery import Celery

celery_app = Celery(
    "ai_meeting",
    broker=settings.CELERY_BROKER_URL,      # redis://localhost:6379/0
    backend=settings.CELERY_RESULT_BACKEND,  # redis://localhost:6379/1
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "src.workers.tasks.*": {"queue": "default"},
    },
)
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis broker URL |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Redis result backend URL |

### Running the Worker

```bash
# Development (single worker, verbose logging)
celery -A src.workers.celery_app worker -Q default --loglevel=info

# Production (multiple workers, concurrency)
celery -A src.workers.celery_app worker -Q default --concurrency=4 --loglevel=warning

# With Docker
docker compose up worker
```

---

## Tasks

### run_pipeline

Orchestrates the full transcription + analysis pipeline.

**Location:** `src/workers/pipeline.py`

```python
@celery_app.task(bind=True)
def run_pipeline(
    self,
    meeting_id: str,
    audio_path: str,
    diarize: bool = False,
    language: str = "vi"
) -> dict:
    """
    Full pipeline: transcribe -> analyze.
    
    Args:
        meeting_id: UUID of the meeting
        audio_path: Path to audio file on server
        diarize: Enable speaker diarization
        language: Transcription language code
        
    Returns:
        {
            "meeting_id": "uuid",
            "transcript_id": "uuid",
            "analysis_id": "uuid",
            "review_item_count": 5,
            "flagged_count": 1
        }
    """
```

**Flow:**
1. Update meeting status to `transcribing`
2. Call `transcribe_audio` task
3. Update meeting status to `analyzing`
4. Call `analyze_transcript` task
5. Update meeting status to `draft`
6. Return summary

### transcribe_audio

Transcribes audio file using OpenAI Whisper API.

**Location:** `src/workers/tasks/transcribe_task.py`

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def transcribe_audio(
    self,
    meeting_id: str,
    audio_path: str,
    diarize: bool = False,
    language: str = "vi"
) -> dict:
    """
    Transcribe audio file.
    
    Args:
        meeting_id: UUID of the meeting
        audio_path: Path to audio file
        diarize: Enable speaker diarization
        language: Transcription language
        
    Returns:
        {
            "transcript_id": "uuid",
            "char_count": 1234,
            "diarized": false
        }
        
    Raises:
        Retry on transient errors (network, rate limit)
        Fail on permanent errors (file not found, invalid audio)
    """
```

**Features:**
- Retry 3 times with 5s delay on transient errors
- Fallback from diarization to plain transcription on failure
- Updates `Transcript` in PostgreSQL

### analyze_transcript

Analyzes transcript using GPT-4o.

**Location:** `src/workers/tasks/analyze_task.py`

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def analyze_transcript(
    self,
    meeting_id: str,
    transcript_id: str
) -> dict:
    """
    Analyze transcript and extract action items.
    
    Args:
        meeting_id: UUID of the meeting
        transcript_id: UUID of the transcript
        
    Returns:
        {
            "analysis_id": "uuid",
            "review_item_count": 5,
            "flagged_count": 1,
            "overall_confidence": 0.85
        }
    """
```

**Flow:**
1. Load transcript from database
2. Call `analysis_service.analyze()`:
   - GPT-4o structured output
   - Rule-based extraction (cross-validation)
   - Validation service (confidence scoring)
   - Summarization service
3. Create `AnalysisResult` in database
4. Flatten to `ReviewItem[]` (status=draft)
5. Flag low-confidence items

### push_to_jira

Pushes approved review items to Jira.

**Location:** `src/workers/tasks/jira_push_task.py`

```python
@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def push_to_jira(
    self,
    meeting_id: str
) -> dict:
    """
    Push approved items to Jira.
    
    Args:
        meeting_id: UUID of the meeting
        
    Returns:
        {
            "is_stub": false,
            "epic_keys": ["PROJ-1", "PROJ-2"],
            "epic_count": 2,
            "task_count": 5,
            "subtask_count": 3
        }
    """
```

**Flow:**
1. Load approved `ReviewItem[]` from database
2. Reconstruct `MeetingAnalysis` from approved items
3. Call `jira_service.push_analysis_to_jira()`
4. Update meeting status to `pushed`
5. Return summary with created issue keys

### cleanup_task

Cleanup old recordings and temporary files.

**Location:** `src/workers/tasks/cleanup_task.py`

```python
@celery_app.task
def cleanup_old_recordings(days: int = 30) -> dict:
    """
    Delete audio recordings older than N days.
    
    Returns:
        {
            "deleted_count": 10,
            "freed_bytes": 1024000
        }
    """
```

---

## Task States

| State | Description |
|-------|-------------|
| `PENDING` | Task queued, not yet started |
| `STARTED` | Worker picked up the task |
| `SUCCESS` | Task completed successfully |
| `FAILURE` | Task failed (check `result` for error) |
| `RETRY` | Task will retry after delay |
| `REVOKED` | Task was cancelled |

---

## Error Handling

### Retry Logic

Tasks use automatic retry for transient errors:

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def my_task(self, arg):
    try:
        # ... task logic
    except TransientError as e:
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
    except PermanentError as e:
        # Don't retry, fail immediately
        raise
```

### Error Types

| Error | Action | Example |
|-------|--------|---------|
| Network timeout | Retry | OpenAI API timeout |
| Rate limit | Retry with backoff | 429 Too Many Requests |
| Invalid input | Fail | Empty transcript |
| File not found | Fail | Audio file deleted |
| Parse error | Fail | Invalid JSON from GPT |

---

## Monitoring

### Task Status API

```
GET /api/v1/jobs/{job_id}
```

Response:
```json
{
  "job_id": "abc123",
  "state": "SUCCESS",
  "result": {
    "transcript_id": "uuid",
    "char_count": 1234
  },
  "error": null
}
```

### Celery Events

Monitor task events:

```bash
# Real-time event monitoring
celery -A src.workers.celery_app events

# Flower web UI (optional)
pip install flower
celery -A src.workers.celery_app flower --port=5555
```

### Logging

Tasks log to the standard logger:

```python
from src.config import get_logger

logger = get_logger(__name__)

@celery_app.task(bind=True)
def my_task(self, meeting_id):
    logger.info("Starting task for meeting %s", meeting_id)
    try:
        # ... logic
        logger.info("Task completed successfully")
    except Exception as e:
        logger.error("Task failed: %s", str(e))
        raise
```

---

## Frontend Integration

### Triggering Tasks

```python
# In API router
from src.workers.pipeline import run_pipeline

@router.post("/meetings/{meeting_id}/audio")
async def upload_audio(meeting_id: str, file: UploadFile):
    # Save file
    audio_path = save_audio(file)
    
    # Trigger async task
    task = run_pipeline.delay(meeting_id, audio_path, diarize=True)
    
    # Update meeting with task ID
    await update_meeting(meeting_id, celery_task_id=task.id)
    
    return {"job_id": task.id, "state": "PENDING"}
```

### Polling from Frontend

```python
# In frontend HTTP backend
def poll_job(self, job_id: str, interval: float = 1.0):
    while True:
        status = self.get_job_status(job_id)
        if status["state"] in ("SUCCESS", "FAILURE"):
            return status
        time.sleep(interval)
```

---

## Docker Configuration

In `docker-compose.yml`:

```yaml
services:
  worker:
    build: .
    command: celery -A src.workers.celery_app worker -Q default --loglevel=info
    depends_on:
      - redis
      - postgres
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
      - POSTGRES_URL=postgresql+asyncpg://...
    volumes:
      - ./data/recordings:/app/data/recordings
```

---

## Best Practices

1. **Idempotency**: Tasks should be safe to retry without side effects
2. **Timeout**: Set reasonable timeouts for external API calls
3. **Logging**: Log task start, completion, and errors
4. **Result cleanup**: Configure result backend TTL to avoid memory issues
5. **Queue isolation**: Use separate queues for different task priorities

```python
# Example: Task with timeout and result expiry
@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    time_limit=300,  # 5 minute hard limit
    soft_time_limit=240,  # 4 minute soft limit
    result_expires=3600,  # Result expires in 1 hour
)
def my_task(self, arg):
    ...
```
