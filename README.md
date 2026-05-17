# AI Meeting Assistant

Convert meeting audio into structured action items (Epic -> Task -> Subtask) and push them to Jira with a human review loop.

## Overview

AI Meeting Assistant automates meeting documentation by:
1. **Recording** system audio + microphone or uploading audio/video files from the Electron app
2. **Transcribing** via OpenAI Whisper API or optional WhisperLiveKit
3. **Analyzing** via GPT-4o to extract Epic/Task/Subtask
4. **Reviewing** with human-in-the-loop approval
5. **Pushing** approved items to Jira

Architecture: **Electron desktop app** + **FastAPI backend** + **Celery worker** + **Redis** + **Supabase database/auth**.

## Project Structure

```
A20-App-089/
├── electron-app/                # Electron + React + TypeScript desktop app
├── src/                         # FastAPI backend and worker code
│   ├── api/                     # Routers + schemas
│   ├── workers/                 # Celery tasks
│   ├── services/                # Business logic
│   ├── providers/               # OpenAI / transcription integrations
│   ├── modules/                 # Jira, audio recorder, exporter
│   ├── db/                      # Supabase client + CRUD helpers
│   └── prompts/                 # LLM prompt templates
├── tests/                       # pytest test files
├── docs/                        # Documentation
├── docker-compose.yml           # Redis + API + worker for backend deploy
├── Dockerfile                   # Backend API/worker image
├── pyproject.toml               # Python package config
└── .env.example                 # Backend environment template
```

## Quick Start

### Prerequisites

- Python 3.11+ for backend
- Node.js 20+ for Electron app
- Docker Desktop with Linux engine enabled for backend deploy
- Supabase project with app tables configured
- `uv` or `pip`

### 1. Backend setup

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[all]"
```

Or with `uv`:

```bash
uv venv
.\.venv\Scripts\Activate.ps1
uv pip install -e ".[all]"
```

### 2. Configure backend environment

```bash
cp .env.example .env
```

Fill in at least:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `OPENAI_API_KEY`
- `APP_SECRET_KEY`

Optional:
- `JIRA_*` variables for Jira integration
- `WHISPER_LIVEKIT_URL` for self-hosted diarization/streaming

### 3. Start backend with Docker

```bash
docker compose up --build
```

This starts:
- **Redis** on the internal Docker network
- **FastAPI** on container port `8000`
- **Celery Worker** using Redis broker/result backend

The API health endpoint is `/api/v1/health`.

### 4. Start Electron app

```bash
cd electron-app
npm install
npm run dev
```

For a production desktop build:

```bash
cd electron-app
npm run build
```

## Local Backend Dev Mode

```bash
# Start Redis only
 docker compose up redis -d

# Run API with hot reload
uvicorn src.api.main:app --reload --port 8000

# Run Celery worker in another terminal
celery -A src.workers.celery_app worker -Q default --loglevel=info
```

## Commands

| Command | Description |
|---------|-------------|
| `uv pip install -e ".[server]"` | Install backend dependencies |
| `uv pip install -e ".[dev]"` | Install dev tools |
| `uv pip install -e ".[all]"` | Install backend + dev dependencies |
| `pytest tests/ -v` | Run tests |
| `flake8 . --max-line-length=100` | Lint Python code |
| `mypy . --ignore-missing-imports` | Type check Python code |
| `cd electron-app && npm run typecheck` | Type check Electron app |
| `cd electron-app && npm run build` | Build Electron desktop app |

## Workflow

```
Electron app
  -> Supabase SDK for auth and direct data views
  -> FastAPI /api/v1 for upload, jobs, AI processing, Jira push
      -> Redis queue
      -> Celery worker
          -> OpenAI / WhisperLiveKit / Jira
          -> Supabase database
```

## Submit Scope

Current MVP submission scope:
- Electron desktop app for auth, recording/upload, transcript review, action-item review, Jira settings, and meeting history.
- FastAPI backend with Celery/Redis jobs for transcription, analysis, Jira push, website runtime, and Windows EXE download metadata.
- Supabase is the canonical database/auth runtime; local PostgreSQL/Alembic/Flet paths are legacy/prototype context only.
- Windows distribution target is `MeetAstro-Setup-*.exe` published through GitHub Releases or mounted in `APP_DOWNLOADS_DIR`.

Known limitations before production:
- Jira assignee account mapping, advanced export templates, usage billing, and richer collaboration features are backlog items.
- Production deployment should restrict `CORS_ORIGINS` and rotate any credentials that were ever shared in logs, screenshots, or committed files.
- `.env` is local-only and must never be committed; use `.env.example` for placeholders.

Local verification before submit:
- `python -m pytest tests/test_website_runtime.py -v`
- `pytest tests/ -v`
- `cd electron-app && npm run typecheck`
- `cd website && npm run build`
- `git status --short` to confirm no secrets, `node_modules`, caches, or release artifacts are staged.

## Documentation

| Document | Purpose |
|----------|---------|
| [`docs/INDEX.md`](docs/INDEX.md) | Documentation index |
| [`docs/technical/api-reference.md`](docs/technical/api-reference.md) | API endpoints & schemas |
| [`docs/technical/supabase-schema.md`](docs/technical/supabase-schema.md) | Supabase Auth ownership + RLS |
| [`docs/product/spec.md`](docs/product/spec.md) | Product specification |
| [`docs/product/roadmap.md`](docs/product/roadmap.md) | Roadmap & milestones |

## Worklog

Update [WORKLOG.md](./WORKLOG.md) whenever your team makes a technical decision or changes direction.

## License

This project is for educational purposes (VinUni A20 - AI Thuc Chien 2026).
