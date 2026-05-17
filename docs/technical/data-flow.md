# Data Flow

Luồng dữ liệu end-to-end từ audio input đến output cuối cùng trong runtime hiện tại.

---

## Pipeline tổng quan

```text
Electron app
  -> record/upload audio or video
  -> FastAPI /api/v1 upload/job endpoints
  -> Redis queue
  -> Celery worker
      -> transcribe via WhisperLiveKit or OpenAI Whisper fallback
      -> save transcript segments to Supabase
      -> analyze via GPT-4o structured output
      -> save analysis/action items to Supabase
  -> Electron reviews transcript/action items
  -> approved items are pushed to Jira through FastAPI/Celery
```

---

## Data Transformations

| Stage | Input | Transform | Output |
|-------|-------|-----------|--------|
| Record | User action in Electron | Electron IPC / Python sidecar captures local audio | local WAV file path |
| Upload | Audio/video file selected in Electron | Multipart upload to FastAPI; backend validates and normalizes audio | normalized audio for worker |
| Transcribe batch | normalized audio | WhisperLiveKit when configured, otherwise OpenAI Whisper/OpenAI diarization fallback | `transcript_segments` rows in Supabase |
| Transcribe stream | audio stream/session | WhisperLiveKit WebSocket/SSE path | realtime transcript segments to Electron |
| User edit | transcript segment text/speaker | FastAPI/Supabase update path | corrected transcript data |
| Analyze | ordered transcript text | GPT-4o JSON mode parsed into `MeetingAnalysis` | `analysis_results` + `action_items` in Supabase |
| Validate | AI items + transcript/context | validation/confidence services | confidence scores and review flags |
| Review | Epic/Task/Subtask action-item tree | Electron user approves, edits, rejects, or adds manual items | selected approved items |
| Push Jira | approved action items | Celery Jira push task creates Epic → Task → Subtask | Jira issue keys/URLs saved to Supabase |

---

## Runtime Boundaries

- Electron uses Supabase JS SDK for auth and user-owned data views.
- Backend uses `SUPABASE_SERVICE_ROLE_KEY` through `src.db.supabase_client` and CRUD helpers.
- Redis/Celery handles long-running transcription, analysis, streaming finalization, cleanup, and Jira push jobs.
- Database runtime is Supabase; there is no local PostgreSQL/Alembic path in the active submit workflow.

---

## Status Flow

```text
pending
  -> transcribing
  -> transcribed
  -> analyzing
  -> draft
  -> approved
  -> pushed
```

`failed` can be reached from worker/API failures and should surface through job polling or item sync status.
