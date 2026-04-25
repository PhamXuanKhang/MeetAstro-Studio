# Contributing Guide

Guidelines for contributing to AI Meeting Assistant.

---

## Development Setup

### Prerequisites

- Python 3.11+ (backend) / Python 3.9+ (frontend)
- Docker Desktop
- [uv](https://docs.astral.sh/uv/) package manager
- Git

### Initial Setup

```bash
# Clone repo
git clone https://github.com/a20-ai-thuc-chien/A20-App-089.git
cd A20-App-089

# Create virtual environment
uv venv
source .venv/Scripts/activate   # Windows
source .venv/bin/activate       # Linux/Mac

# Install all dependencies
uv pip install -e ".[all]"

# Copy environment template
cp .env.example .env
# Fill in OPENAI_API_KEY and APP_SECRET_KEY

# Start infrastructure
docker compose up postgres redis -d

# Run tests to verify setup
pytest tests/ -v
```

---

## Code Style

### Python Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Functions/variables | snake_case | `create_meeting`, `audio_path` |
| Classes | PascalCase | `MeetingAnalysis`, `OpenAIAnalyzer` |
| Constants | UPPER_CASE | `OPENAI_API_KEY`, `DEFAULT_LANGUAGE` |
| Type hints | Python 3.9+ style | `list[str]`, `Optional[str]` |

### Type Hints

Use Python 3.9+ style (not `str | int` union syntax for 3.9 compatibility):

```python
# Correct
def analyze(transcript: str, language: Optional[str] = None) -> MeetingAnalysis:
    ...

# Correct
def process_items(items: list[dict[str, Any]]) -> list[ReviewItem]:
    ...

# Avoid (requires Python 3.10+)
def analyze(transcript: str, language: str | None = None):
    ...
```

### Docstrings

Use Vietnamese for descriptions, English for technical terms:

```python
def analyze(self, transcript: str) -> MeetingAnalysis:
    """
    Phân tích transcript và trích xuất action items.
    
    Args:
        transcript: Nội dung transcript đã chuyển đổi từ audio.
        
    Returns:
        MeetingAnalysis chứa epics, tasks, subtasks.
        
    Raises:
        ValueError: Nếu transcript trống.
        RuntimeError: Nếu OpenAI API gọi thất bại 3 lần.
    """
```

### Logging

Use the project logger (never `print()`):

```python
from src.config import get_logger

logger = get_logger(__name__)

# Usage
logger.info("Transcription completed: %d characters", len(transcript))
logger.warning("Falling back to plain transcription")
logger.error("Failed to push to Jira: %s", str(e))
```

---

## Project Structure Rules

### Adding New Providers

New AI providers MUST:

1. **Extend the corresponding ABC:**
   ```python
   from src.providers.base_analyzer import BaseAnalyzer
   
   class GeminiAnalyzer(BaseAnalyzer):
       def analyze(self, transcript: str) -> MeetingAnalysis:
           ...
   ```

2. **Have a dedicated test file:**
   ```
   tests/test_gemini_analyzer.py
   ```

3. **Mock all external API calls in tests:**
   ```python
   @patch('src.providers.gemini_analyzer.GeminiClient')
   def test_analyze_success(self, mock_client):
       ...
   ```

### Adding New Services

Services in `src/services/` are orchestration logic:
- Pure functions when possible
- No direct database access (use CRUD functions)
- Error handling with specific exceptions

### Adding New API Endpoints

1. Create/update router in `src/api/routers/`
2. Add Pydantic schemas in `src/api/schemas/`
3. Register router in `src/api/main.py`
4. Add tests in `tests/`

---

## Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific file
pytest tests/test_analysis_service.py -v

# With coverage
pytest tests/ -v --cov=src --cov-report=term-missing
```

### Test Guidelines

1. **Mock all external APIs:**
   ```python
   @patch('openai.OpenAI')
   def test_transcribe(self, mock_openai):
       ...
   ```

2. **Use tmp_path for database tests:**
   ```python
   def test_create_meeting(tmp_path):
       db_path = str(tmp_path / "test.db")
       ...
   ```

3. **Test both success and failure cases:**
   ```python
   def test_analyze_success(self):
       ...
   
   def test_analyze_empty_transcript_raises(self):
       with pytest.raises(ValueError):
           analyze("")
   ```

---

## Verification Commands

Run before every commit:

```bash
# Quick check
flake8 . --max-line-length=100 && mypy . --ignore-missing-imports && pytest tests/ -v

# Or use the alias
./scripts/verify.sh  # if available
```

| Tool | Purpose | Pass Criteria |
|------|---------|---------------|
| flake8 | Code style | 0 warnings |
| mypy | Type checking | 0 errors |
| pytest | Unit tests | All passing |

---

## Git Workflow

### Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feat/description` | `feat/speaker-diarization` |
| Bug fix | `fix/description` | `fix/jira-assignee-mapping` |
| Documentation | `docs/description` | `docs/api-reference` |
| Refactor | `refactor/description` | `refactor/service-layer` |

### Commit Messages

Use conventional commits:

```
feat: add speaker diarization to transcription service
fix: handle null assignee in Jira payload
docs: update API reference with new endpoints
refactor: extract validation logic to service
test: add integration tests for Jira flow
```

### Pull Request Process

1. Create feature branch from `main`
2. Make changes with atomic commits
3. Run verification commands
4. Push and create PR
5. Request review
6. Squash and merge

---

## Documentation

### When to Update Docs

- New feature → update relevant technical docs
- API change → update `api-reference.md`
- Architecture change → update `architecture.md`
- Deployment change → update `deployment.md`

### Documentation Files

| File | Update When |
|------|-------------|
| `docs/technical/architecture.md` | Adding new modules/services |
| `docs/technical/api-reference.md` | Adding/changing API endpoints |
| `docs/technical/data-flow.md` | Changing data pipeline |
| `docs/llms.txt` | Any significant change |
| `CLAUDE.md` | Project rules change |

---

## Common Patterns

### Error Handling

```python
from src.config import get_logger

logger = get_logger(__name__)

def transcribe(audio_path: str) -> str:
    try:
        result = whisper_api.transcribe(audio_path)
        return result
    except OpenAIError as e:
        logger.error("Whisper API failed: %s", str(e))
        raise RuntimeError(f"Transcription failed: {e}") from e
```

### Async Database Operations

```python
from src.db.session import get_async_session
from src.db.crud import meeting_crud

async def create_and_process(title: str):
    async with get_async_session() as db:
        meeting = await meeting_crud.create_meeting(db, title, "user")
        await db.commit()
        return meeting
```

### Celery Tasks

```python
from src.workers.celery_app import celery_app
from src.config import get_logger

logger = get_logger(__name__)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def process_audio(self, meeting_id: str, audio_path: str):
    try:
        # ... processing logic
        return {"status": "success"}
    except Exception as e:
        logger.error("Task failed: %s", str(e))
        raise self.retry(exc=e)
```

---

## Questions?

- Check existing docs in `docs/`
- Review `CLAUDE.md` for project rules
- Ask in team chat/issues
