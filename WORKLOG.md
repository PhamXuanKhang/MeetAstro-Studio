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
3. Trích xuất conversation history từ Claude Code local storage (`~/.claude/projects/*/\*.jsonl`), chuyển sang format session.jsonl, append vào file
4. Chạy `python scripts/submit_log.py` thủ công → submit 49 entries thành công (server trả 202)

**Học được:** Trên Windows luôn dùng `python` (không `python3`). Luôn test hook bằng cách chạy script trực tiếp trước.