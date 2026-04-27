# Frontend (Flet Desktop App)

Desktop UI for AI Meeting Assistant. The app is **HTTP-only** and communicates with the FastAPI backend for all operations.

---

## Overview

The Flet desktop app provides a Windows-first, cross-platform UI for:
- Recording system audio + microphone
- Uploading audio files
- Viewing transcripts
- Reviewing AI analysis
- Approving/editing action items (Human-in-the-Loop)
- Exporting to Markdown/JSON/CSV
- Pushing to Jira

**Architecture:** Thin client - no direct business logic imports from `src.*` except local audio capture.

---

## Project Structure

```
frontend/
├── main.py                     # Flet entry point
├── app.py                      # App factory + routing
├── config.py                   # UI constants, colors, styles
├── __init__.py
├── core/
│   ├── backend_factory.py      # Returns HttpBackend instance
│   ├── http_backend.py         # HTTP client (httpx) for FastAPI
│   └── state.py                # AppState dataclass
├── components/
│   ├── sidebar.py              # Navigation sidebar
│   └── topbar.py               # Top bar with title/actions
├── views/
│   ├── dashboard_view.py       # Meeting list overview
│   ├── new_meeting_view.py     # Main workflow: record/upload/transcribe/analyze
│   ├── results_view.py         # Analysis results display
│   ├── review_view.py          # Human-in-the-loop review
│   ├── history_view.py         # Past meetings list
│   └── settings_view.py        # Provider config management
└── requirements.txt            # Frontend-specific dependencies (optional)
```

---

## Core Components

### main.py

Entry point for the Flet application.

```python
import flet as ft
from frontend.app import create_app

def main(page: ft.Page):
    app = create_app(page)
    # Initialize and run

if __name__ == "__main__":
    ft.app(target=main)
```

Run: `python frontend/main.py`

### app.py

App factory with routing setup.

```python
def create_app(page: ft.Page) -> App:
    """
    Create Flet app với routing.
    
    Routes:
        / -> dashboard_view
        /new -> new_meeting_view
        /results/{id} -> results_view
        /review/{id} -> review_view
        /history -> history_view
        /settings -> settings_view
    """
```

### config.py

UI constants and configuration.

```python
@dataclass(frozen=True)
class FrontendConfig:
    app_version: str = "0.1.0"
    sidebar_width: int = 260
    content_max_width: int = 1100
```

---

## State Management

### AppState (`core/state.py`)

Centralized state for the application.

```python
@dataclass
class AppState:
    route: str = "home"
    audio_path: Optional[str] = None
    transcript: str = ""
    analysis: Optional[MeetingAnalysis] = None
    selected_meeting: Optional[MeetingRecord] = None
    progress_text: str = ""
    busy: bool = False
    search_query: str = ""
    cached_meetings: list[MeetingRecord] = field(default_factory=list)
    review_items: list[ReviewItem] = field(default_factory=list)
    meeting_status: str = ""
    current_meeting_id: Optional[str] = None
```

State updates trigger UI refresh via `page.update()`.

---

## HTTP Backend

### HttpBackend (`core/http_backend.py`)

HTTP client singleton for all API communication.

```python
class HttpBackend:
    def __init__(self, base_url: str = API_BASE_URL):
        self.client = httpx.Client(base_url=base_url, timeout=60.0)
    
    # Meetings
    def create_meeting(self, title: str) -> dict: ...
    def get_meeting(self, meeting_id: str) -> dict: ...
    def list_meetings(self) -> list[dict]: ...
    
    # Audio
    def upload_audio(self, meeting_id: str, file_path: str, 
                     diarize: bool = False, language: str = "vi") -> dict: ...
    
    # Transcript
    def get_transcript(self, meeting_id: str) -> dict: ...
    def update_transcript(self, meeting_id: str, text: str) -> dict: ...
    
    # Analysis
    def trigger_analysis(self, meeting_id: str) -> dict: ...
    def get_analysis(self, meeting_id: str) -> dict: ...
    
    # Review
    def list_review_items(self, meeting_id: str) -> list[dict]: ...
    def update_review_item(self, meeting_id: str, item_id: str, **fields) -> dict: ...
    def approve_item(self, meeting_id: str, item_id: str) -> dict: ...
    def reject_item(self, meeting_id: str, item_id: str) -> dict: ...
    def approve_all(self, meeting_id: str) -> dict: ...
    
    # Jira
    def push_to_jira(self, meeting_id: str) -> dict: ...
    
    # Export
    def export_markdown(self, meeting_id: str) -> str: ...
    def export_json(self, meeting_id: str) -> str: ...
    def export_csv(self, meeting_id: str) -> str: ...
    
    # Jobs
    def get_job_status(self, job_id: str) -> dict: ...
```

