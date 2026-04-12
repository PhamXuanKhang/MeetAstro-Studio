# Deployment & Setup

Hướng dẫn cài đặt, chạy app, và troubleshoot.

---

## Prerequisites

- Python 3.9+
- `uv` package manager (khuyến nghị) hoặc `pip`
- Git

---

## Cài đặt

### 1. Clone repo

```bash
git clone https://github.com/a20-ai-thuc-chien/A20-App-089.git
cd A20-App-089
```

### 2. Tạo virtual environment

```bash
python -m venv .venv

# Activate:
# Linux/macOS:
source .venv/bin/activate

# Windows (Git Bash):
source .venv/Scripts/activate

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
# Với uv (nhanh hơn):
uv pip install -r requirements.txt
uv pip install -e .

# Với pip:
pip install -r requirements.txt
pip install -e .
```

> **Quan trọng:** `pip install -e .` (editable install) cần thiết để `from src.xxx import ...` hoạt động trong Streamlit và tests.

### 4. Cấu hình environment

```bash
cp .env.example .env
# Sửa .env — điền OPENAI_API_KEY (bắt buộc)
```

### 5. Setup git hooks

```bash
bash scripts/setup_hooks.sh
```

---

## Chạy app

```bash
# Activate venv trước!
source .venv/Scripts/activate  # Windows
streamlit run src/app.py
```

App mở tại `http://localhost:8501`.

---

## Chạy tests

```bash
pytest tests/ -v
```

### Verification đầy đủ

```bash
flake8 . --max-line-length=100 && mypy . --ignore-missing-imports && pytest tests/ -v
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'src'`

**Nguyên nhân:** Chưa chạy `pip install -e .` (editable install).

**Fix:**
```bash
source .venv/Scripts/activate
uv pip install -e .  # hoặc pip install -e .
```

### Streamlit dùng system Python thay vì .venv

**Kiểm tra:**
```bash
which streamlit
which python
```

Nếu `streamlit` trỏ ra ngoài `.venv` → install streamlit vào `.venv`:
```bash
uv pip install streamlit
```

### `python3` không chạy trên Windows

**Nguyên nhân:** `python3` trên Windows là alias Microsoft Store.

**Fix:** Luôn dùng `python` (không phải `python3`). Đã fix trong `scripts/setup_hooks.sh` và `.git/hooks/pre-push`.

### pre-push hook không submit log

**Kiểm tra:**
```bash
cat .git/hooks/pre-push  # Phải là "python" không phải "python3"
python scripts/submit_log.py  # Chạy thủ công để test
```

---

## Environment Variables

Xem chi tiết: [api-reference.md — Configuration](api-reference.md#configuration--srcconfigpy)

| Variable | Bắt buộc | Mô tả |
|----------|----------|-------|
| `OPENAI_API_KEY` | Yes | API key cho GPT-4o + Whisper |
| `OPENAI_MODEL` | No (default: `gpt-4o`) | Model cho analysis |
| `WHISPER_LOCAL_MODEL` | No (default: `base`) | Whisper local model size |
| `DATABASE_URL` | No (default: `sqlite:///data/meetings.db`) | SQLite path |
| `JIRA_BASE_URL` | No | Jira instance URL |
| `JIRA_API_TOKEN` | No | Jira API token |
| `JIRA_PROJECT_KEY` | No | Jira project key |
| `LOG_LEVEL` | No (default: `INFO`) | Logging level |

---

## Project structure

```
A20-App-089/
├── src/
│   ├── app.py                  ← Entry point (Streamlit)
│   ├── schema.py               ← Data models
│   ├── config.py               ← Config + logging
│   ├── providers/              ← Strategy Pattern (AI providers)
│   ├── services/               ← Orchestration (fallback chain)
│   ├── modules/                ← DB, export, Jira
│   └── prompts/                ← Prompt templates
├── tests/                      ← pytest (85 tests)
├── docs/                       ← Tài liệu (bạn đang ở đây)
├── scripts/                    ← Hooks, log submission
├── pyproject.toml              ← Package config
├── requirements.txt            ← Dependencies
├── .env.example                ← Template environment
├── CLAUDE.md                   ← AI agent instructions
├── JOURNAL.md                  ← Weekly journal
└── WORKLOG.md                  ← Technical decisions log
```
