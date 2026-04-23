# AI Meeting Assistant

Convert meeting audio into structured action items (Epic -> Task -> Subtask) and push them to Jira with a human review loop.

This repo is **HTTP-only**: the Flet desktop app talks to a FastAPI backend (with Celery + Postgres + Redis).

## Structure

```
├── frontend/                # Flet desktop app (HTTP client)
├── src/                     # FastAPI, services, providers, schema
├── tests/                   # pytest
├── docs/                    # Technical and product docs
├── scripts/                 # Hook setup + logging
├── docker-compose.yml       # Postgres + Redis + API + worker
├── requirements.txt         # Full dev/runtime dependencies
├── requirements-server.txt  # Server + worker only
├── .env.example
```

## Quick Start (Windows-first)

### 1) Configure environment

```bash
cp .env.example .env
```

Fill in at least `OPENAI_API_KEY` and update `API_BASE_URL` if your API runs elsewhere.

### 2) Start backend (API + worker)

```bash
docker compose up --build
```

This starts Postgres, Redis, migrations, the API, and the Celery worker.

### 3) Start the Flet app

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
pip install -r frontend\requirements.txt

python frontend\main.py
```

## Weekly Journal

Update [JOURNAL.md](./JOURNAL.md) at the end of each week with product learnings and decisions.

## Worklog

Update [WORKLOG.md](./WORKLOG.md) whenever your team makes a technical decision or changes direction.

## AI Logging

Prompts and tool calls are logged automatically after you run `scripts/setup_hooks.sh`. See [AGENTS.md](./AGENTS.md).
