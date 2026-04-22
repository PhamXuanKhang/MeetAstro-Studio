# Frontend (Flet desktop)

Tài liệu cho UI desktop trong thư mục `frontend/` của AI Meeting Assistant.

## Mục tiêu & phạm vi

- **Mục tiêu**: cung cấp UI desktop (Windows) để record/upload audio, transcribe, phân tích (LLM), xem kết quả Epic/Task/Subtask, export, lưu DB, và đẩy Jira.
- **Kiến trúc hiện tại**: frontend gọi trực tiếp business-logic trong repo (`src.*`) qua lớp facade `frontend/core/local_backend.py` (chưa có FastAPI).
- **Ghi chú**: các chức năng Transcribe/Analyze vẫn cần env vars giống Streamlit app (ví dụ `OPENAI_API_KEY`).

## Cài đặt

Chạy tại repo root.

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r frontend\requirements.txt
pip install -e .
```

- **Vì sao cần `pip install -e .`**: để import `from src...` hoạt động ổn định khi chạy từ `frontend/`.
- **Env file**: nếu cần, tạo `.env` từ `.env.example` và điền `OPENAI_API_KEY`.

## Chạy app

```bash
python frontend\main.py
```

## Cấu trúc thư mục `frontend/`

```text
frontend/
  main.py                     # Entry point Flet app
  app.py                      # Build layout + routing theo state.route
  config.py                   # FrontendConfig (UI constants)
  core/
    state.py                  # AppState: route, transcript, analysis, cached_meetings...
    local_backend.py          # Facade gọi trực tiếp src.* (DB/record/transcribe/analyze/export/jira)
  components/
    sidebar.py                # Sidebar navigation
    topbar.py                 # Top bar: title + search + record button
  views/
    dashboard_view.py         # For you (list meeting cards, search)
    history_view.py           # History list
    new_meeting_view.py       # Upload/Record/Transcribe/Analyze/Export/Save/Jira
    results_view.py           # Render summary + epics/tasks
    settings_view.py          # Provider configs (jira + generic json)
  utils/
    helpers.py                # fmt_dt, helpers UI nhỏ
```

## Routing & state

- **Route**: `AppState.route` nhận các giá trị: `home`, `new_meeting`, `results`, `history`, `settings`.
- **Navigation**: `frontend/app.py` render UI theo `route` và truyền callbacks (`on_navigate`, `set_busy`, `toast`).
- **Search**: `AppState.search_query` được cập nhật từ topbar, và được dùng để lọc list meetings ở `dashboard_view.py` / `history_view.py`.
- **Selection**: khi mở một bản ghi (`MeetingRecord`) từ dashboard/history, app set:
  - `state.selected_meeting`
  - `state.analysis`, `state.transcript`, `state.audio_path`
  rồi chuyển route sang `results`.

## Backend facade (`LocalBackend`)

`frontend/core/local_backend.py` gom các thao tác UI cần dùng:

- **DB**: `init_db()`, `list_meetings()`, `create_meeting(...)`
- **Recording**: `start_recording()`, `stop_recording()`
- **Transcription**: `transcribe(audio_path, diarize=bool)`
- **Summary streaming**: `generate_summary_stream(transcript, on_token=...)`
- **Analysis**: `analyze(transcript)`
- **Export**: `export_markdown/json/csv(analysis)`
- **Jira**: `push_to_jira(analysis)`
- **Config parsing**: `parse_json_or_empty(raw)`
- **Save dialog**: `save_text_via_dialog(...)` (dùng Tkinter thay vì Flet FilePicker)

Thiết kế này giúp frontend **không bị phụ thuộc Streamlit** và có thể thay `LocalBackend` bằng HTTP client khi có API server.

## Luồng chính: “New meeting”

Trong `frontend/views/new_meeting_view.py`:

1. **Audio input**
   - Upload: dùng Tkinter file dialog (tránh `ft.FilePicker`).
   - Record: gọi `backend.start_recording()` / `backend.stop_recording()`.
2. **Transcribe**
   - `backend.transcribe(state.audio_path, diarize=...)` → set `state.transcript`.
3. **Analyze**
   - Streaming summary: `backend.generate_summary_stream(...)` cập nhật text-field qua callback.
   - Phân tích: `backend.analyze(state.transcript)` → set `state.analysis`.
4. **Actions**
   - Export: markdown/json/csv (Save As dialog)
   - Save DB: `backend.create_meeting(...)`
   - Push Jira: `backend.push_to_jira(...)` (có thể vào STUB mode nếu thiếu credentials)

## View “Results”

`frontend/views/results_view.py` render:

- **Summary**: `analysis.summary`
- **Epics/Tasks**: loop `analysis.epics` và `epic.tasks`, hiển thị các trường:
  - `task.summary`, `task.assignee`, `task.deadline`, `task.priority.value`, `task.context`

## View “Settings” (Integrations)

`frontend/views/settings_view.py` quản lý config theo provider:

- **jira**: form `url/email/token/project_key`
- **khác**: text-area JSON (parse bằng `LocalBackend.parse_json_or_empty`)

Config được lưu qua `backend.set_provider_config(...)` và trạng thái “đã cấu hình/chưa” đọc từ `backend.list_provider_configs()`.

## Cách thêm view/route mới

1. Tạo file view trong `frontend/views/`, ví dụ `my_view.py` với hàm `build_my_view(...) -> ft.Control`.
2. Thêm route string và mapping trong `frontend/app.py` (khối `if route == ...`).
3. (Tuỳ chọn) thêm nav item trong `frontend/components/sidebar.py`.
4. Nếu view cần gọi backend: dùng `LocalBackend` (hoặc mở rộng facade nếu cần thêm method).

## Troubleshooting (Windows/Flet)

- **“Unknown control: FilePicker” (Flet desktop)**:
  - Hiện tại project tránh `ft.FilePicker` và dùng Tkinter dialogs (`askopenfilename`, `asksaveasfilename`).
  - Nếu máy thiếu Tkinter: cài Python standard distribution đầy đủ hoặc bật Tkinter feature (tuỳ distro).
- **UI bị “đơ” khi chạy tác vụ dài**:
  - `new_meeting_view.py` chạy background thread cho record/transcribe/analyze và dùng `page.call_from_thread(...)` để update UI.
- **`ModuleNotFoundError: src`**:
  - Chạy lại `pip install -e .` từ repo root.

