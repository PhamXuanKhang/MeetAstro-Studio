# Frontend (Flet)

Cross-platform desktop UI for the AI Meeting Assistant. The app is **HTTP-only** and talks to the FastAPI backend.

## Install

From the repo root:

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
pip install -r frontend\requirements.txt
```

## Run

```bash
python frontend\main.py
```

Make sure the API server and worker are running (see root README).

