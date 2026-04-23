# Frontend (Flet desktop)

Desktop UI for the AI Meeting Assistant. The app is **HTTP-only** and uses the FastAPI backend for all data operations.

## Goals

- Provide a Windows-first, cross-platform desktop UI for recording/uploading audio, transcription, analysis, export, review, and Jira push.
- Keep the client thin: no direct business logic imports from `src.*` except local system audio capture.

## Key files

```text
frontend/
  main.py                     # Flet entry point
  app.py                      # Layout + routing
  config.py                   # UI constants
  core/
    backend_factory.py        # Always returns HttpBackend
    http_backend.py           # HTTP client for FastAPI
    state.py                  # AppState
  components/
    sidebar.py
    topbar.py
  views/
    dashboard_view.py         # Overview list
    history_view.py           # History list
    new_meeting_view.py       # Upload/record/transcribe/analyze/export/Jira
    results_view.py           # Render analysis results
    review_view.py            # Human review flow
    settings_view.py          # Provider configs (Jira + generic JSON)
```

## Main flow (New meeting)

1. **Audio input**: Upload or record system audio.
2. **Transcribe**: Upload audio to the backend and wait for transcript.
3. **Analyze**: Update transcript (if edited) and run analysis.
4. **Actions**: Export, review, and push to Jira.

## Notes

- The app expects the API server and worker to be running.
- `API_BASE_URL` is read from `.env` and displayed in the sidebar.

## Troubleshooting (Windows/Flet)

- **“Unknown control: FilePicker” (Flet desktop)**:
  - Hiện tại project tránh `ft.FilePicker` và dùng Tkinter dialogs (`askopenfilename`, `asksaveasfilename`).
  - Nếu máy thiếu Tkinter: cài Python standard distribution đầy đủ hoặc bật Tkinter feature (tuỳ distro).
- **UI bị “đơ” khi chạy tác vụ dài**:
  - `new_meeting_view.py` chạy background thread cho record/transcribe/analyze và dùng `page.call_from_thread(...)` để update UI.
- **`ModuleNotFoundError: src`**:
  - Chạy lại `pip install -e .` từ repo root.

