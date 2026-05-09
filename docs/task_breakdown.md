# MeetAstro — Master Task Breakdown
> **Tổng hợp từ toàn bộ brainstorm session + diagrams đã chốt**
> Cập nhật lần cuối dựa trên: Context Diagram, ERD, Screenflow, System Architecture, Use Case Diagrams (Phase 1 MVP)

---

## 📌 Quy ước đọc tài liệu

| Ký hiệu | Ý nghĩa |
|---------|--------|
| 🟥 P0 | Must-have — blocking nếu thiếu |
| 🟧 P1 | Should-have — cần cho UX hoàn chỉnh |
| 🟦 P2 | Nice-to-have — Phase sau |
| `[UC: Xx]` | Use case ID tương ứng |
| `→` | Output chuyển thành Input của task tiếp theo |

**Phân công cố định:**
- **Duy** — Supabase, database schema, migrations, FastAPI endpoints, RLS policies
- **Thức** — AI pipeline (Whisper, GPT-4o), Celery workers, chunking, audio processing
- **Khang** — Electron UI screens (React/TypeScript), API contract design; Flet là tạm thời và sẽ được xóa sau khi Electron hoàn thiện

---

## ═══════════════════════════════════════
## PHASE 1.1 — Foundation
### Mục tiêu: App chạy được, user đăng nhập, cấu hình được Jira & OpenAI
---

### Task 1.1-A — Database Schema & Supabase Foundation
**Người phụ trách:** Duy
**Use cases:** A1, A2, A3, A4, A5, A6, A8 (backend layer); B1, B2, B4 (data layer)

#### Subtasks

**[1.1-A.1] Thiết kế & migrate toàn bộ database schema** 🟥 P0
- **Input:** ERD đã chốt (7 tables: AUTH_USERS, PROFILES, PROVIDER_CONFIGS, MEETINGS, TRANSCRIPT_SEGMENTS, ANALYSIS_RESULTS, ACTION_ITEMS)
- **Output:** SQL migration files chạy được trên Supabase; tất cả tables tồn tại với đúng columns, types, FK constraints; self-referencing `action_items.parent_id` hoạt động
- **Ghi chú:** Bao gồm enum types cho `meetings.status` (8 states: pending, transcribing, transcribed, analyzing, draft, approved, pushed, failed), `action_items.item_type`, `review_status`, `sync_status`, `priority`

**[1.1-A.2] Cấu hình Supabase Auth & RLS policies** 🟥 P0
- **Input:** Supabase project, danh sách tables có `user_id`
- **Output:** Google OAuth provider được enable; RLS enabled trên tất cả app tables; policies "user chỉ thấy data của mình" được verify; trigger tự tạo `profiles` row khi `auth.users` insert
- **Ghi chú:** Test bằng 2 test accounts khác nhau — account A không đọc được data account B

**[1.1-A.3] FastAPI JWT middleware cho protected routes** 🟥 P0
- **Input:** Supabase JWT secret (từ Supabase project settings)
- **Output:** FastAPI middleware verify `Authorization: Bearer <jwt>` trên tất cả protected endpoints (`/api/v1/settings/*`, `/api/v1/meetings/*`); extract `user_id` từ JWT claims, inject vào request context; trả 401 nếu token invalid/expired
- **Ghi chú:** ~~FastAPI Auth proxy endpoints đã bị loại~~. Auth (register/login/OAuth/forgot-password) do Electron xử lý trực tiếp qua Supabase SDK. FastAPI chỉ verify token, không proxy auth.

**[1.1-A.4] CRUD endpoints cho Provider Configs (Jira + OpenAI)** 🟥 P0
- **Input:** `PROVIDER_CONFIGS` table, Fernet encryption helper
- **Output:** `PUT /api/v1/settings/providers/jira` (lưu encrypted), `GET /api/v1/settings/providers/jira` (trả về masked), `DELETE /api/v1/settings/providers/jira`; tương tự cho `/api/v1/settings/providers/openai`; `POST /api/v1/settings/providers/jira/test` gọi Jira `/rest/api/3/myself` verify; `POST /api/v1/settings/providers/openai/test` gọi `/v1/models`
- **Ghi chú:** `api_key` phải Fernet-encrypt trước khi lưu DB; GET response mask giá trị (chỉ trả `***` + 4 ký tự cuối); generic pattern `/api/v1/settings/providers/{provider_name}` để dễ mở rộng

**[1.1-A.5] Indexes & performance baseline** 🟧 P1
- **Input:** Schema đã tạo ở A.1
- **Output:** Indexes tạo trên: `meetings(user_id, status)`, `meetings(created_at DESC)`, `action_items(meeting_id)`, `action_items(parent_id)`, `transcript_segments(meeting_id, start_time)`, `provider_configs(user_id, provider_name)`
- **Ghi chú:** Không cần benchmark, chỉ cần indexes tồn tại trước khi load test

**Trích dẫn:**
- ERD schema → `ERD_diagram.md` §2.3 PROVIDER_CONFIGS, §2.4 MEETINGS, §2.7 ACTION_ITEMS
- Auth flow → `screenflow.md` §2.1 Auth Flow
- RLS requirement → Brainstorm session: "RLS policies cho mọi bảng có user_id — multi-tenant isolation"

---

