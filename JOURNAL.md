# Weekly Journal

Ghi lại hành trình xây dựng sản phẩm mỗi tuần — những gì đã làm, học được gì, AI giúp như thế nào.

> **Cập nhật mỗi cuối tuần** (trước khi tạo PR). Không cần dài, chỉ cần thật.

---

## Template

```markdown
## Tuần N — DD/MM/YYYY

### Đã làm
-

### Khó nhất tuần này
-

### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code | | |

### Học được
-

### Nếu làm lại, sẽ làm khác
-

### Kế hoạch tuần tới
-
```


---

### Tuần 1 — 12/04/2026

**Thành viên:** Phạm Xuân Khang

#### Đã làm
- Xóa legacy code (`agent.py`, `tools.py`) — starter template không liên quan tới Meeting Assistant
- Build toàn bộ kiến trúc mới theo CLAUDE.md spec:
  - `src/schema.py`: dataclasses Priority, ActionItem, Subtask, Task, Epic, MeetingAnalysis, MeetingRecord
  - `src/providers/`: Strategy Pattern — ABC base + 3 providers (OpenAI Analyzer, OpenAI Transcriber, Local Transcriber)
  - `src/services/`: Fallback chain transcription (Whisper API → Local Whisper), analysis orchestration
  - `src/modules/`: SQLite CRUD (database.py), export Markdown/JSON/CSV (exporter.py), Jira stub client (jira_client.py)
  - `src/prompts/extract_action_items.md`: Vietnamese prompt cho GPT-4o structured output
  - `src/app.py`: Streamlit UI — upload audio → transcribe → analyze → export/save/push Jira
- Viết 85 unit tests (9 test files), tất cả pass
- Setup `pyproject.toml` + editable install để giải quyết `ModuleNotFoundError` khi chạy Streamlit
- Sửa pre-push hook (`python3` → `python`) để submit log hoạt động trên Windows
- Trích xuất conversation history từ Claude Code local storage → submit 49 log entries lên server

#### Khó nhất tuần này
- SQLite `:memory:` không dùng được cho tests vì mỗi `sqlite3.connect(":memory:")` tạo DB mới → init_db tạo bảng ở connection A nhưng test query ở connection B → bảng không tồn tại. Phải đổi sang `tmp_path` fixture (file-based SQLite).
- `python3` trên Windows là alias Microsoft Store (mở Store thay vì chạy Python) → pre-push hook chạy `python3 scripts/submit_log.py` fail im lặng, log không bao giờ được submit. Mất thời gian để phát hiện vì `exit 0` che lỗi.
- `streamlit run src/app.py` không tìm được module `src` vì Python path không có project root → giải quyết bằng `pyproject.toml` + `uv pip install -e .`

#### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code (Opus) | Survey codebase vs spec, tạo refactor plan chi tiết (Bước 1-4) | Plan chính xác, phát hiện 100% gap giữa code hiện tại và spec |
| Claude Code (Sonnet) | Implement toàn bộ plan: tạo 20+ files, viết 85 tests | Build thành công trong 1 session, 85/85 tests pass |
| Claude Code (Opus) | Debug submit_log, trích xuất conversation history, viết JOURNAL/WORKLOG | Phát hiện root cause python3 Windows issue, submit 49 entries thành công |

#### Học được
- Strategy Pattern (ABC) giúp swap provider dễ dàng — chỉ cần implement `analyze()` hoặc `transcribe()` theo interface
- Fallback chain cần log warning khi switch provider — không im lặng, phải trace được
- SQLite `sqlite3.connect()` tạo connection mới mỗi lần gọi — cần cùng file path chứ không dùng `:memory:` cho tests nhiều hàm
- `pyproject.toml` + editable install (`uv pip install -e .`) là cách chuẩn để Python biết về package structure
- Git hook trên Windows phải dùng `python` (không phải `python3`) — luôn kiểm tra `which python3` trước khi dùng

#### Nếu làm lại, sẽ làm khác
- Chạy `setup_hooks.sh` và test submit log ngay từ ngày đầu, không để đến đầu tuần 2 mới phát hiện lỗi
- Setup `pyproject.toml` trước khi bắt đầu code, thay vì sau khi gặp import error
- Dùng `tmp_path` fixture cho SQLite tests ngay từ đầu thay vì thử `:memory:` rồi debug

#### Kế hoạch tuần tới
- Smoke test Streamlit app end-to-end với audio thật
- Tìm hiểu model detect giọng từng người để extract action items tốt hơn
- Nghiên cứu việc chunking để transcribe realtime
- Test Jira integration với Atlassian sandbox (nếu có)

---

### Tuần 2 — 19/04/2026

**Thành viên:** Phạm Xuân Khang, Vthuc, Duypt

#### Đã làm
- **Audio Recording (Vthuc):**
  - `audio_recorder.py`: System audio capture via pysysaudio + optional mic mixing via sounddevice
  - Chunk rotation mỗi N giây (configurable via `TRANSCRIPTION_CHUNK_SECONDS`)
  - Background thread recording với thread-safe chunk queue
  - `recording_service.py`: Orchestration singleton cho Streamlit
- **Validation & Extraction (Khang):**
  - `extraction_service.py`: Rule-based regex extraction để cross-validate với AI
  - `validation_service.py`: Cross-validation scoring (cross_validation, context_coherence, structural)
  - Confidence scores + validation_notes cho mỗi action item
- **Summarization (Khang):**
  - `summarization_service.py`: Async OpenAI call cho summary + key_decisions + parking_lot
  - Streaming mode (`generate_summary_stream()`) cho real-time UI
- **Schema & Config (Khang):**
  - Migrate từ dataclasses → Pydantic models (validation, serialization tốt hơn)
  - Thêm fields: `key_decisions`, `discussion_points`, `parking_lot`, `confidence`, `validation_notes`
  - `config.py`: Migrate sang pydantic-settings với validation
  - Thêm `MockAnalyzer` cho testing/fallback
- **Security (Khang):**
  - `credential_vault.py`: Fernet symmetric encryption cho provider credentials
  - `database.py`: Provider configs CRUD với encryption
- **Docs (Duypt):**
  - `jira-upload-flow.md`: Document chi tiết luồng upload Epic → Task → Subtask

#### Khó nhất tuần này
- Audio recording trên Windows: pysysaudio cần setup đặc biệt, mic device selection heuristic phức tạp
- Pydantic migration: cần giữ backward-compat với `to_dict/from_dict` API cũ
- Async summarization trong Streamlit: cần careful handling để không block UI

#### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code (Opus) | Rà soát docs vs code, tạo plan cập nhật tài liệu | Phát hiện 6+ file docs cần cập nhật |
| Claude Code (Sonnet) | Implement validation service, extraction service | Cross-validation scoring hoạt động |

#### Học được
- Pydantic `model_dump(mode="json")` tự động convert enum → string, datetime → ISO — không cần custom encoder
- Fernet key derivation: nếu key không đúng format, dùng SHA256 hash + base64 encode
- `pysysaudio` + `sounddevice` có thể mix system audio + mic trong real-time

#### Nếu làm lại, sẽ làm khác
- Migrate sang Pydantic sớm hơn (Phase 1) thay vì dataclasses — Pydantic có validation built-in
- Design validation service trước khi có AI output format — giúp define confidence metrics rõ hơn

#### Kế hoạch tuần tới
- Smoke test E2E với audio thật
- Integrate validation scores vào UI
- Test Jira với Atlassian sandbox
- Deploy lên cloud
