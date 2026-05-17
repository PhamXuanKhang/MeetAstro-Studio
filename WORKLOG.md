# Worklog

Ghi lại các quyết định kỹ thuật, phân công, và brainstorming của nhóm.

> Cập nhật **bất cứ khi nào** nhóm ra quyết định kỹ thuật quan trọng hoặc thay đổi hướng đi.

---

## Template

### Quyết định kỹ thuật

```markdown
### [ADR-N] Tiêu đề quyết định — DD/MM/YYYY

**Bối cảnh:** Vấn đề cần giải quyết là gì?

**Các lựa chọn đã xem xét:**
- Option A: ...
- Option B: ...

**Quyết định:** Chọn option nào và tại sao.

**Hệ quả:** Những gì bị ảnh hưởng / trade-off.
```

### Phân công

```markdown
### Sprint N — DD/MM → DD/MM/YYYY

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| | | | |
```

### Brainstorming

```markdown
### Brainstorm: [Chủ đề] — DD/MM/YYYY

**Câu hỏi:** ...

**Các ý tưởng:**
- Ý tưởng 1: ...
- Ý tưởng 2: ...

**Kết luận:** ...
```

---


### [ADR-1] Xóa legacy code và build mới theo Meeting Assistant spec — 11/04/2026

**Bối cảnh:** Codebase hiện tại chỉ là generic OpenAI agent starter template (`agent.py` + `tools.py`). CLAUDE.md spec yêu cầu AI Meeting Assistant với kiến trúc hoàn toàn khác: Streamlit UI, Whisper transcription, GPT-4o analysis, Jira integration.

**Các lựa chọn đã xem xét:**
- **Option A: Refactor từ code hiện tại** — giữ `agent.py`, thêm features lên trên. Ưu: ít thay đổi. Nhược: code cũ không liên quan, kiến trúc sai hướng.
- **Option B: Xóa sạch, build mới** — xóa `agent.py` + `tools.py`, build lại toàn bộ theo spec. Ưu: sạch sẽ, đúng kiến trúc. Nhược: mất nhiều effort hơn.

**Quyết định:** Chọn Option B. Code cũ là generic agent loop, không có gì liên quan Meeting Assistant. Giữ lại chỉ gây confusing.

**Hệ quả:** Cần build ~20 files mới. Ước tính 12-15h. Không có entry point tạm thời cho tới khi `app.py` hoàn thành.

---

### [ADR-2] SQLite thay vì PostgreSQL cho MVP — 11/04/2026

**Bối cảnh:** CLAUDE.md spec ghi PostgreSQL. Nhưng đây là MVP, chạy local, không cần multi-user hay complex queries.

**Các lựa chọn đã xem xét:**
- **PostgreSQL**: Đúng spec, production-ready. Nhưng cần setup server, connection string, driver riêng.
- **SQLite**: Built-in Python (`sqlite3`), zero config, file-based. Đủ cho MVP, dễ swap sau nhờ abstraction layer.

**Quyết định:** SQLite cho MVP. Design database module với interface đủ abstract để swap sang PostgreSQL sau không cần sửa logic.

**Hệ quả:** Không cần install PostgreSQL, driver, hay setup connection. Trade-off: không có concurrent write support (OK cho single-user MVP).

---

### [ADR-5] Jira stub client thay vì bỏ Jira hoàn toàn — 11/04/2026

**Bối cảnh:** Không có Jira sandbox để test. Spec yêu cầu Jira integration (Epic → Task → Subtask).

**Các lựa chọn đã xem xét:**
- **Tạm bỏ Jira**: Đơn giản nhất nhưng vi phạm spec hoàn toàn.
- **Stub client**: Code đầy đủ Jira REST API calls, nhưng khi thiếu credentials thì return fake keys + log warning. Test bằng mock HTTP.

**Quyết định:** Stub client. Code production-ready, chỉ cần fill `.env` là hoạt động thật. Tests dùng `unittest.mock` để verify request payload/headers đúng Jira schema.

**Hệ quả:** 12 tests cho Jira client đều pass. Khi có Jira sandbox chỉ cần set `JIRA_BASE_URL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY` trong `.env`.

---

### [ADR-3] pyproject.toml + editable install cho package resolution — 12/04/2026

