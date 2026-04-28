# AI Meeting Assistant

Convert meeting audio into structured action items (Epic -> Task -> Subtask) and push them to Jira with a human review loop.

## Overview

AI Meeting Assistant automates meeting documentation by:
1. **Recording** system audio + microphone (or uploading audio files)
2. **Transcribing** via OpenAI Whisper API (with optional speaker diarization)
3. **Analyzing** via GPT-4o to extract Epic/Task/Subtask
4. **Reviewing** with human-in-the-loop approval before export
5. **Exporting** to Markdown/JSON/CSV or pushing directly to Jira

Architecture: **FastAPI backend** (Celery workers + PostgreSQL + Redis) + **Flet desktop app** (HTTP client).

## Project Structure

```
A20-App-089/
├── frontend/                   # Flet desktop app (HTTP client)
│   ├── main.py                 # Entry point
│   ├── app.py                  # App factory + routing
│   ├── core/                   # HttpBackend, AppState
│   ├── views/                  # UI pages
│   └── components/             # Sidebar, Topbar
├── src/                        # FastAPI backend
│   ├── api/                    # Routers + schemas
│   ├── workers/                # Celery tasks
│   ├── services/               # Business logic
│   ├── providers/              # OpenAI integrations
│   ├── modules/                # Jira, Audio, Exporter
│   ├── db/                     # SQLAlchemy + Alembic
│   └── prompts/                # LLM prompt templates
├── tests/                      # pytest test files
├── docs/                       # Documentation
│   ├── product/                # Canvas, Spec, Roadmap
│   ├── technical/              # Architecture, API, Deployment
│   └── evaluation/             # Metrics, Test plan
├── docker-compose.yml          # PostgreSQL + Redis + API + Worker
├── pyproject.toml              # Package config (uv)
└── .env.example                # Environment template
```

## Quick Start

### Prerequisites

- **Python 3.11+** (backend) / Python 3.9+ (frontend)
- **Docker Desktop** running with the Linux engine enabled (for PostgreSQL + Redis + API + worker)
- **Git**
- **uv** (preferred) or **pip** (both read dependencies from `pyproject.toml`)

### 1. Clone and Setup

```bash
git clone https://github.com/a20-ai-thuc-chien/A20-App-089.git
cd A20-App-089

# Create virtual environment (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies (all-in-one for local dev)
python -m pip install -e ".[all]"

# Or, if uv is installed
uv venv
.\.venv\Scripts\Activate.ps1
uv pip install -e ".[all]"
```

Dependencies are declared in `pyproject.toml`; this repo does not use a
`requirements.txt` file.

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and fill in:
- `OPENAI_API_KEY` (required) - your OpenAI API key
- `APP_SECRET_KEY` (required) - generate with:
  ```python
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- `JIRA_*` variables (optional) - for Jira integration

### 3. Start Backend (Docker)

```bash
docker compose up --build
```

This starts:
- **PostgreSQL** on `localhost:5432`
- **Redis** on `localhost:6379`
- **FastAPI** on `http://localhost:8000`
- **Celery Worker** (background)
- Auto-runs **Alembic migrations**

If Docker fails with a named-pipe error such as `open //./pipe/dockerDesktopLinuxEngine`,
start Docker Desktop, wait until the Linux engine is running, then retry:

```bash
docker context ls
docker --context desktop-linux ps
docker compose up --build
```

### 4. Start Desktop App

```bash
python frontend/main.py
```

The app connects to `http://localhost:8000` by default.

## Alternative: Dev Mode (without Docker)

```bash
# Start PostgreSQL + Redis only
docker compose up postgres redis -d

# Run API (hot reload)
uvicorn src.api.main:app --reload --port 8000

# Run Celery worker (separate terminal)
celery -A src.workers.celery_app worker -Q default --loglevel=info

# Run desktop app (separate terminal)
python frontend/main.py
```

## Commands

| Command | Description |
|---------|-------------|
| `uv pip install -e ".[server]"` | Install backend dependencies |
| `uv pip install -e ".[frontend]"` | Install frontend dependencies |
| `uv pip install -e ".[dev]"` | Install dev tools (pytest, flake8, mypy) |
| `uv pip install -e ".[all]"` | Install everything |
| `pytest tests/ -v` | Run tests |
| `flake8 . --max-line-length=100` | Lint code |
| `mypy . --ignore-missing-imports` | Type check |

## Documentation

| Document | Purpose |
|----------|---------|
| [`docs/INDEX.md`](docs/INDEX.md) | Documentation index |
| [`docs/technical/architecture.md`](docs/technical/architecture.md) | System architecture |
| [`docs/technical/api-reference.md`](docs/technical/api-reference.md) | API endpoints & schemas |
| [`docs/technical/deployment.md`](docs/technical/deployment.md) | Setup & deployment |
| [`docs/product/spec.md`](docs/product/spec.md) | Product specification |
| [`docs/product/roadmap.md`](docs/product/roadmap.md) | Roadmap & milestones |

## Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                     Desktop App (Flet)                          │
│                                                                 │
│  [Record/Upload] → [Transcribe] → [Analyze] → [Review] → [Push] │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP (httpx)
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI + Celery Workers                      │
│                                                                 │
│  POST /audio → transcribe_task (Whisper API)                    │
│            → analyze_task (GPT-4o JSON mode)                    │
│            → create ReviewItems (draft)                         │
│                                                                 │
│  POST /jira/push → jira_push_task (approved items only)         │
└─────────────────────────────────────────────────────────────────┘
```

## Weekly Journal

Update [JOURNAL.md](./JOURNAL.md) at the end of each week with product learnings and decisions.

## Worklog

Update [WORKLOG.md](./WORKLOG.md) whenever your team makes a technical decision or changes direction.

## AI Logging

Prompts and tool calls are logged automatically after you run `scripts/setup_hooks.sh`. See [AGENTS.md](./AGENTS.md).

## License

This project is for educational purposes (VinUni A20 - AI Thuc Chien 2026).
