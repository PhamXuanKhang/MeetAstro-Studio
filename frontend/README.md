# Frontend (Flet)

Cross-platform desktop UI for the AI Meeting Assistant. The app is **HTTP-only** and talks to the FastAPI backend.

## Install

From the repo root:

```bash
# PowerShell venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Or use the existing conda env
conda activate meetingProject

# Frontend dependencies are declared in pyproject.toml.
# There is no frontend/requirements.txt in this repo.
python -m pip install -e ".[frontend]"
```

## Run

```bash
python frontend\main.py
```

Make sure the API server and worker are running first (see the root README).
The app reads `API_BASE_URL` from `.env` and defaults to `http://localhost:8000`.