---

## Views

### dashboard_view.py

Overview of recent meetings.

Features:
- List of recent meetings with status
- Quick actions (open, delete)
- Button to create new meeting

### new_meeting_view.py

Main workflow view with multiple stages:

```
┌─────────────────────────────────────────────────────────────┐
│                    New Meeting View                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. AUDIO INPUT                                              │
│     [Record System Audio]  [Upload File]                     │
│     Status: Recording... 00:45 / Uploaded: meeting.wav       │
│                                                              │
│  2. TRANSCRIPTION                                            │
│     [Transcribe]  [x] Enable Diarization                     │
│     ┌────────────────────────────────────────┐              │
│     │ Transcript text area (editable)        │              │
│     │ ...                                    │              │
│     └────────────────────────────────────────┘              │
│                                                              │
│  3. ANALYSIS                                                 │
│     [Analyze Transcript]                                     │
│     Status: Analyzing...                                     │
│                                                              │
│  4. RESULTS                                                  │
│     Epic 1: ...                                              │
│       Task 1.1: ...                                          │
│                                                              │
│  5. ACTIONS                                                  │
│     [Review Items] [Export MD] [Export JSON] [Push to Jira]  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

Key features:
- Audio recording via `AudioRecorder` (local)
- File upload via Tkinter dialog
- Polling for task completion
- Editable transcript text area
- Progress indicators

### results_view.py

Display analysis results in structured format.

Features:
- Hierarchical display: Epic > Task > Subtask
- Color-coded priorities
- Expandable sections
- Export buttons

### review_view.py

Human-in-the-Loop review interface.

```
┌─────────────────────────────────────────────────────────────┐
│                    Review Items                              │
├─────────────────────────────────────────────────────────────┤
│  [Approve All Draft]                                        │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ [TASK] Implement API endpoint                          │ │
│  │ Assignee: John  |  Deadline: 2026-04-30  |  High       │ │
│  │ Confidence: 0.85 ████████░░                            │ │
│  │ Context: "John said he will implement the endpoint..." │ │
│  │                                                         │ │
│  │ [Edit] [Approve] [Reject]                    [draft]   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ [TASK] Review documentation        ⚠️ FLAGGED          │ │
│  │ Assignee: TBD  |  Deadline: N/A  |  Medium             │ │
│  │ Confidence: 0.35 ███░░░░░░░                            │ │
│  │ ...                                                     │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

Features:
- List all review items
- Edit inline (summary, assignee, deadline, priority)
- Approve/reject individual items
- Bulk approve all draft items
- Visual indicators for flagged items
- Confidence score visualization

### history_view.py

Past meetings list.

Features:
- Chronological list
- Filter by status
- Open meeting details
- Delete meetings

### settings_view.py

Provider configuration management.

Features:
- Configure Jira credentials
- Configure other provider settings
- Test connection button
- Encrypted storage (via credential_vault)

---

## Components

### sidebar.py

Navigation sidebar component.

```python
def sidebar(page: ft.Page, state: AppState) -> ft.Container:
    """
    Sidebar with navigation links.
    
    Links:
        - Dashboard (/)
        - New Meeting (/new)
        - History (/history)
        - Settings (/settings)
        
    Shows:
        - API connection status
        - Current user
    """
```

### topbar.py

Top bar with title and actions.

