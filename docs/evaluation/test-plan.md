# Test Plan

Chiến lược testing cho AI Meeting Assistant.

---

## Tổng quan

| Loại test | Coverage | Status |
|-----------|----------|--------|
| **Unit tests** | 85 tests, 9 files | ✅ All passing |
| **Integration tests** | E2E với audio thật | ⬜ Chưa implement |
| **Manual smoke test** | Streamlit UI + real audio | ⬜ Chưa chạy |
| **Eval test** | AI quality (recall, precision, WER) | ⬜ Chưa implement |

---

## Unit Tests

### Test files hiện có

| File | Số tests | Mô tả |
|------|----------|--------|
| `tests/test_schema.py` | ~10 | Dataclass construction, `to_dict` / `from_dict` round-trip |
| `tests/test_openai_analyzer.py` | ~10 | Mock OpenAI client, verify JSON parsing, retry logic |
| `tests/test_openai_transcriber.py` | ~10 | Mock Whisper API |
| `tests/test_local_transcriber.py` | ~10 | Mock `whisper.load_model` |
| `tests/test_transcription_service.py` | ~10 | **Fallback chain**: OpenAI fail → Local OK, both fail → RuntimeError, verify warning log |
| `tests/test_analysis_service.py` | ~10 | Mock analyzer, empty transcript → ValueError |
| `tests/test_database.py` | ~10 | SQLite CRUD với `tmp_path` fixture (file-based, không `:memory:`) |
| `tests/test_exporter.py` | ~10 | Build `MeetingAnalysis` cứng, assert output MD/JSON/CSV chứa expected fields |
| `tests/test_jira_client.py` | ~12 | Mock `requests.post`, verify request payload + headers, stub mode behavior |

### Chạy tests

```bash
# Tất cả tests
pytest tests/ -v

# Một file cụ thể
pytest tests/test_transcription_service.py -v

# Với coverage (nếu cần)
pytest tests/ -v --cov=src --cov-report=term-missing
```

### Lưu ý quan trọng

- **Database tests:** Dùng `tmp_path` fixture (file-based SQLite), **KHÔNG** dùng `:memory:` vì mỗi `sqlite3.connect(":memory:")` tạo DB riêng biệt
- **Provider tests:** Tất cả mock external APIs — không gọi OpenAI/Whisper thật trong unit test
- **Fallback chain test:** Phải verify cả: (1) OpenAI thành công, (2) OpenAI fail → Local thành công + log warning, (3) Cả hai fail → RuntimeError

---

## Integration Test Plan [TBD]

### E2E Flow Test

```
Audio file (≤ 2 phút)
    → transcribe() → assert transcript not empty, len > 50
    → analyze(transcript) → assert analysis has ≥ 1 epic
    → export_markdown(analysis) → assert contains "Epic"
    → export_json(analysis) → assert valid JSON, has "epics" key
    → export_csv(analysis) → assert header row + ≥ 1 data row
    → create_meeting(record) → assert id > 0
    → get_meeting(id) → assert record.title matches
```

**Cần:** Audio file mẫu + OPENAI_API_KEY thật (hoặc mock server).

### Fallback Integration Test

1. Set `OPENAI_API_KEY` thành invalid → transcribe audio
2. Verify: fallback sang Local Whisper, log warning xuất hiện
3. Verify: transcript output vẫn có nội dung hợp lệ

### Jira Integration Test

1. Setup Atlassian sandbox (nếu có)
2. Set `JIRA_*` env vars
3. Chạy `create_epic() → create_task() → create_subtask()`
4. Verify: issues tạo đúng trên Jira dashboard

---

## Manual Smoke Test Checklist

Chạy `streamlit run src/app.py` và kiểm tra:

### Upload & Transcribe
- [ ] Upload file `.wav` → audio player hiển thị
- [ ] Upload file `.mp3` → audio player hiển thị
- [ ] Nhấn "Transcribe" → spinner → transcript hiển thị
- [ ] Transcript text area editable → sửa text → text thay đổi

### Analyze
- [ ] Nhấn "Phân tích" → spinner → Epic/Task/Subtask hiển thị
- [ ] Mỗi task có: summary, assignee (hoặc TBD), deadline (hoặc N/A), priority
- [ ] Epic expanders mở được, nested tasks hiển thị đúng

### Export
- [ ] "Tải Markdown" → download file `.md` → mở được, có nội dung
- [ ] "Tải JSON" → download file `.json` → valid JSON, có `epics` key
- [ ] "Tải CSV" → download file `.csv` → mở Excel, có header + data rows

### Save & Jira
- [ ] "Lưu vào DB" → success message với ID
- [ ] Sidebar hiển thị cuộc họp vừa lưu
- [ ] "Đẩy lên Jira" → warning "STUB mode" (khi thiếu credentials)

### Edge Cases
- [ ] Transcribe khi chưa upload file → button disabled
- [ ] Analyze khi transcript trống → button disabled
- [ ] Lưu DB khi chưa nhập tên cuộc họp → warning message
- [ ] Upload file rất lớn (> 25MB) → xử lý hợp lý (error hoặc warning)

---

## Verification Sau Mỗi Code Change

Chạy đầy đủ:

```bash
flake8 . --max-line-length=100 && mypy . --ignore-missing-imports && pytest tests/ -v
```

| Tool | Mục đích | Pass criteria |
|------|----------|---------------|
| `flake8` | Lint style | 0 warnings |
| `mypy` | Type checking | 0 errors |
| `pytest` | Unit tests | 85/85 pass |
