# Deployment & Setup

Current submit runtime: Electron desktop app + FastAPI server + Celery worker + Redis + Supabase.

---

## Prerequisites

- Python 3.11+ for backend
- Node.js 20+ for Electron and website builds
- Docker Desktop for the backend stack
- Supabase project with app tables/auth configured
- `uv` or `pip`

---

## Local Development Setup

```bash
uv venv
source .venv/Scripts/activate
uv pip install -e ".[all]"
cp .env.example .env
```

Fill at least:
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `OPENAI_API_KEY`
- `APP_SECRET_KEY`

Optional:
- `SUPABASE_ANON_KEY` for Electron auth
- `JIRA_*` for real Jira push
- `WHISPER_LIVEKIT_URL` for self-hosted streaming/diarization

---

## Backend with Docker

```bash
docker compose up --build
```

Services:
- **Redis**: broker/result backend
- **FastAPI**: `/api/v1/*`, health at `/api/v1/health`, landing page at `/`
- **Celery worker**: queue `default`

Supabase is external; Docker Compose does not start PostgreSQL or Alembic migrations for the active runtime.

For local hot reload:

```bash
docker compose up redis -d
uvicorn src.api.main:app --reload --port 8000
celery -A src.workers.celery_app worker -Q default --loglevel=info
```

---

## Electron Desktop App

```bash
cd electron-app
npm install
npm run dev
```

Production Windows build:

```bash
cd electron-app
npm run build
```

The submission artifact is `MeetAstro-Setup-*.exe`. Release metadata is served through `/downloads/metadata.json`; the backend reads the latest GitHub Release first and can fall back to `APP_DOWNLOAD_URL` or a file mounted in `APP_DOWNLOADS_DIR`.

---

## Website / Landing Page

The backend Docker image builds `website/` and serves `website/dist` from FastAPI.

```bash
cd website
npm install
npm run build
```

Website media env vars:
- `VITE_HERO_IMAGE_URL` defaults to `/hero-preview.png`
- `VITE_DEMO_EMBED_URL` is optional; when empty the page shows the built-in product walkthrough placeholder

---

## Verification

```bash
pytest tests/ -v
cd electron-app && npm run typecheck
cd website && npm run build
```

Use sanitized environment values before sharing `docker compose config` output because Compose expands `.env` secrets.

---

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Backend service-role database access |
| `SUPABASE_ANON_KEY` | Electron | Frontend auth key |
| `OPENAI_API_KEY` | Yes | GPT-4o + Whisper API fallback |
| `APP_SECRET_KEY` | Yes | Fernet key for provider credential encryption |
| `CELERY_BROKER_URL` | No | Redis broker URL |
| `CELERY_RESULT_BACKEND` | No | Redis result backend URL |
| `WHISPER_LIVEKIT_URL` | No | Optional WhisperLiveKit WebSocket URL |
| `APP_DOWNLOAD_GITHUB_REPO` | No | GitHub repo used for latest EXE release metadata |
| `APP_DOWNLOAD_URL` | No | Explicit EXE download URL fallback |
| `APP_DOWNLOAD_FILENAME` | No | Local EXE filename fallback |
| `APP_DOWNLOADS_DIR` | No | Host folder mounted read-only to `/app/downloads` |
| `JIRA_BASE_URL` / `JIRA_EMAIL` / `JIRA_API_TOKEN` / `JIRA_PROJECT_KEY` | No | Jira integration; missing credentials keep Jira in stub mode |