**Bối cảnh:** `streamlit run src/app.py` gây `ModuleNotFoundError: No module named 'src'` vì Streamlit chạy file như script độc lập, không có project root trong `sys.path`.

**Các lựa chọn đã xem xét:**
- **Hack sys.path trong app.py**: Nhanh nhưng fragile, không chuẩn.
- **Root app.py wrapper**: Redirect entry point, nhưng Streamlit không hỗ trợ `runpy` tốt.
- **pyproject.toml + `uv pip install -e .`**: Chuẩn Python packaging — khai báo `src` là package, cài editable mode.

**Quyết định:** `pyproject.toml` + editable install. Giải quyết import ở mọi nơi (tests, streamlit, scripts) mà không cần hack.

**Hệ quả:** Cần chạy `uv pip install -e .` một lần sau khi clone. Thêm 1 file `pyproject.toml` vào repo.

---

### Sprint 1 — 02/04 → 12/04/2026

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| Survey codebase vs CLAUDE.md spec | Khang (+ Claude Code Opus) | 11/04 | ✅ Xong |
| Tạo refactor plan chi tiết (Bước 1-4) | Khang (+ Claude Code Opus) | 11/04 | ✅ Xong |
| Xóa legacy code (`agent.py`, `tools.py`) | Khang (+ Claude Code Sonnet) | 12/04 | ✅ Xong |
| Build schema.py + providers (ABC + 3 concrete) | Khang (+ Claude Code Sonnet) | 12/04 | ✅ Xong |
| Build services (transcription + analysis) | Khang (+ Claude Code Sonnet) | 12/04 | ✅ Xong |
| Build modules (database + exporter + jira stub) | Khang (+ Claude Code Sonnet) | 12/04 | ✅ Xong |
| Build Streamlit UI (app.py) | Khang (+ Claude Code Sonnet) | 12/04 | ✅ Xong |
| Viết 85 unit tests (9 files) | Khang (+ Claude Code Sonnet) | 12/04 | ✅ Xong |
| Setup pyproject.toml + fix imports | Khang (+ Claude Code) | 12/04 | ✅ Xong |
| Fix pre-push hook (python3 → python) | Khang (+ Claude Code Opus) | 12/04 | ✅ Xong |
| Submit conversation logs lên server | Khang (+ Claude Code Opus) | 12/04 | ✅ Xong |
| Cập nhật JOURNAL.md + WORKLOG.md | Khang (+ Claude Code Opus) | 12/04 | ✅ Xong |

---

### Bug quan trọng: pre-push hook không submit log — 12/04/2026

**Triệu chứng:** Push code thành công, `session.jsonl` bị reset (nội dung cũ mất), nhưng không có output `[ai-log] Submitted ...`. Server cũng không nhận log.

**Root cause:** `.git/hooks/pre-push` dùng `python3 scripts/submit_log.py`. Trên Windows, `python3` là alias Microsoft Store — không chạy Python mà mở Store app. Hook fail im lặng, `exit 0` ở dòng sau đảm bảo push không bị chặn, nên không có error message.

**Tại sao session.jsonl bị reset:** Chưa xác định chính xác — có thể do git clean hoặc hook behavior. Nội dung cũ (log từ các session trước) bị mất.

**Fix:**
1. Sửa `.git/hooks/pre-push`: `python3` → `python`
2. Sửa `scripts/setup_hooks.sh`: tương tự, để lần setup sau không tạo lại bug
3. Trích xuất conversation history từ Claude Code local storage (`~/.claude/projects/*/*.jsonl`), chuyển sang format session.jsonl, append vào file
4. Chạy `python scripts/submit_log.py` thủ công → submit 49 entries thành công (server trả 202)

**Học được:** Trên Windows luôn dùng `python` (không `python3`). Luôn test hook bằng cách chạy script trực tiếp trước.

---

### [ADR-6] Pydantic thay dataclasses cho schema — 18/04/2026

**Bối cảnh:** Schema dùng `dataclasses` không có validation built-in. Khi parse JSON từ GPT-4o, cần validate fields (deadline format, priority enum) thủ công.

**Các lựa chọn đã xem xét:**
- **Giữ dataclasses + custom validation**: Thêm validation functions. Nhược: code boilerplate, dễ bỏ sót.
- **Pydantic models**: Built-in validation, serialization, type coercion. Ưu: standard, well-tested.