### Task 1.1-B — AI Provider Integration & Audio Pipeline Foundation
**Người phụ trách:** Thức
**Use cases:** B4 (OpenAI key validation), C2, C3 (file ingestion backend)

#### Subtasks

**[1.1-B.1] Fernet encryption helper & key management** 🟥 P0
- **Input:** `APP_SECRET_KEY` env var, `cryptography` lib
- **Output:** Module `utils/encryption.py` với `encrypt(plaintext) → ciphertext`, `decrypt(ciphertext) → plaintext`; unit tests pass; dùng chung cho cả Jira token và OpenAI key
- **Ghi chú:** Duy cần module này cho 1.1-A.4 — cần deliver trước hoặc song song

**[1.1-B.2] File ingestion: audio upload & video-to-audio extraction** 🟥 P0
- **Input:** File `.mp3/.wav/.m4a/.ogg` hoặc `.mp4/.mkv/.webm` từ client upload (multipart)
- **Output:** Audio được normalize về `.wav` 16kHz mono (Whisper optimal) tại VPS temp path `data/tmp/{meeting_id}.wav`; `meetings.audio_storage_path` được update với `file://` URI của file gốc trên máy client (do client gửi kèm); `meetings.audio_duration_seconds` được tính và lưu; file temp VPS bị xóa sau khi Whisper transcription xong
- **Ghi chú:** Audio không lưu vĩnh viễn trên VPS hoặc Supabase Storage — canonical path là `file://` URI trên máy user. Dùng `ffmpeg-python` cho extraction và normalization; validate MIME type trước khi process

**[1.1-B.3] Celery + Redis setup & worker boilerplate** 🟥 P0
- **Input:** `docker-compose.yml` với Redis service, Celery config
- **Output:** Celery app khởi động được; `beat` + `worker` chạy trong Docker; health check endpoint `/health/workers` trả về số worker đang active; task `debug_task` chạy được end-to-end qua Redis queue
- **Ghi chú:** Concurrency mặc định 2 jobs/worker theo architecture diagram; dùng `redis://localhost:6379/0` cho dev

**[1.1-B.4] OpenAI client wrapper với BYOK support** 🟧 P1
- **Input:** `PROVIDER_CONFIGS` table, OpenAI Python SDK
- **Output:** `AIClient` class nhận `user_id`, tự load API key từ DB, khởi tạo `openai.Client`; fallback về app-level key nếu user chưa config BYOK; unit tests mock API calls
- **Ghi chú:** Design pattern: factory method, không hardcode key trong bất kỳ file nào

**Trích dẫn:**
- System architecture → `system_architecture.md`: "Electron → FastAPI /api/v1 (HTTP: Upload, AI jobs) → Redis queue → Celery Workers"
- File storage → `system_architecture.md`: "audio_storage_path ref → Audio (local — user machine)"
- BYOK requirement → Brainstorm session: "B4 promote P1→P0: cần BYOK để beta test sớm"

---

### Task 1.1-C — Auth UI & Settings UI Electron
**Người phụ trách:** Khang
**Use cases:** A1, A2, A3, A4, A5, A6, A8 (frontend); B1, B2, B4 (frontend)
> **Lưu ý:** Electron là target frontend chính thức — UI Electron sẽ thay thế toàn bộ 1.1-C sau khi Electron build xong. Auth dùng Supabase SDK trực tiếp (không qua FastAPI proxy).

#### Subtasks

**[1.1-C.1] LoginPage & RegisterPage** 🟥 P0
- **Input:** Supabase SDK (auth calls trực tiếp, không qua FastAPI); Flet framework; screenflow diagram
- **Output:** `LoginPage`: email/pass form + "Sign in with Google" button + links tới Register/ForgotPassword; `RegisterPage`: form đăng ký + email verification notice screen ("Check your email"); form validation client-side (email format, password ≥8 chars); loading state khi đang call API
- **Ghi chú:** Google OAuth button mở browser tab; sau OAuth success Supabase SDK trả về session/JWT; Flet lưu JWT local để gọi FastAPI protected endpoints

**[1.1-C.2] ForgotPasswordPage & ResetLinkSent screen** 🟥 P0
- **Input:** Supabase SDK `resetPasswordForEmail()`; screenflow §2.1
- **Output:** `ForgotPasswordPage`: email input form; `ResetLinkSentPage`: confirmation message + "Back to Login" link; error handling (email không tồn tại → vẫn show success để tránh user enumeration)
- **Ghi chú:** Theo screenflow: Login → Forgot Password → Reset Link Sent → Login

**[1.1-C.3] SettingsPage: Jira Config tab + OpenAI Config tab** 🟥 P0
- **Input:** `PUT /api/v1/settings/providers/jira`, `POST /api/v1/settings/providers/jira/test`, `PUT /api/v1/settings/providers/openai`; screenflow §1 "Settings Page (Jira Config)"
- **Output:** `SettingsPage` có 2 tabs: (1) Jira: input domain, email, API token + "Test Connection" button với feedback ✅/❌ + inline hướng dẫn lấy token; (2) OpenAI: input API key + model selector dropdown + validate button; masked display khi đã save (hiện `sk-...xxxx`)
- **Ghi chú:** Screenflow chỉ ghi "Settings Page (Jira Config)" nhưng scope đã chốt phải có cả OpenAI tab

