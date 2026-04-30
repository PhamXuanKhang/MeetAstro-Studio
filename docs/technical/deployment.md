# Deployment & Setup

Stack: Flet desktop app (HTTP client) + FastAPI server + Celery worker + PostgreSQL + Redis.

---

## Prerequisites

- Python 3.9+ (frontend), Python 3.11+ (server/Docker)
- [uv](https://docs.astral.sh/uv/) — package manager
- Docker Desktop — chạy PostgreSQL + Redis locally
- Git

---

## Local Development Setup

### 1) Clone repo

```bash
git clone https://github.com/a20-ai-thuc-chien/A20-App-089.git
cd A20-App-089
```

### 2) Tạo virtual environment

```bash
uv venv
# Windows
source .venv/Scripts/activate
# Linux/Mac
source .venv/bin/activate
```

### 3) Cài dependencies

```bash
# Cài tất cả (local dev — server + frontend + dev tools)
uv pip install -e ".[all]"

# Hoặc chỉ cài từng group cần thiết:
uv pip install -e ".[server]"    # Backend API + Celery + PostgreSQL
uv pip install -e ".[frontend]"  # Flet desktop app + audio recording
uv pip install -e ".[dev]"       # pytest + flake8 + mypy
```

### 4) Cấu hình environment

```bash
cp .env.example .env
```

Điền vào `.env`:
- `OPENAI_API_KEY` — bắt buộc
- `POSTGRES_URL` — URL PostgreSQL (để trống nếu dùng Docker compose mặc định)
- `APP_SECRET_KEY` — generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

### 5) Setup git hooks (tùy chọn)

```bash
bash scripts/setup_hooks.sh
```

---

## Chạy Backend (Docker — Recommended)

Khởi động toàn bộ stack (PostgreSQL + Redis + API server + Celery worker):

```bash
docker compose up --build
```

Services:
- **PostgreSQL**: `localhost:5432` (db=ai_meeting_db, user=ai_meeting)
- **Redis**: `localhost:6379`
- **API server**: `http://localhost:8000`
- **Celery worker**: tự khởi động, listen queue `default`
- **migrate**: tự chạy `alembic upgrade head` trước khi API start

### Supabase database mode

Revision `0003_supabase_rls_foundation.py` changes user-owned database rows to
Supabase Auth ownership (`user_id uuid references auth.users(id)`) and enables
RLS. To apply it against Supabase, set `POSTGRES_URL` to the Supabase
PostgreSQL connection string, then run:

```bash
alembic upgrade head
```

Do not put Supabase service-role keys or plaintext Jira credentials in desktop
or frontend configuration. Jira config rows are per-user and should store
credential fields encrypted.

### Chỉ khởi động infrastructure (không build app)

```bash
docker compose up postgres redis -d
```

Sau đó chạy API và worker thủ công (dev mode với hot reload):

```bash
uvicorn src.api.main:app --reload --port 8000
celery -A src.workers.celery_app worker -Q default --loglevel=info
```

---

## Chạy Flet Desktop App

```bash
python frontend/main.py
```

App kết nối tới `API_BASE_URL` (mặc định `http://localhost:8000`). Đảm bảo backend đang chạy.

---

## Tests & Verification

```bash
pytest tests/ -v
flake8 . --max-line-length=100 && mypy . --ignore-missing-imports && pytest tests/ -v
```

---

## Production Deploy (VPS)

### Backend (Docker trên VPS)

```bash
# Trên VPS
git clone ... && cd A20-App-089
cp .env.example .env  # fill production values
docker compose up -d --build
```

Cần cấu hình thêm:
- Reverse proxy (nginx) để expose port 8000
- SSL/TLS certificate
- Persistent volumes cho PostgreSQL data

### Frontend (Desktop .exe)

Build Flet app thành `.exe` bằng [flet pack](https://flet.dev/docs/publish):

```bash
uv pip install -e ".[frontend]"
flet pack frontend/main.py --name "AI Meeting Assistant"
```

Distribute file `.exe` cho người dùng. Cấu hình `API_BASE_URL` trong `.env` để trỏ về VPS.

---

## Environment Variables

Xem `.env.example` để biết đầy đủ. Các biến quan trọng:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | GPT-4o + Whisper API |
| `POSTGRES_URL` | Yes (server) | — | PostgreSQL connection string |
| `APP_SECRET_KEY` | Yes | — | Fernet key cho credential encryption |
| `CELERY_BROKER_URL` | No | `redis://localhost:6379/0` | Redis broker |
| `CELERY_RESULT_BACKEND` | No | `redis://localhost:6379/1` | Redis result backend |
| `API_BASE_URL` | No | `http://localhost:8000` | Server URL (Flet client) |
| `DEFAULT_TRANSCRIPTION_LANGUAGE` | No | `vi` | Ngôn ngữ Whisper |
| `JIRA_BASE_URL` | No | — | Jira instance URL (stub mode nếu thiếu) |
| `JIRA_EMAIL` | No | — | Jira Basic Auth email |
| `JIRA_API_TOKEN` | No | — | Jira API token |
| `JIRA_PROJECT_KEY` | No | — | Jira project key |
| `CONFIDENCE_LOW_THRESHOLD` | No | `0.4` | Threshold để flag review items |
| `LOG_LEVEL` | No | `INFO` | Logging level |
