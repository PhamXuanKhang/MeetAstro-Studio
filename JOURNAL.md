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
| Claude Code (Opus) | Debug submit_log, trích xuất conversation history, tổng hợp worklog entries | Phát hiện root cause python3 Windows issue, submit 49 entries thành công |

#### Học được
- Strategy Pattern (ABC) giúp swap provider dễ dàng — chỉ cần implement `analyze()` hoặc `transcribe()` theo interface
- Fallback chain cần log warning khi switch provider — không im lặng, phải trace được
- SQLite `sqlite3.connect()` tạo connection mới mỗi lần gọi — cần cùng file path chứ không dùng `:memory:` cho tests nhiều hàm
- `pyproject.toml` + editable install (`uv pip install -e .`) là cách chuẩn để Python biết về package structure
- Git hook trên Windows phải dùng `python` (không phải `python3`) — luôn kiểm tra `which python3` trước khi dùng

#### Nếu làm lại, sẽ làm khác
- Chạy setup_hooks.sh và test submit log ngay khi setup môi trường, trước khi bắt đầu code
- Setup pyproject.toml và package structure ngay từ đầu để tránh import issues về sau
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

---

### Tuần 3 — 26/04/2026

**Thành viên:** Phạm Xuân Khang, Vthuc, Duypt

#### Đã làm
- **Backend API & Worker Pipeline (Khang):**
  - Mở rộng FastAPI routers cho meetings, transcriptions, analysis, reviews, Jira, exports, settings, stream
  - Thiết kế job polling qua `/api/v1/jobs/{job_id}` và health endpoint `/api/v1/health`
  - Tách các tác vụ dài sang Celery worker với Redis broker/result backend
  - Chuẩn hóa service layer cho audio ingestion, transcription, analysis, validation, summarization, cleanup
- **Database & Security (Khang, Duypt):**
  - Chuẩn bị hướng chuyển từ prototype local DB sang runtime có auth/ownership rõ hơn
  - Bổ sung rate limiting, CORS config, credential handling và tài liệu security
  - Cập nhật schema/docs để phản ánh review flow và trạng thái xử lý meeting
- **Frontend / Prototype Evolution (Vthuc, Duypt):**
  - Thử nghiệm desktop UI và upload/review flow trước khi chốt hướng Electron
  - Cải thiện tài liệu luồng audio/Jira để frontend và backend cùng bám contract
- **Docs & QA:**
  - Cập nhật architecture, API reference, data flow, Celery task docs, evaluation/test plan
  - Bổ sung kiểm thử cho service/provider/API paths quan trọng

#### Khó nhất tuần này
- Chuyển từ app prototype chạy đồng bộ sang kiến trúc API + worker async khiến state management phức tạp hơn
- Cần phân biệt rõ việc nào chạy qua Supabase/direct data view, việc nào phải đi qua FastAPI job pipeline
- Review flow cần giữ đúng schema Epic → Task → Subtask nhưng vẫn cho phép người dùng sửa trước khi push Jira

#### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code | Refactor backend API/service/worker theo từng bước nhỏ | Tách được pipeline rõ ràng, dễ test hơn |
| Claude Code | Viết và rà soát docs kỹ thuật | Architecture và API docs đồng bộ hơn với code |
| Claude Code | Debug test failures khi đổi schema/config | Giữ được test suite cho các module quan trọng |

#### Học được
- Với tác vụ AI/audio dài, job queue + polling an toàn hơn HTTP request chạy lâu
- API contract cần được viết sớm để frontend không phụ thuộc vào chi tiết service nội bộ
- Security docs phải đi cùng thay đổi auth/credential, không để đến cuối dự án mới bổ sung

#### Nếu làm lại, sẽ làm khác
- Chốt contract API/job status sớm hơn trước khi mở rộng nhiều router
- Viết migration note song song với thay đổi database runtime để docs luôn đồng bộ

#### Kế hoạch tuần tới
- Chốt frontend desktop chính bằng Electron + React/TypeScript
- Hoàn thiện Supabase Auth/DB integration
- Kết nối review/action item flow từ UI đến backend pipeline

---

### Tuần 4 — 11/05/2026

**Thành viên:** Phạm Xuân Khang, Vthuc, Duypt

#### Đã làm
- **Electron Desktop App (Khang, Duypt):**
  - Chuyển trọng tâm frontend sang `electron-app/` với React, TypeScript, Vite và Electron
  - Xây dựng các màn hình auth, meeting history, upload/recording, transcript review, action item review, settings
  - Thêm Supabase email/password auth, routing, store/state management và Axios API client
- **Supabase Migration (Duypt, Vthuc, Khang):**
  - Chuẩn hóa Supabase SDK/API layer, domain models và backend contract v1
  - Chuyển dữ liệu meeting/transcript/analysis/action items sang Supabase-first runtime
  - Ghi rõ local DB/Flet/Streamlit là prototype/legacy context trong docs