**[1.1-C.4] App navigation shell & auth guard** 🟥 P0
- **Input:** JWT từ login; Flet routing; screenflow "Main Navigation — APP Node"
- **Output:** `AppShell` component với bottom/side navigation: New Meeting (Home) / History / Settings; auth guard redirect về LoginPage nếu token invalid/expired; JWT refresh logic; persistent session (lưu token local)
- **Ghi chú:** Screenflow: "Auth Success → APP Node → 3 màn hình chính"

**[1.1-C.5] API contract document cho Phase 1.1** 🟧 P1
- **Input:** Tất cả endpoints từ 1.1-A; Flet UI requirements từ 1.1-C
- **Output:** `docs/api/phase1.1.md` liệt kê request/response schema cho mỗi endpoint; được dùng làm "contract" giữa Duy (backend) và Khang (UI)
- **Ghi chú:** Khang define contract trước khi Duy implement — API-first approach để unblock UI development

**Trích dẫn:**
- Screen structure → `screenflow.md` §1 Authentication, §2 Main Navigation
- Auth flows → `screenflow.md` §2.1 Auth Flow
- Settings scope → Use case diagram `usecase_diagram.md` Diagram 1: B1, B2, B4

---

## ═══════════════════════════════════════
## PHASE 1.2 — Capture & Process
### Mục tiêu: User upload/record được, thấy transcript streaming với diarization
---

### Task 1.2-A — Meeting Management APIs & Recording Backend
**Người phụ trách:** Duy
**Use cases:** C1, C2, C3, C4, C7, C9 (backend)

#### Subtasks

**[1.2-A.1] Meeting CRUD APIs** 🟥 P0
- **Input:** `MEETINGS` table; authenticated user JWT
- **Output:** `POST /meetings` (tạo, status='pending'), `GET /meetings` (list của user, sort created_at DESC), `GET /meetings/{id}` (detail), `DELETE /meetings/{id}` (xóa meeting + audio file trên Storage); tất cả endpoints enforce user ownership qua RLS
- **Ghi chú:** DELETE phải cascade xóa: transcript_segments, analysis_results, action_items

