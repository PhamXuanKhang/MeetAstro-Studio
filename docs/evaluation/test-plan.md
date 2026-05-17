# Test Plan

Chiến lược testing cho AI Meeting Assistant.

---

## Tổng quan

| Loại test | Coverage | Status |
|-----------|----------|--------|
| **Unit tests** | 14 test files trong `tests/` | Đã chạy thành công với dev deps |
| **Integration tests** | `tests/test_integration.py`, mock external APIs | E2E script `test_e2e.sh` sẵn sàng |
| **Manual smoke test** | Electron UI + FastAPI + worker + real audio | Cần chạy định kỳ |
| **Eval test** | AI quality: recall, precision, WER | Chưa tự động hóa |

---

## Unit Tests

### Test files hiện có

| File | Mô tả |
|------|-------|
| `tests/test_schema.py` | Domain schema, enum, serialization round-trip |
| `tests/test_openai_analyzer.py` | Mock OpenAI analyzer, JSON parsing, retry/error handling |
| `tests/test_openai_transcriber.py` | Mock OpenAI Whisper API transcriber |
| `tests/test_openai_diarize_transcriber.py` | Mock OpenAI diarization transcriber |
| `tests/test_whisper_livekit_transcriber.py` | Mock Whisper via LiveKit transcriber |
| `tests/test_transcription_service.py` | Plain transcription + diarization fallback về plain OpenAI transcription |
| `tests/test_analysis_service.py` | Analysis orchestration, empty transcript validation |
| `tests/test_validation_service.py` | Confidence scoring, rule-based cross validation |
| `tests/test_recording_service.py` | Recording service orchestration |
| `tests/test_exporter.py` | Markdown/JSON/CSV export |
| `tests/test_jira_client.py` | Jira REST payloads, auth, stub mode |
| `tests/test_jira_service.py` | Jira push orchestration Epic -> Task -> Subtask |
| `tests/test_audio_ingestion.py` | Audio upload validation, ffmpeg normalization, video-to-audio extraction |
| `tests/test_integration.py` | Mocked integration flow |
| `tests/__init__.py` | Test package marker |

### Chạy tests

```bash
# Tất cả tests
pytest tests/ -v

# Một file cụ thể
pytest tests/test_transcription_service.py -v

# Một test class cụ thể
pytest tests/test_schema.py::TestPriority -v

# Một test cụ thể
pytest tests/test_schema.py::TestPriority::test_values -v

# Với coverage nếu cần
pytest tests/ -v --cov=src --cov-report=term-missing
```

### Lưu ý quan trọng

- **External APIs:** Tất cả OpenAI, Whisper, Jira calls phải được mock trong unit test.
- **Database:** Runtime dùng Supabase qua `src/db/supabase_client.py`; không thêm SQLite/local PostgreSQL test path mới.
- **Transcription fallback:** Chỉ cho phép fallback từ diarization sang plain OpenAI Whisper transcription. Không dùng Local Whisper.
- **Prompt changes:** Sau khi sửa prompt/analyzer, verify output parse được thành `MeetingAnalysis` và match Jira schema Epic/Task/Subtask.

---

## Integration Test Plan

### E2E Flow Test

Script `test_e2e.sh` đã có sẵn, chạy end-to-end với audio thật:

```text
Audio file (<= 2 phút)
    -> POST /api/v1/meetings (tạo meeting)
    -> POST /api/v1/meetings/{id}/audio (upload + trigger transcribe)
    -> poll /api/v1/jobs/{job_id}
    -> assert transcript not empty
    -> export JSON
```

**Cần:** audio file mẫu tại `data/recordings/test_audio.mp3`, Supabase env, Redis + worker đang chạy, `OPENAI_API_KEY`.

```bash
# Chạy E2E test
./test_e2e.sh
```

### Diarization Fallback Integration Test

1. Mock diarization provider lỗi transient.
2. Verify service fallback sang plain OpenAI transcription.
3. Verify transcript output vẫn được lưu và pipeline không bị gián đoạn.

### Jira Integration Test

1. Setup Atlassian sandbox nếu có.
2. Set `JIRA_*` env vars.
3. Chạy push approved review items qua `POST /api/v1/meetings/{id}/jira/push`.
4. Poll `/api/v1/jobs/{job_id}` và verify issues tạo đúng trên Jira dashboard.

---

## Manual Smoke Test Checklist

Run `python -m frontend.main` với API + worker đang chạy và verify:

### Upload & Transcribe

- [ ] Upload file `.wav` -> job được queue và transcript hiển thị sau polling.
- [ ] Upload file `.mp3` -> job được queue và transcript hiển thị sau polling.
- [ ] Upload file `.m4a`, `.ogg`, `.mp4`, `.mkv`, `.webm` -> được convert và transcribe đúng.
- [ ] Bật/tắt diarization -> transcript vẫn trả về hợp lệ.
- [ ] Transcript field editable -> edits được lưu qua `PATCH /transcript`.

### Analyze

- [ ] Click "Analyze" -> job được queue -> Epic/Task/Subtask hiển thị.
- [ ] Each task shows summary, assignee (or TBD), deadline (or N/A), priority.
- [ ] Low-confidence/flagged items được hiển thị để review.

### Review

- [ ] Approve một item.
- [ ] Reject một item.
- [ ] Edit item rồi approve.
- [ ] Approve all hoạt động đúng.

### Export

- [ ] "Export Markdown" -> Save As dialog -> `.md` mở đúng.
- [ ] "Export JSON" -> valid JSON, có `epics`.
- [ ] "Export CSV" -> header + data rows.

### Save & Jira

- [ ] Meeting appears in History after analysis.
- [ ] "Push to Jira" bị chặn nếu còn pending review items.
- [ ] "Push to Jira" chạy STUB mode khi thiếu credentials.

### Edge Cases

- [ ] Transcribe khi chưa upload file -> button disabled hoặc API trả lỗi rõ.
- [ ] Analyze khi transcript trống -> button disabled hoặc API trả lỗi rõ.
- [ ] Upload file rất lớn (> 25MB) -> xử lý hợp lý bằng error/warning.

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
| `pytest` | Unit tests | All passing |

---

## API Endpoints Testing

API endpoints cần test (tham khảo `src/api/routers/`):

| Router | Endpoints cần smoke test |
|--------|-------------------------|
| `meetings.py` | POST /meetings, GET /meetings, GET /meetings/{id}, PATCH /meetings/{id}, DELETE /meetings/{id} |
| `transcriptions.py` | GET /meetings/{id}/transcript, PATCH /meetings/{id}/transcript |
| `analysis.py` | POST /meetings/{id}/analyze |
| `reviews.py` | GET /meetings/{id}/reviews, PATCH /reviews/{id}, POST /meetings/{id}/reviews/approve-all |
| `jira.py` | POST /meetings/{id}/jira/push |
| `exports.py` | GET /meetings/{id}/export/{format} |
| `stream.py` | Streaming endpoints |
| `settings.py` | GET/PUT settings |
| `main.py` | GET /api/v1/health |

---

## Database Migrations Testing

Khi chạy migration mới:

```bash
# Chạy migration
alembic upgrade head

# Verify schema
alembic current
alembic history --ind -10

# Rollback nếu cần
alembic downgrade -1
```

Test migration rollback path trên dev trước khi apply lên production.