- **Backend Contract & Integration:**
  - Đồng bộ FastAPI endpoints với Electron UI cho upload, job polling, analysis, review, Jira push
  - Cập nhật settings/Jira config flow và error handling
  - Bổ sung deploy/release workflow nền tảng cho backend và desktop app
- **Docs:**
  - Cập nhật frontend docs, Supabase schema, architecture và deployment notes

#### Khó nhất tuần này
- Supabase Auth chạy ở frontend nhưng backend vẫn cần service-role access an toàn, nên phải tách rõ trách nhiệm client/server
- Electron IPC, recording sidecar và API polling cần phối hợp để UX không bị treo khi job chạy lâu
- Migration từ nhiều prototype UI sang một frontend chính làm docs dễ bị mâu thuẫn nếu không cập nhật kỹ

#### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code | Rà soát Electron app structure và backend contract | Xác định rõ boundary Electron ↔ FastAPI ↔ Supabase |
| Claude Code | Cập nhật docs migration và Supabase schema | Giảm mâu thuẫn giữa prototype cũ và runtime hiện tại |
| Claude Code | Debug TypeScript/API integration issues | UI kết nối backend ổn định hơn |

#### Học được
- Electron phù hợp hơn Streamlit/Flet cho desktop app cần auth, IPC recording và release installer
- Supabase SDK nên xử lý auth/data view ở client, còn AI processing/upload/Jira push nên đi qua backend
- Tài liệu phải gọi rõ cái gì là current runtime, cái gì là prototype history

#### Nếu làm lại, sẽ làm khác
- Định nghĩa naming convention cho meeting/action item models giữa frontend và backend sớm hơn
- Chuẩn bị migration checklist trước khi chuyển frontend/database runtime để đảm bảo docs nhất quán

#### Kế hoạch tuần tới
- Hoàn thiện live recording/realtime transcription path
- Polish UI theo design system
- Kiểm tra release packaging và tài liệu nộp bài

---

### Tuần 5 — 17/05/2026

**Thành viên:** Phạm Xuân Khang, Vthuc, Duypt

#### Đã làm
- **Live Streaming & Recording (Khang):**
  - Hoàn thiện realtime audio streaming/live transcription path cho Electron + FastAPI
  - Kết nối WebSocket/recording flow với transcript update và job status
  - Cải thiện xử lý audio chunk, upload và fallback provider behavior
- **Analysis, Review & Jira Flow (Duypt, Vthuc, Khang):**
  - Kết nối upload/provider/push-to-Jira từ UI đến backend
  - Cải thiện transcript review, speaker workflow, action item tree, create/edit/re-analyze flow
  - Tinh chỉnh phân tích tiếng Việt/tiếng Anh và Jira credential/error handling
- **UI Polish & Release (Khang):**
  - Áp dụng design-system polish cho Electron views và website/download pages
  - Chuẩn bị Windows installer `MeetAstro-Setup-*.exe` qua release workflow/local release script
  - Làm rõ submit scope, limitations và verification checklist
- **Submission Docs:**
  - Tổng hợp git log toàn nhóm để kiểm tra tính đầy đủ và cập nhật README
  - Liên kết architecture diagram, journal, worklog, product spec và evaluation docs từ README

#### Khó nhất tuần này
- Live audio path có nhiều boundary: Electron IPC, Python sidecar/recording, FastAPI stream, worker/provider, Supabase persistence
- Jira flow cần vừa hỗ trợ stub/missing credentials vừa hiển thị lỗi đủ rõ cho người dùng
- Tài liệu cuối kỳ phải phản ánh toàn bộ lịch sử project nhưng không làm người đọc nhầm prototype cũ với kiến trúc hiện tại

#### AI tool đã dùng
| Tool | Dùng để làm gì | Kết quả |
|---|---|---|
| Claude Code | Rà soát git log và tài liệu hiện có | Xác nhận docs đồng bộ với code thực tế |
| Claude Code | Cập nhật README theo phong cách landing page | README có thumbnail, badges, deliverables links |
| Claude Code | Kiểm tra consistency giữa docs và architecture hiện tại | Giảm link thiếu và mâu thuẫn runtime |

#### Học được
- Realtime UX cần observable status rõ ràng, không chỉ xử lý backend đúng
- Release packaging nên được xem là một phần sản phẩm, không phải bước phụ cuối cùng
- README cho submission cần đóng vai trò landing page: người chấm phải thấy ngay sản phẩm, kiến trúc, tài liệu và cách chạy

#### Nếu làm lại, sẽ làm khác
- Tạo screenshot/thumbnail UI sớm hơn thay vì dùng architecture diagram làm ảnh đại diện tạm thời

#### Kế hoạch tuần tới
- Thu thập feedback demo và cập nhật backlog production
- Nếu có thời gian, bổ sung screenshot UI thật cho thumbnail
- Theo dõi feedback demo và cập nhật backlog cho giai đoạn production tiếp theo