**[1.2-A.2] File upload endpoint & audio ingestion** 🟥 P0
- **Input:** Multipart form upload (`POST /api/v1/meetings/{meeting_id}/upload`); audio path gốc từ client (file:// URI)
- **Output:** Endpoint nhận file + `client_path` (file:// URI), normalize audio về WAV temp, update `meetings.audio_storage_path` = client_path, enqueue `transcribe_task` lên Redis, update status='transcribing', trả về `{meeting_id, job_id, status: "queued"}`
- **Ghi chú:** Validate MIME type + file size (max configurable, default 500MB); file temp VPS bị xóa sau transcription; audio không lưu permanent trên server

**[1.2-A.3] Pipeline progress polling endpoint** 🟥 P0
- **Input:** `celery_task_id`; Celery result backend (Redis)
- **Output:** `GET /jobs/{task_id}` trả về `{state: 'PROGRESS'|'SUCCESS'|'FAILURE', progress: 0-100, message: 'Transcribing chunk 3/8...', result?: {...}}`; client poll mỗi 2-3 giây; khi SUCCESS tự động trả về meeting data mới nhất
- **Ghi chú:** Celery task phải update `meta` với progress info để endpoint này đọc được

**[1.2-A.4] Live recording session management APIs** 🟧 P1
- **Input:** Recording chunks từ Flet client; `MEETINGS` table
- **Output:** `POST /meetings/{id}/recording/start` (init session), `POST /meetings/{id}/recording/chunk` (nhận audio chunk, enqueue partial transcribe), `POST /meetings/{id}/recording/stop` (finalize, enqueue final chunk + merge)
- **Ghi chú:** Chunks lưu temp ở `data/recordings/{meeting_id}/chunk_{n}.wav`; sau stop, merge thành 1 file rồi cleanup temp

**Trích dẫn:**
- System flow → `system_architecture.md`: "FastAPI API → Save audio + create meeting status → File storage"
- Meeting status states → Brainstorm session: 8-state enum (pending → transcribing → ...)
- Use cases → `usecase_diagram.md` Diagram 2: C1–C9

---

### Task 1.2-B — Transcription Worker (Whisper + Diarization + Streaming)
**Người phụ trách:** Thức
**Use cases:** D1, D2, D3, D5 (backend); C4, C7 (processing)

#### Subtasks

**[1.2-B.1] Chunked transcription Celery task (Whisper API)** 🟥 P0
- **Input:** Audio file path (Supabase Storage URL hoặc local path); `meeting_id`; OpenAI API key từ `AIClient`
- **Output:** `transcribe_task(meeting_id)` chạy được: download audio → split thành chunks (configurable, default 60s overlap 5s) → gọi `whisper-1` cho từng chunk song song → merge kết quả → lưu vào `transcript_segments` → update `meetings.status='transcribed'`; progress update qua Celery `update_state`
- **Ghi chú:** Overlap 5s giữa chunks để tránh mất câu; handle OpenAI rate limits với exponential backoff

**[1.2-B.2] Diarization pipeline** 🟥 P0
- **Input:** Raw Whisper transcript text + timestamps; audio file
- **Output:** Mỗi `transcript_segments` row có `speaker` field được điền (VD: "Speaker A", "Speaker B"); speakers được phân biệt nhất quán trong cùng 1 meeting
- **Ghi chú:** Dùng `pyannote.audio` hoặc Whisper large-v3 với `--diarize` nếu available; fallback: simple VAD-based speaker change detection; label format chuẩn: "Speaker A", "Speaker B" (không phải "SPEAKER_00")

**[1.2-B.3] Real-time transcript streaming** 🟥 P0
- **Input:** `transcript_segments` được INSERT dần vào Supabase khi từng chunk transcribe xong
- **Output:** Celery worker insert mỗi segment mới vào Supabase `transcript_segments` table; Electron subscribe Supabase Realtime channel `transcript_segments:meeting_id=eq.{id}` → nhận INSERT events → append segment vào UI realtime; subscription kết thúc khi `meetings.status='transcribed'`
- **Ghi chú:** Có 2 streaming mode:
  1. **Supabase Realtime** (canonical theo contract v1 D1): Worker INSERT vào DB, client subscribe channel
  2. **WhisperLiveKit SSE (C10)**: Backend WebSocket → WhisperLiveKit Server → SSE → Frontend. Xem `backend-contract-v1.md` §C10

**[1.2-B.4] Transcript CRUD APIs** 🟥 P0
- **Input:** `TRANSCRIPT_SEGMENTS` table; `meeting_id`
- **Output:** `GET /meetings/{id}/transcript` (trả về list segments sorted by start_time), `PATCH /meetings/{id}/transcript/segments/{seg_id}` (sửa content + speaker), `PUT /meetings/{id}/transcript/speakers` (bulk rename speaker — đổi "Speaker A" → "Anh Nam" trên toàn bộ segments)
- **Ghi chú:** Sau khi user sửa transcript → status giữ 'transcribed', chưa chuyển sang 'analyzing'

**[1.2-B.5] Live recording chunking optimization** 🟧 P1
- **Input:** Audio stream từ recording session; chunk config (30-60s)
- **Output:** Mỗi chunk completed → tự động enqueue `partial_transcribe_task` → kết quả append realtime; cuối cùng merge tất cả partial transcripts theo thứ tự time
- **Ghi chú:** Cải tiến chunking để không bị duplicate sentence ở chunk boundary

**Trích dẫn:**
- Architecture → `system_architecture.md`: "Audio transcription (Whisper API / WhisperLiveKit) → Action item analysis (GPT-4o)"
- Streaming → `screenflow.md` §3 Upload Workflow: "Transcribing State → Review Transcript"
- D3 diarization → `usecase_diagram.md` Diagram 2: "D2 Xem transcript hoàn chỉnh <<include>> D3 Xem diarization"
- WhisperLiveKit SSE → `backend-contract-v1.md` §C10

---

### Task 1.2-C — Meeting Input UI & Transcript UI (Flet)
**Người phụ trách:** Khang
**Use cases:** C1, C2, C3, C4, C7, C9 (frontend); D1, D2, D3, D4, D5 (frontend)

#### Subtasks

**[1.2-C.1] NewMeetingPage: Upload workflow** 🟥 P0
- **Input:** `/meetings` và `/meetings/{id}/upload` APIs; screenflow §2.3 Upload File Flow
- **Output:** `NewMeetingPage` với 2 tabs (Upload / Record); Upload tab: title input + file picker (audio + video formats) + drag-drop zone + upload progress bar; sau upload → navigate tới `TranscribingStatePage`
- **Ghi chú:** Screenflow: "New Meeting Page → Upload File → Transcribing State"

**[1.2-C.2] LiveRecordingScreen** 🟥 P0
- **Input:** `/meetings/{id}/recording/*` APIs; system audio capture; screenflow §2.4 Live Record Flow
- **Output:** `LiveRecordingScreen`: waveform visualization + timer + Pause/Stop buttons; realtime transcript panel hiển thị chunks mới nhất; "Minimize" → `MiniPopupWindow` (PIP mode: compact timer + last transcript line + Stop button); "Stop" → navigate tới `FinalizingAIProcessingPage`
- **Ghi chú:** MiniPopup là feature đặc trưng trong screenflow diagram — phải có cho Phase 1

**[1.2-C.3] Processing state screens** 🟥 P0
- **Input:** `/jobs/{task_id}` polling; screenflow §2.3, §2.4
- **Output:** `TranscribingStatePage` (progress bar + step message "Đang transcribe chunk 3/8..."); `AIAnalyzingStatePage` (progress bar + "Đang phân tích..."); `FinalizingAIProcessingPage` (progress khi kết thúc record); tất cả poll API mỗi 2s → auto-navigate khi SUCCESS
- **Ghi chú:** Các state screens map với `meetings.status` enum

**[1.2-C.4] ReviewTranscriptPage (Pre-Analysis)** 🟥 P0
- **Input:** `GET /meetings/{id}/transcript`; screenflow: "Review Transcript (Pre-Analysis)" screen
- **Output:** `ReviewTranscriptPage`: list transcript segments, mỗi segment hiển thị speaker label (màu) + timestamp + text; inline edit text (D5); click speaker label → modal đổi tên + màu (D4); bulk rename speaker; "Analyze" button trigger E1 → navigate tới `AIAnalyzingStatePage`
- **Ghi chú:** Đây là screen quan trọng — user PHẢI qua đây trước khi trigger analysis

**[1.2-C.5] API contract cho Phase 1.2** 🟧 P1
- **Input:** UI requirements từ C.1–C.4; backend capabilities
- **Output:** `docs/api/phase1.2.md` với WebSocket contract cho streaming, recording chunk endpoints, transcript patch schema
- **Ghi chú:** Đặc biệt cần làm rõ WebSocket vs SSE để Thức chọn implementation

**Trích dẫn:**
- Screen flows → `screenflow.md` §2.3 Upload Flow, §2.4 Live Record Flow
- MiniPopup → `screenflow.md` §1: "Mini Pop-up (Real-time Transcript & Tasks)"
- Trigger Analysis button → `screenflow.md` §2.3: "User clicks 'Analyze' → AI Analyzing State"

---

## ═══════════════════════════════════════
## PHASE 1.3 — Analyze, Review & Deliver
### Mục tiêu: AI ra action items, user review, push lên Jira thành công
---

### Task 1.3-A — Analysis Worker & Review APIs
**Người phụ trách:** Duy
**Use cases:** E1, E2, E3, E4, E6 (backend); F1, F5, F6, F8 (backend)

#### Subtasks

**[1.3-A.1] GPT-4o analysis Celery task** 🟥 P0
- **Input:** Full transcript từ `transcript_segments` (join và sort by start_time); `meeting_id`; `AIClient` với user's OpenAI key
- **Output:** `analyze_task(meeting_id)` chạy: build transcript text → gọi GPT-4o với structured output schema → parse `MeetingAnalysis` object (summary, key_decisions, parking_lot, epics với nested tasks/subtasks) → lưu vào `ANALYSIS_RESULTS` → flatten tree thành `ACTION_ITEMS` rows (với `parent_id` self-ref) → update `meetings.status='draft'`; progress update qua Celery meta
- **Ghi chú:** Structured output dùng Pydantic model + OpenAI function calling hoặc `response_format=json_schema`; confidence_score cho từng action item

**[1.3-A.2] GPT-4o prompt engineering cho MeetAstro** 🟥 P0
- **Input:** Sample transcripts (tự tạo hoặc từ cuộc họp thật); output schema yêu cầu
- **Output:** System prompt + user prompt template trong `prompts/analyze_meeting.py`; output JSON schema với: `summary` (text), `key_decisions` (array string), `action_items` (nested: epic → task → subtask với name, description, assignee_speaker_name, deadline, priority, context, confidence_score); `parking_lot` (array string); README giải thích prompt reasoning
- **Ghi chú:** Prompt phải specify: "Extract in the SAME language as the transcript (Vietnamese/English)"; assignee = speaker name từ diarization; deadline = natural language ngày nếu được nhắc đến

**[1.3-A.3] Analysis & Review CRUD APIs** 🟥 P0
- **Input:** `ANALYSIS_RESULTS` + `ACTION_ITEMS` tables
- **Output:** `GET /meetings/{id}/analysis` (summary, key_decisions, parking_lot); `GET /meetings/{id}/action-items` (tree hoặc flat, query param `format=tree|flat`); `PATCH /action-items/{id}` (edit name, description, assignee, deadline, priority); `POST /action-items/{id}/approve`, `/reject`; `POST /meetings/{id}/action-items` (add manual item — F8); `PATCH /action-items/bulk` (bulk status update — F7 Phase 2)
- **Ghi chú:** Khi approve/reject → update `review_status`; `is_selected` dùng cho UI checkbox state

**[1.3-A.4] Meetings status transition logic** 🟧 P1
- **Input:** 8-state machine đã define; Celery task outcomes
- **Output:** `MeetingStatusManager` service handle transitions: invalid transitions bị reject (VD: không thể đi từ 'pushed' về 'analyzing'); status change trigger webhook/event nếu cần; `GET /meetings/{id}/status` trả về current state + timestamp
- **Ghi chú:** State machine: pending→transcribing→transcribed→analyzing→draft→approved→pushed; failed có thể từ bất kỳ state nào

**Trích dẫn:**
- Analysis flow → `system_architecture.md`: "Action item analysis (GPT-4o) → Save to PostgreSQL"
- Analysis output → `ERD_diagram.md` §2.5 ANALYSIS_RESULTS: summary_text, key_decisions, parking_lot, raw_response
- Action items schema → `ERD_diagram.md` §2.7 ACTION_ITEMS
- E4 Key Decisions vị trí → Brainstorm session: "E4 đặt trước E3 trong UI ordering"

---

### Task 1.3-B — Jira Push Worker & History APIs
**Người phụ trách:** Thức
**Use cases:** G1, G2, G3, G4 (backend); H1, H4, H5 (backend)

#### Subtasks

**[1.3-B.1] Jira API client** 🟥 P0
- **Input:** Jira credentials từ `PROVIDER_CONFIGS` (decrypted); `httpx` async client
- **Output:** `JiraClient` class với methods: `get_myself()` (test connection), `create_issue(project_key, issue_type, summary, description, parent_key=None)` → trả về issue key; `get_issue(key)`; handle errors (401, 403, 404, 429 rate limit); async + retry 3 lần với backoff
- **Ghi chú:** Jira Cloud API v3; auth = Basic Auth (email:token); issue types: "Epic", "Task", "Subtask"

**[1.3-B.2] Jira push Celery task (async, ordered)** 🟥 P0
- **Input:** List approved `ACTION_ITEMS` (status='approved', is_selected=True); `JiraClient`; Jira default project key
- **Output:** `push_to_jira_task(meeting_id)` chạy: query approved items → reconstruct tree (epics first) → tạo Epic → lấy epic_key → tạo Tasks với parent=epic_key → tạo Subtasks với parent=task_key → update từng item với `jira_issue_key`, `jira_issue_url`, `sync_status='synced'`; update `meetings.status='pushed'`; progress update mỗi issue created
- **Ghi chú:** Phase 1 KHÔNG set Jira `assignee` field (thiếu speaker→accountId mapping, Phase 2 mới làm). Thay vào đó, description Jira issue phải include dòng: "Người được giao (theo meeting): {assignee_speaker_name}"

**[1.3-B.3] Push status & retry endpoints** 🟥 P0
- **Input:** Celery task state; `ACTION_ITEMS.sync_status`
- **Output:** `POST /api/v1/meetings/{id}/jira/push` (trigger task, trả về `{job_id, status, unreviewed_count}`); `GET /api/v1/jobs/{task_id}` (progress); `POST /api/v1/meetings/{id}/jira/retry` (retry failed items — G3); Jira links đọc qua Supabase SDK từ `action_items` (G4)
- **Ghi chú:** Retry chỉ select items có `sync_status='failed'`, không push lại đã synced

**[1.3-B.4] History APIs** 🟥 P0
- **Input:** `MEETINGS` table; authenticated user
- **Output:** `GET /meetings` (list meetings của user: id, title, status, created_at, audio_duration, jira_links_count); `GET /meetings/{id}` (full detail: meeting + transcript + analysis + action_items); `DELETE /meetings/{id}` (cascade delete DB rows + xóa audio trên Storage)
- **Ghi chú:** Soft delete (deleted_at) cho Phase 3; Phase 1 là hard delete

**Trích dẫn:**
- Push flow → `context_diagram.md`: "Create epic / Task / Subtask → Jira → Return issue keys and URLs"
- Architecture push → `system_architecture.md`: "Push to Jira"
- History use cases → `usecase_diagram.md` Diagram 4: H1, H4, H5
- Assignee handling → Brainstorm session: "Phase 1: không set assignee Jira field, đưa tên speaker vào description"

---

### Task 1.3-C — Analysis/Review/Push/History UI (Electron)
**Người phụ trách:** Khang
**Use cases:** E2, E3, E4, E6 (frontend); F1, F5, F6, F8 (frontend); G1, G2, G3, G4 (frontend); H1, H4, H5 (frontend)

#### Subtasks

**[1.3-C.1] MeetingDetailScreen: Tab 1 (Summary) & Tab 2 (Transcript)** 🟥 P0
- **Input:** `GET /meetings/{id}/analysis`; `GET /meetings/{id}/transcript`; screenflow §5 Core Workspace
- **Output:** `MeetingDetailScreen` với tab navigation; Tab 1 Summary: summary text + key decisions list (bullet points) + parking lot section; Tab 2 Transcript: editable segment list với speaker labels màu sắc (reuse từ 1.2-C.4 ReviewTranscriptPage)
- **Ghi chú:** Meeting detail screen được navigate từ cả upload flow, record flow VÀ history (screenflow: "Select past meeting → Meeting Detail Screen")

**[1.3-C.2] MeetingDetailScreen: Tab 3 (Action Items) với Review UI** 🟥 P0
- **Input:** `GET /meetings/{id}/action-items?format=tree`; screenflow §6 Jira Sync Workflow
- **Output:** Tab 3 Action Items: tree view (Epic → Task → Subtask) với collapse/expand; mỗi item: checkbox (is_selected), confidence badge 🟢/🟡/🔴, name, assignee_speaker_name, deadline, priority; click item → edit modal (F1: sửa name/description/context); Approve button (F5) / Reject button (F6); "Add Task" button (F8): form inline hoặc modal với parent epic selector
- **Ghi chú:** Key decisions (E4) hiển thị ở Tab 1 phía trên action items — đúng thứ tự đã chốt

**[1.3-C.3] Jira Push flow UI** 🟥 P0
- **Input:** Push APIs từ 1.3-B.3; screenflow §6: "Approve → Push Jira processing State → Push to Jira API"
- **Output:** "Push to Jira" button (enabled khi ≥1 item approved + is_selected); `PushProgressScreen`: progress bar + live feed "Tạo Epic MEET-1...", "Tạo Task MEET-2..." + issue key list với clickable Jira links; nếu có failures → hiển thị failed items list + "Retry" button (G3)
- **Ghi chú:** Screenflow có "Push Jira processing State" là intermediate screen

**[1.3-C.4] Export Modal** 🟦 P2 → *Defer sang Phase 2 (H7)*
- **Ghi chú:** Đã chốt trong RRI: export defer Phase 2. Screenflow có Export Modal nhưng không nằm trong scope contract v1. Xem Task 2.6 — H7 Export với template.

**[1.3-C.5] HistoryPage** 🟥 P0
- **Input:** `GET /meetings` API; screenflow §2.5 History Revisit Flow
- **Output:** `HistoryPage`: list meetings với title + date + status badge (pill màu theo status) + jira links count + delete button; click row → navigate tới `MeetingDetailScreen`; delete → confirm dialog → call DELETE API
- **Ghi chú:** Screenflow: "History Page → Select past meeting → Meeting Detail Screen"

**Trích dẫn:**
- Tab structure → `screenflow.md` §5: "Tab 1: Summary, Tab 2: Transcript, Tab 3: Action Items"
- Jira sync flow → `screenflow.md` §6 Jira Sync Workflow
- Export → `screenflow.md` §6: "Export Modal (MD/JSON/CSV)"
- History → `screenflow.md` §2.5 History Revisit Flow

---

## ═══════════════════════════════════════
## PHASE 2 — Enhancement (P1)
### Mục tiêu: UX hoàn chỉnh, tính năng cộng tác, export nâng cao
---

### Task 2.1 — Auth & Account Improvements
**Người phụ trách:** Duy
**Use cases:** A7, A11

| Subtask | Input | Output | Priority |
|---------|-------|--------|----------|
| Đổi mật khẩu (A7) | Current + new password | Supabase `updateUser` call; success/error feedback | 🟧 P1 |
| ToS acceptance (A11) | ToS text; `profiles` table thêm field `tos_accepted_at` | Checkbox screen trước Register; gate login nếu chưa accept | 🟧 P1 |

---

### Task 2.2 — Advanced Settings
**Người phụ trách:** Duy + Khang
**Use cases:** B3, B5, B7

| Subtask | Người | Input | Output | Priority |
|---------|-------|-------|--------|----------|
| In-app Jira token guide (B3) | Khang | Atlassian docs URL | Step-by-step guide screen/modal trong app | 🟧 P1 |
| Language selection (B5) | Duy + Thức | `provider_configs` thêm `preferred_language`; Whisper language param | Dropdown: English / Vietnamese / Auto-detect; pass vào Whisper API call | 🟧 P1 |
| Usage dashboard (B7) | Duy | `ANALYSIS_RESULTS.input/output_tokens`; `MEETINGS` count | Usage screen: meeting count / total tokens / estimated cost tháng này | 🟧 P1 |

---

### Task 2.3 — Recording UX Improvements
**Người phụ trách:** Thức + Khang
**Use cases:** C5, C6, C10

| Subtask | Người | Input | Output | Priority |
|---------|-------|-------|--------|----------|
| Pause/Resume recording (C5, C6) | Khang | Recording session API; Flet audio | Pause button freeze audio capture; Resume tiếp tục; timeline hiển thị "paused" segments | 🟧 P1 |
| Cancel pipeline (C10) | Thức | `celery_task_id`; Celery revoke API | `POST /jobs/{task_id}/cancel` revoke Celery task; cleanup temp files; update status='failed' | 🟧 P1 |

---

### Task 2.4 — Enhanced Transcript Features
**Người phụ trách:** Thức + Khang
**Use cases:** D7, D8, E9, E11

| Subtask | Người | Input | Output | Priority |
|---------|-------|-------|--------|----------|
| Re-run transcription (D7) | Thức | Existing audio file; new language setting | `POST /meetings/{id}/transcript/rerun`; xóa segments cũ → chạy lại transcribe task | 🟧 P1 |
| Download transcript (D8) | Khang | `GET /meetings/{id}/transcript?format=txt\|srt` | Export file txt (plain) hoặc srt (với timestamps); download về máy | 🟧 P1 |
| Manual notes input (E9) | Khang | Notes textarea trong LiveRecordingScreen | `MEETINGS` thêm field `user_notes TEXT`; `PATCH /meetings/{id}/notes` save notes | 🟧 P1 |
| Combined analysis E9+transcript (E11) | Thức | `user_notes` + transcript; prompt template | System prompt augmentation: `<user_notes>{notes}</user_notes>` inject trước transcript analysis | 🟧 P1 |

---

### Task 2.5 — Review Enhancement
**Người phụ trách:** Duy + Khang
**Use cases:** F2, F3, F4, F7, F12

| Subtask | Người | Input | Output | Priority |
|---------|-------|-------|--------|----------|
| Assignee mapping (F12) | Duy | `SPEAKER_MAPPINGS` table mới; Jira Users API | `GET /jira/users` fetch Jira users; mapping table `speaker_name → jira_account_id`; edit mapping trong Transcript screen | 🟧 P1 |
| Set assignee Jira (F2) | Duy | `speaker_mappings` table; push task | Push task dùng mapping để set `assignee.accountId` trong Jira issue payload | 🟧 P1 |
| Edit deadline/priority (F3, F4) | Khang | Action items edit modal | Thêm date picker (deadline) + priority dropdown vào edit modal; `PATCH /action-items/{id}` | 🟧 P1 |
| Bulk approve (F7) | Khang | Checkbox multi-select trong Tab 3 | "Select all / Approve selected" button; `PATCH /action-items/bulk {ids, review_status}` | 🟧 P1 |

---

### Task 2.6 — Jira & History Enhancement
**Người phụ trách:** Thức
**Use cases:** G5, H6, H7

| Subtask | Input | Output | Priority |
|---------|-------|--------|----------|
| Override project (G5) | Dropdown Jira projects (`GET /jira/projects`); per-meeting project setting | `MEETINGS` thêm `jira_project_override`; push task dùng override nếu set | 🟧 P1 |
| Re-push old meeting (H6) | Meeting ở status 'pushed' hoặc 'failed'; existing action items | `POST /meetings/{id}/push-to-jira` với `reset=true` — set sync_status='pending' rồi push lại | 🟧 P1 |
| Export với template (H7) | Meeting data; 3 template types (MD/JSON/CSV) | `GET /meetings/{id}/export?format=md` trả về formatted export; preview trước download | 🟧 P1 |

---

## ═══════════════════════════════════════
## PHASE 3 — Future (P2)
### Để sau khi có feedback từ early users
---

| Task | Người dự kiến | Use cases | Mô tả ngắn | Priority |
|------|--------------|-----------|------------|----------|
| Profile & avatar (A9) | Khang | A9 | Supabase Storage cho avatar; profile edit form | 🟦 P2 |
| GDPR account deletion (A10) | Duy | A10 | Cascade delete tất cả user data; Supabase Auth delete | 🟦 P2 |
| Per-app audio capture (B6) | Thức | B6 | WASAPI/ScreenCaptureKit capture từ tab/app cụ thể | 🟦 P2 |
| Subscription management (B8) | Duy | B8 | Stripe integration; plan tiers; usage quota enforcement | 🟦 P2 |
| Transcript search (D9) | Duy + Khang | D9 | Full-text search trên segments; highlight kết quả | 🟦 P2 |
| Re-run analysis (E7) | Thức | E7 | Custom prompt hints; multiple analysis versions; diff view | 🟦 P2 |
| Note templates (E10) | Khang | E10 | 4 templates: Daily Standup / Decision / Discussion / Free-form | 🟦 P2 |
| Filter by confidence (F10) | Khang | F10 | Filter chips trên Tab 3: All / High / Medium / Low | 🟦 P2 |
| Drag-drop task hierarchy (F11) | Khang | F11 | Drag task từ Epic này sang Epic khác trong tree view | 🟦 P2 |
| Bidirectional Jira sync (G7, G8) | Thức | G7, G8 | Pull existing tasks; detect "done/update" intent trong meeting | 🟦 P2 |
| Meeting search & filter (H2, H3) | Khang | H2, H3 | Search by title; filter by status/date range | 🟦 P2 |
| Bulk export (H8) | Duy | H8 | Select multiple meetings → ZIP export | 🟦 P2 |

---

## 📊 Tổng kết phân công

| Phase | Duy (DB + API) | Thức (AI + Workers) | Khang (UI + Contract) | Tổng |
|-------|---------------|--------------------|-----------------------|------|
| 1.1 | 1.1-A (5 subtasks) | 1.1-B (4 subtasks) | 1.1-C (5 subtasks) | 14 |
| 1.2 | 1.2-A (4 subtasks) | 1.2-B (5 subtasks) | 1.2-C (5 subtasks) | 14 |
| 1.3 | 1.3-A (4 subtasks) | 1.3-B (4 subtasks) | 1.3-C (5 subtasks) | 13 |
| 2 | 2.1 + 2.2 + 2.5 | 2.3 + 2.4 + 2.6 | 2.2 + 2.3 + 2.4 + 2.5 | ~18 |
| 3 | 4 tasks | 4 tasks | 5 tasks | 13 |

---

## 🔗 Dependency Map (blocking dependencies)

```
1.1-B.1 (Fernet) ──────────────► 1.1-A.4 (Provider config APIs)
1.1-A (Schema + Auth APIs) ─────► 1.1-C (Auth UI)
1.1-A.4 + 1.1-B.4 (OpenAI) ────► 1.2-A + 1.2-B (Pipeline)
1.2-B.4 (Transcript APIs) ──────► 1.2-C.4 (Review Transcript UI)
1.3-A.1 (Analysis task) ────────► 1.3-A.2 (Prompt phải xong trước)
1.3-A.3 (Review APIs) ──────────► 1.3-C.2 (Action Items UI)
1.3-B.1 (Jira client) ──────────► 1.3-B.2 (Push task)
1.3-B.3 (Push APIs) ────────────► 1.3-C.3 (Push UI)
Phase 1 complete ───────────────► Phase 2
```

---

## 📎 Tài liệu tham chiếu

| Document | Dùng cho |
|---------|---------|
| `context_diagram.md` | Data flows User↔System↔Jira↔AI |
| `ERD_diagram.md` | Schema chi tiết, column types, constraints |
| `screenflow.md` | Screen names, navigation routes, UI states |
| `system_architecture.md` | Component topology: Electron→(Supabase SDK \| FastAPI /api/v1)→Redis→Celery→Whisper/GPT-4o→Supabase DB |
| `usecase_diagram.md` | Use case IDs (A1–H5), relationships (include/extend) |
| `MeetAstro_Phase2_Phase3_Backlog.md` | Chi tiết Phase 2 + 3 user stories, prompt templates |
| `MeetAstro_Phase1_UseCase_Specs.md` | Preconditions, main flows, entities cho từng P0 use case |