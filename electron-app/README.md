# MeetAstro-Studio — Electron App

Electron + React + TypeScript frontend thay thế Flet, giữ nguyên FastAPI backend.

## Yêu cầu

- Node.js 20+
- Backend đang chạy tại `http://localhost:8000`
- Python environment của project đã cài dependencies audio (`pysysaudio`, `sounddevice`, `numpy`) nếu dùng recording

## Cài đặt

```bash
cd electron-app
npm install
```

## Chạy dev

```bash
npm run electron:dev
```

Backend dev:

```bash
uvicorn src.api.main:app --reload --port 8000
celery -A src.workers.celery_app worker -Q default --loglevel=info
```

## Build / verify

```bash
npm run typecheck
npm run build:renderer
npm run build
```

## Config

Copy `.env.example` → `.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Kiến trúc

- `electron/` — main process, preload, IPC handlers
- `electron/audio/pythonRecorder.ts` — spawn Python sidecar để tái sử dụng `src/modules/audio_recorder.py`
- `python/recorder_server.py` — JSON-lines bridge cho audio recording
- `src/api/` — axios API layer mirror `frontend/core/http_backend.py`
- `src/store/appStore.ts` — Zustand store mirror `frontend/core/state.py`
- `src/views/` — React views mirror Flet views

## Audio recording

Electron gọi Python sidecar qua IPC:

```
Renderer → preload → main.ts → pythonRecorder.ts → recorder_server.py → AudioRecorder
```

Protocol stdin/stdout JSON lines:

```json
{"action":"start","config":{"sample_rate":16000,"mic_enabled":true}}
{"action":"stop"}
```

Output giữ format WAV 16kHz mono int16 PCM như app Flet hiện tại.

## API contract

Backend không đổi. Electron app gọi cùng endpoints dưới `/api/v1`:

- meetings CRUD
- multipart audio upload
- transcript update
- analysis job
- job polling
- review HITL
- export MD/JSON/CSV
- Jira push
- provider settings
