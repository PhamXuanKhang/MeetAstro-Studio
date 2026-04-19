# AI Meeting Assistant

Ứng dụng chuyển đổi audio cuộc họp thành biên bản hoàn chỉnh và action items có cấu trúc (Epic → Task → Subtask) để tích hợp tự động vào Jira.

## Structure

```
├── src/
│   ├── app.py              # Streamlit UI (entry point)
│   ├── config.py           # Configuration + logging (pydantic-settings)
│   ├── schema.py           # Pydantic models (Epic, Task, Subtask, MeetingAnalysis)
│   ├── modules/
│   │   ├── database.py         # SQLite CRUD (meetings + provider_configs)
│   │   ├── exporter.py         # Export Markdown / JSON / CSV
│   │   ├── jira_client.py      # Jira REST API v3 client
│   │   ├── audio_recorder.py   # System audio capture + mic mixing
│   │   └── credential_vault.py # Fernet encryption cho provider credentials
│   ├── providers/
│   │   ├── base_analyzer.py    # ABC cho AI analyzers
│   │   ├── base_transcriber.py # ABC cho transcription providers
│   │   ├── openai_analyzer.py  # GPT-4o structured output
│   │   ├── openai_transcriber.py # Whisper API
│   │   ├── local_transcriber.py  # Local Whisper fallback
│   │   └── mock_analyzer.py    # Mock analyzer cho testing/fallback
│   ├── services/
│   │   ├── analysis_service.py     # AI analysis orchestration
│   │   ├── transcription_service.py # Fallback chain transcription
│   │   ├── jira_service.py         # Jira push orchestration
│   │   ├── recording_service.py    # Audio recording orchestration
│   │   ├── extraction_service.py   # Rule-based action item extraction
│   │   ├── validation_service.py   # Cross-validation AI vs rule-based
│   │   └── summarization_service.py # Async summary generation
│   └── prompts/            # Prompt templates (tiếng Việt)
├── tests/                  # pytest (14 test files)
├── docs/                   # System documentation
├── scripts/
│   ├── setup_hooks.sh      # One-time hook installer
│   ├── log_hook.py         # AI tool hook handler
│   └── submit_log.py       # Submits logs on git push
├── requirements.txt
├── .env.example
├── AGENTS.md               # Rules for using AI coding agents
├── JOURNAL.md              # Weekly journal — product journey & learnings
└── WORKLOG.md              # Technical decisions, task assignments, brainstorming
```

## Getting Started

### 1. Clone and setup

```bash
git clone <repo-url>
cd <repo>

# Install git pre-push hook (required, run once)
bash scripts/setup_hooks.sh
```

### 2. Configure environment

```bash
cp .env.example .env
```

Mở `.env` và điền các khóa `OPENAI_API_KEY`, cấu hình Jira (`JIRA_BASE_URL`...), và DB config.

### 3. Run

```bash
python -m venv venv
source venv/bin/activate       # Linux/Mac
# or: venv\Scripts\activate    # Windows

pip install -r requirements.txt
pip install -e .               # Cài đặt module 'src' để chạy Streamlit
streamlit run src/app.py
```

## Weekly Journal

Update **[JOURNAL.md](./JOURNAL.md)** at the end of every week to document your product-building journey:

- Features shipped
- AI tools used and how they helped
- Hardest problem of the week and how you solved it
- What you'd do differently
- Plan for next week

> JOURNAL.md **must be updated** before each PR. It is your learning record for the course.

## Worklog

Update **[WORKLOG.md](./WORKLOG.md)** whenever your team makes a technical decision or changes direction:

- **Technical decisions** — why did you choose this approach over alternatives?
- **Task assignments** — who does what, by when
- **Brainstorming** — options considered, pros/cons, conclusion
- **Important bugs** — root cause and fix

See each file for the format and examples.

## AI Logging

Prompts and tool calls are **automatically logged** when you use any supported AI tool (Claude Code, Cursor, Codex, Gemini, Copilot). No manual steps needed after running `setup_hooks.sh`.

See [AGENTS.md](./AGENTS.md) for details.
