# AI Meeting Assistant

## Overview
Ứng dụng chuyển đổi audio cuộc họp thành action items có cấu trúc (Epic → Task → Subtask) và tích hợp tự động vào Jira. Workflow: Ghi âm → Whisper transcribe → LLM phân tích → Xuất Jira tickets.

Tech stack: Python 3.9+ / Streamlit 1.32+ / OpenAI API (GPT-4o + Whisper) / PostgreSQL / Jira REST API.

## Commands
```
pip install -r requirements.txt    # Install
streamlit run src/app.py               # Run app
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
- `JIRA_BASE_URL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY` — Jira integration
- `DATABASE_URL` — PostgreSQL connection string

## Agent Behavior

**Think Before Coding** — Nêu rõ assumptions trước khi implement. Nếu có nhiều cách diễn giải, trình bày tất cả thay vì tự chọn im lặng. Nếu có hướng đơn giản hơn, nói ra. Nếu không rõ yêu cầu, dừng lại và hỏi.

**Simplicity First** — Viết lượng code tối thiểu giải quyết đúng vấn đề. Không thêm feature, abstraction, hay "flexibility" ngoài yêu cầu. Nếu 200 dòng có thể viết lại thành 50, hãy làm vậy.

**Surgical Changes** — Chỉ chạm vào những gì cần thiết. Không "cải thiện" code lân cận, không refactor code không bị hỏng. Giữ đúng style hiện có. Xóa import/biến/hàm mà chính thay đổi của mình tạo ra — không xóa dead code có sẵn trừ khi được yêu cầu.

**Goal-Driven Execution** — Biến task thành tiêu chí kiểm chứng được. Với task nhiều bước, nêu kế hoạch ngắn trước khi làm:
```
1. [Bước] → verify: [kiểm tra]
2. [Bước] → verify: [kiểm tra]
```

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