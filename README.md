# AI Meeting Assistant

Ứng dụng chuyển đổi audio cuộc họp thành biên bản hoàn chỉnh và action items có cấu trúc (Epic → Task → Subtask) để tích hợp tự động vào Jira.

## Structure

```
├── src/
│   ├── app.py          # Streamlit UI
│   ├── config.py       # Configuration
│   ├── schema.py       # Data Models
│   ├── modules/        # Database, Exporter, Jira client
│   ├── providers/      # Strategy pattern cho AI (Whisper, GPT)
│   └── services/       # Orchestration (Analyze, Transcribe, Jira)
├── tests/              # Unit tests
├── docs/               # System documentation
├── scripts/
│   ├── setup_hooks.sh  # One-time hook installer
│   ├── log_hook.py     # AI tool hook handler
│   └── submit_log.py   # Submits logs on git push
├── requirements.txt
├── prompt_notes/       # Ghi chú prompt từ Instructor
├── .env.example
├── AGENTS.md           # Rules for using AI coding agents
├── JOURNAL.md          # Weekly journal — product journey & learnings
└── WORKLOG.md          # Technical decisions, task assignments, brainstorming
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