```python
def topbar(page: ft.Page, title: str, actions: list[ft.Control] = None) -> ft.Container:
    """
    Top bar with page title and action buttons.
    """
```

---

## Audio Recording

Audio recording uses the local `AudioRecorder` module (not via API).

```python
from src.modules.audio_recorder import AudioRecorder
from src.services.recording_service import start_recording, stop_recording

# In new_meeting_view.py
def on_record_click(e):
    if state.is_recording:
        audio_path = stop_recording()
        state.audio_path = audio_path
        state.is_recording = False
    else:
        output_path = start_recording()
        state.is_recording = True
        # Start elapsed time update thread
```

Features:
- System audio capture (pysysaudio)
- Microphone mixing (sounddevice)
- Chunk rotation every N seconds
- Background thread recording

---

## Job Polling

Long-running operations (transcribe, analyze, Jira push) use Celery jobs. The frontend polls for completion via `GET /api/v1/jobs/{job_id}`.

```python
async def poll_job(job_id: str, interval: float = 1.0):
    """
    Poll job state until completion.
    
    States:
        PENDING -> still queued
        STARTED -> in progress
        SUCCESS -> done, get result
        FAILURE -> error occurred
        RETRY -> retrying
    """
    while True:
        status = backend.get_job_status(job_id)
        if status["state"] == "SUCCESS":
            return status["result"]
        elif status["state"] == "FAILURE":
            raise Exception(status.get("error", "Job failed"))
        await asyncio.sleep(interval)
```

UI shows progress indicator during polling.

---

## File Dialogs

File dialogs use Tkinter (not Flet FilePicker) for better Windows compatibility.

```python
from tkinter import filedialog, Tk

def open_file_dialog() -> str:
    """Open file dialog and return selected path."""
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        filetypes=[
            ("Audio files", "*.wav *.mp3 *.m4a"),
            ("All files", "*.*")
        ]
    )
    root.destroy()
    return file_path

def save_file_dialog(default_ext: str = ".md") -> str:
    """Save file dialog and return selected path."""
    root = Tk()
    root.withdraw()
    file_path = filedialog.asksaveasfilename(
        defaultextension=default_ext,
        filetypes=[
            ("Markdown", "*.md"),
            ("JSON", "*.json"),
            ("CSV", "*.csv")
        ]
    )
    root.destroy()
    return file_path
```

---

## Threading

UI-blocking operations run in background threads to keep the UI responsive.

```python
import threading

def run_in_background(func, callback):
    """Run function in background thread, call callback on completion."""
    def wrapper():
        try:
            result = func()
            page.call_from_thread(callback, result, None)
        except Exception as e:
            page.call_from_thread(callback, None, e)
    
    thread = threading.Thread(target=wrapper)
    thread.start()
```

Usage:
```python
def on_transcribe_click(e):
    show_progress("Transcribing...")
    run_in_background(
        lambda: backend.upload_audio(meeting_id, audio_path),
        on_transcribe_complete
    )

def on_transcribe_complete(result, error):
    hide_progress()
    if error:
        show_error(str(error))
    else:
        state.transcript = result["transcript"]
        page.update()
```

---

## Troubleshooting

### "Unknown control: FilePicker" (Flet desktop)

The project uses Tkinter dialogs instead of `ft.FilePicker`. If Tkinter is missing, install Python standard distribution or enable Tkinter feature.

### UI freezes during long operations

All long operations should use background threads with `page.call_from_thread()` for UI updates.

### `ModuleNotFoundError: src`

Run `pip install -e .` from repo root to install the package in editable mode.

### Connection refused to API

- Check if backend is running (`docker compose up`)
- Verify `API_BASE_URL` in `.env` matches the server address

---

## Building Executable

Build standalone `.exe` using [flet pack](https://flet.dev/docs/publish):

```bash
# Install frontend dependencies
uv pip install -e ".[frontend]"

# Build executable
flet pack frontend/main.py --name "AI Meeting Assistant"
```

The executable will be in `dist/` directory.

Configure `API_BASE_URL` to point to production server before distribution.
