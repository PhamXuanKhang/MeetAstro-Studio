# AI Meeting Assistant

## Overview
Ứng dụng chuyển đổi audio cuộc họp thành biên bản hoàn chỉnh và action items có cấu trúc (Epic → Task → Subtask) để tích hợp tự động vào Jira. Workflow mới: File âm thanh MP3 → xử lý song song STT + diarization → alignment timestamp/người nói → LLM bước 1 (cleaning & formatting) → LLM bước 2 (extraction & summary) → xuất Jira tickets.

Tech stack: Python 3.9+ / Streamlit 1.32+ / OpenAI API (GPT-4o + Whisper) / PostgreSQL / Jira REST API.

## Commands
```
pip install -r requirements.txt    # Install dependencies
pip install -e .                   # Run this to avoid ModuleNotFoundError for 'src'
streamlit run src/app.py           # Run app
pytest tests/ -v                   # Test all
pytest tests/test_X.py -v          # Test single
flake8 . --max-line-length=100     # Lint
mypy . --ignore-missing-imports    # Typecheck
```

## Architecture
```
src/
  app.py                  → Streamlit UI (entry point)
  schema.py               → Dataclasses: ActionItem, MeetingAnalysis, MeetingRecord
  config.py               → Config tập trung + logging setup
  providers/
    base_analyzer.py      → ABC cho AI analyzers
    base_transcriber.py   → ABC cho transcription providers
    openai_analyzer.py    → GPT-4o structured output (JSON mode)
    openai_transcriber.py → Whisper API transcription
    local_transcriber.py  → Local Whisper fallback
  services/
    analysis_service.py   → Chọn + gọi AI analyzer (orchestration)
    transcription_service.py → Fallback chain: Whisper API → Local Whisper
  modules/
    database.py           → PostgreSQL CRUD cho meeting records
    exporter.py           → Export Markdown / JSON / CSV
  prompts/                → Prompt templates (tiếng Việt)
tests/                  → pytest files
```

## Key Patterns
- **Strategy Pattern**: Mỗi AI provider kế thừa ABC (`base_analyzer.py`, `base_transcriber.py`). Provider mới PHẢI implement ABC tương ứng.
- **Parallel Pipeline**: STT và diarization chạy song song từ cùng một input audio để tối ưu thời gian xử lý.
- **Timestamp Alignment**: Kết quả STT và speaker labels được hợp nhất bằng bước alignment để tạo diarized transcript có người nói gắn đúng với từng đoạn.
- **Two-stage LLM Post-processing**: LLM bước 1 dùng để cleaning & formatting, LLM bước 2 dùng để extraction & summary.
- **Fallback Chain**: `transcription_service.py` tự fallback Whisper API → Local khi lỗi.
- **Structured Output**: OpenAI dùng JSON mode cho action items extraction. Output cuối phải map được sang Jira schema: Epic → Task → Subtask với assignee, deadline, priority.
- **State**: Streamlit `session_state` cho UI state; PostgreSQL cho persistent data.

## Action Items Schema (Jira integration target)
Mỗi cuộc họp extract ra cấu trúc:
- **Epic**: Chủ đề lớn / quyết định chính của cuộc họp
- **Task**: Action item cụ thể (có assignee, deadline, priority)
- **Subtask**: Bước nhỏ trong task (nếu có)
- Mỗi item cần: `summary`, `assignee`, `deadline`, `priority` (Critical/High/Medium/Low), `context` (trích dẫn từ transcript)

## Code Style
- snake_case functions/variables, PascalCase classes, UPPER_CASE constants.
- Type hints đầy đủ (Python 3.9+ style: `list[str]`, không `List[str]`).
- Docstrings tiếng Việt, tên biến + kỹ thuật tiếng Anh.
- Logging (không print). Dùng `config.py` logger.
- Pure functions khi có thể. Không global state ngoài config.

## Environment Variables
Xem `.env.example`. Keys quan trọng:
- `OPENAI_API_KEY` — GPT-4o + Whisper API
- `WHISPER_LOCAL_MODEL` — tiny/base/small/medium/large
- `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY` — Jira integration (Basic Auth)
- `DATABASE_URL` — PostgreSQL connection string

## Rules
- LUÔN chạy `pytest tests/ -v` sau khi sửa logic trong `providers/` hoặc `services/`.
- LUÔN verify structured output match Jira schema (Epic/Task/Subtask) sau khi sửa prompts hoặc analyzer.
- KHÔNG commit `.env`, API keys, hoặc credentials.
- KHÔNG sửa files trong `.claude/` mà không hỏi trước.
- Provider mới PHẢI kế thừa ABC + có test file riêng.
- External API calls PHẢI có error handling + retry logic.
- Prompt changes PHẢI test với ≥2 sample transcripts trước khi commit.

## Verification
Sau mỗi thay đổi: `flake8 . --max-line-length=100 && mypy . --ignore-missing-imports && pytest tests/ -v`

## Recurring Mistakes
<!-- Thêm lỗi mới vào đây mỗi khi Claude mắc lỗi lặp. Format: -->
<!-- - [Ngày] Lỗi: ... → Fix: ... -->