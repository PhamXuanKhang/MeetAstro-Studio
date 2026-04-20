# AI Meeting Assistant

## Overview
Ứng dụng chuyển đổi audio cuộc họp thành biên bản hoàn chỉnh và action items có cấu trúc (Epic → Task → Subtask) để tích hợp tự động vào Jira.

**Current Tech stack**: Python 3.9+ / Streamlit 1.32+ / OpenAI API (GPT-4o + Whisper) / SQLite / Jira REST API v3 / `uv` / Pydantic.
**Target Tech stack (Roadmap)**: Đang lên kế hoạch nâng cấp lưu trữ lên PostgreSQL.

**Current Workflow (Thực tế đang chạy)**:
1. **Input**: Upload file hoặc Record system/mic audio (`recording_service`).
2. **STT**: Whisper API (có fallback về Local Whisper qua `transcription_service`).
3. **Validate**: Cross-validate AI extraction vs Rule-based regex.
4. **LLM Analysis**: GPT-4o (1 bước) thông qua JSON mode để extract Epic/Task/Subtask.
5. **Output**: Export MD/JSON/CSV hoặc Push lên Jira (auto stub mode nếu thiếu credentials).

**Target/Future Workflow (Hướng phát triển tiếp theo)**:
File âm thanh MP3 → **xử lý song song STT + Diarization** (nhận diện người nói) → **Alignment timestamp/người nói** → **LLM bước 1 (cleaning & formatting)** → **LLM bước 2 (extraction & summary)** → Xuất Jira tickets.

## Commands
```bash
# Sử dụng uv để quản lý package
uv venv
source .venv/Scripts/activate      # Windows
uv pip install -e .                # Cài đặt dạng editable để tránh lỗi ModuleNotFoundError

streamlit run src/app.py           # Run app
pytest tests/ -v                   # Test all
flake8 . --max-line-length=100     # Lint
mypy . --ignore-missing-imports    # Typecheck
```

## Architecture
```text
src/
  app.py                    → Streamlit UI (entry point)
  schema.py                 → Dataclasses: ActionItem, MeetingAnalysis, MeetingRecord
  config.py                 → Config tập trung + logging setup
  providers/
    base_analyzer.py        → ABC cho AI analyzers
    base_transcriber.py     → ABC cho transcription providers
    openai_analyzer.py      → GPT-4o structured output (JSON mode, retry 3x)
    openai_transcriber.py   → Whisper API transcription
    local_transcriber.py    → Local Whisper fallback
  services/
    transcription_service.py → Fallback chain: Whisper API → Local Whisper
    analysis_service.py     → Chọn + gọi AI analyzer (orchestration)
    jira_service.py         → Push Jira (Epic → Task → Subtask)
    recording_service.py    → Capture audio (System + Mic)
    extraction_service.py   → Rule-based regex extraction
    validation_service.py   → Cross-validate AI vs Rule-based
    summarization_service.py → Async OpenAI summary
  modules/
    database.py             → SQLite CRUD (Target Roadmap: Chuyển đổi sang PostgreSQL)
    exporter.py             → Export Markdown / JSON / CSV
    jira_client.py          → REST API v3 (Auto stub mode)
    credential_vault.py     → Fernet encryption cho keys bảo mật của provider
  prompts/                  → Prompt templates (tiếng Việt)
tests/                      → pytest files
docs/                       → Tài liệu chi tiết về product/technical/evaluation
```

## Key Patterns
- **Strategy Pattern**: Mỗi AI provider kế thừa ABC (`base_analyzer.py`, `base_transcriber.py`). Provider mới PHẢI implement ABC tương ứng.
- **Fallback Chain**: `transcription_service.py` tự fallback Whisper API → Local khi lỗi.
- **Structured Output**: OpenAI dùng JSON mode cho action items extraction. Output cuối phải map được sang Jira schema: Epic → Task → Subtask với assignee, deadline, priority.
- **Validation**: AI extraction được cross-validate với rule-based rules (`validation_service`) để tính toán confidence score.
- **State**: Streamlit `session_state` cho UI state; SQLite database cho persistent data lưu local (sẽ nâng lên PostgreSQL trong tương lai).
- **Security**: Module `credential_vault.py` tự động mã hoá provider configs lưu trong database bằng hệ mã hoá đối xứng Fernet.

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
- Logging (không print). Dùng `from src.config import get_logger`.
- Pure functions khi có thể. Không global state ngoài config (ngoại trừ session state Streamlit).

## Environment Variables
Xem `.env.example`. Keys quan trọng:
- `OPENAI_API_KEY` — GPT-4o + Whisper API
- `WHISPER_LOCAL_MODEL` — model size cho local (tiny/base/small/medium/large)
- `DATABASE_URL` — Dùng SQLite hiện tại (vd: `sqlite:///data/meetings.db`). Sẽ map sang PostgreSQL sau.
- `APP_SECRET_KEY` — Dùng cho credential vault để mã hoá
- `AUDIO_*` — Các config setup record audio channel (sample rate, sys_gain, mic_gain).
- `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY` — Jira integration (Basic Auth)

## Agent Behavior

**Think Before Coding** — Khuyến khích đọc kĩ tài liệu trong thư mục `docs/`. Nêu rõ assumptions trước khi implement. Nếu có nhiều cách diễn giải, trình bày tất cả thay vì tự chọn im lặng. Nếu có hướng đơn giản hơn, nói ra.

**Simplicity First** — Viết lượng code tối thiểu giải quyết đúng vấn đề. Chú ý đồng bộ với Architecture Setup hiện tại (nhắc nhở check `docs/`).

**Surgical Changes** — Chỉ chạm vào những gì cần thiết. Không "cải thiện" code lân cận, không refactor code không bị hỏng. Xóa import/biến/hàm mà chính thay đổi của mình tạo ra — không xóa dead code có sẵn.

**Goal-Driven Execution** — Biến task thành tiêu chí kiểm chứng được. Với task nhiều bước, nêu kế hoạch ngắn:
```text
1. [Bước] → verify: [kiểm tra]
2. [Bước] → verify: [kiểm tra]
```

## Rules
- LUÔN chạy `pytest tests/ -v` sau khi sửa logic trong `providers/` hoặc `services/`.
- LUÔN verify structured output match Jira schema (Epic/Task/Subtask) sau khi sửa prompts hoặc analyzer.
- KHÔNG commit `.env`, API keys, hoặc credentials.
- KHÔNG sửa files trong `.claude/` mà không hỏi trước.
- Provider mới PHẢI kế thừa ABC + có test file riêng (`mock_analyzer`, `local_transcriber`, vv).
- External API calls PHẢI có error handling + retry logic.
- Prompt changes PHẢI test với ≥2 sample transcripts trước khi commit.

## Verification
Sau mỗi thay đổi: `flake8 . --max-line-length=100 && mypy . --ignore-missing-imports && pytest tests/ -v`

## Recurring Mistakes
<!-- Thêm lỗi mới vào đây mỗi khi AI mắc lỗi lặp. Format: -->
<!-- - [Ngày] Lỗi: ... → Fix: ... -->