**Quyết định:** Migrate sang Pydantic. Giữ `to_dict/from_dict/to_json/from_json` API để không break callers.

**Hệ quả:** Cần update tests. `model_dump(mode="json")` tự động handle enum + datetime serialization.

---

### [ADR-7] Validation service với cross-validation scoring — 18/04/2026

**Bối cảnh:** AI có thể hallucinate action items. Cần mechanism để phát hiện và đánh giá confidence.

**Các lựa chọn đã xem xét:**
- **Human review only**: User tự kiểm tra. Nhược: tốn thời gian, dễ bỏ sót.
- **Rule-based cross-validation**: Regex extraction → so sánh với AI output → confidence score.

**Quyết định:** Implement dual extraction (AI + rule-based) + cross-validation scoring.

**Scoring formula:**
- `cross_validation_score` (35%): AI items match với rule items
- `context_coherence_score` (35%): Action item words xuất hiện trong transcript
- `structural_validation_score` (30%): Title length, description, action verbs

**Hệ quả:** Mỗi action item có `confidence` score (0.0–1.0) và `validation_notes`. UI có thể highlight low-confidence items.

---

### [ADR-8] Credential vault cho provider configs — 18/04/2026

**Bối cảnh:** Chuẩn bị multi-provider support (Gemini, Claude, etc.). API keys cần lưu trong database nhưng không plaintext.

**Các lựa chọn đã xem xét:**
- **Plaintext in .env**: Đơn giản nhưng không scale cho nhiều providers, không per-user.
- **Encrypted in SQLite**: Fernet encryption, key từ `APP_SECRET_KEY`. Per-user, per-provider configs.

**Quyết định:** `credential_vault.py` với Fernet encryption. `database.py` có `provider_configs` table lưu encrypted config JSON.

**Hệ quả:** Cần set `APP_SECRET_KEY` trong `.env`. Nếu key mất, không decrypt được configs cũ.

---

### [ADR-9] Audio recording với chunk rotation — 18/04/2026

**Bối cảnh:** Transcription real-time cần audio chunks thay vì đợi cả file. System audio capture cần mix với mic.

**Các lựa chọn đã xem xét:**
- **Wait for full recording**: Đơn giản nhưng không real-time.
- **Chunk rotation**: Mỗi N giây đóng chunk cũ, mở chunk mới. Chunk hoàn thành có thể transcribe ngay.

**Quyết định:** `AudioRecorder` với chunk rotation. `on_chunk_complete` callback cho downstream processing.

**Config:**
- `TRANSCRIPTION_CHUNK_SECONDS` (default: 60)
- `AUDIO_MIC_ENABLED`, `AUDIO_MIC_GAIN`, `AUDIO_SYS_GAIN`

**Hệ quả:** Recording folder có nhiều chunk files (`*_chunk000.wav`, `*_chunk001.wav`, ...). `get_completed_chunks()` trả về list paths.

---

### Sprint 2 — 13/04 → 26/04/2026

| Task | Người làm | Deadline | Trạng thái |
|---|---|---|---|
| Audio recording module (pysysaudio + mic) | Vthuc | 18/04 | ✅ Xong |
| Recording service orchestration | Vthuc | 18/04 | ✅ Xong |
| Chunk rotation + callback | Vthuc | 18/04 | ✅ Xong |
| Pydantic migration (schema.py) | Khang | 18/04 | ✅ Xong |
| pydantic-settings migration (config.py) | Khang | 18/04 | ✅ Xong |
| Rule-based extraction service | Khang | 18/04 | ✅ Xong |
| Validation service (cross-validation) | Khang | 18/04 | ✅ Xong |
| Async summarization service | Khang | 18/04 | ✅ Xong |
| Credential vault (Fernet) | Khang | 18/04 | ✅ Xong |
| Provider configs CRUD | Khang | 18/04 | ✅ Xong |
| MockAnalyzer cho testing | Khang | 18/04 | ✅ Xong |
| Jira upload flow documentation | Duypt | 18/04 | ✅ Xong |
| Update docs (architecture, api-reference, etc.) | Khang | 19/04 | ✅ Xong |
| Smoke test E2E | Khang | 26/04 | ⬜ |
| Test Jira với sandbox | Khang | 26/04 | ⬜ |
| Deploy cloud | [TBD] | 26/04 | ⬜ |