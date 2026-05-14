# Hybrid Contract v1 - Phase 1.1

Status: Draft
Scope: Phase 1.1 P0 use cases — target architecture only (không phải migration guide)
Target Frontend: Electron (Flet là tạm thời, sẽ xóa sau khi Electron build xong)
Architecture: Electron dùng Supabase SDK trực tiếp cho Auth/basic data; FastAPI cho heavy/server-only actions.
Storage Convention: storage_provider="local" nghĩa là audio file lưu trên máy người dùng (không phải VPS). audio_storage_path là file:// URI trỏ tới path gốc trên client. VPS chỉ giữ temp copy trong lúc xử lý Whisper.

## Routing Rules

Supabase SDK:
- Auth/session.
- Read/list user-owned data.
- Lightweight user edits protected by RLS.
- Realtime subscriptions.

FastAPI (VPS) — base path: /api/v1:
- Upload audio/video và trigger AI jobs.
- Provider secrets encryption/decryption.
- Jira integration.
- Any operation needing service role, Fernet key, Celery, OpenAI, or external APIs.

## Shared Shapes

Meeting:
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "title": "Sprint Planning",
  "status": "pending",
  "storage_provider": "local",
  "audio_storage_path": "file:///Users/name/recordings/sprint.wav",
  "audio_duration_seconds": 1830,
  "error_message": null,
  "created_at": "2026-05-05T10:00:00Z",
  "updated_at": "2026-05-05T10:00:00Z"
}
```

Status enum: `pending` -> `transcribing` -> `transcribed` -> `analyzing` -> `draft` -> `approved` -> `pushed` | `partial_success` | `failed`

Transcript segment:
```json
{
  "id": "uuid",
  "meeting_id": "uuid",
  "speaker": "Speaker A",
  "start_time": 0.0,
  "end_time": 8.4,
  "content": "Transcript text."
}
```

Analysis result:
```json
{
  "id": "uuid",
  "meeting_id": "uuid",
  "summary_text": "Short summary.",
  "key_decisions": ["Decision 1"],
  "parking_lot": ["Question 1"],
  "raw_response": {},
  "ai_model": "gpt-4o",
  "input_tokens": 1200,
  "output_tokens": 700,
  "created_at": "2026-05-05T10:00:00Z"
}
```

Action item:
```json
{
  "id": "uuid",
  "meeting_id": "uuid",
  "parent_id": null,
  "item_type": "task",
  "title": "Finalize checklist",
  "description": "Complete launch checklist.",
  "assignee": "Minh",
  "deadline": "2026-05-10",
  "priority": "high",
  "context": "Transcript excerpt.",
  "confidence_score": 0.84,
  "review_status": "draft",
  "is_selected": false,
  "sync_status": "pending",
  "sync_error": null,
  "jira_issue_key": null,
  "jira_issue_url": null,
  "created_at": "2026-05-05T10:00:00Z",
  "updated_at": "2026-05-05T10:00:00Z"
}
```

## A1 - Register With Email/Password

Routing: Supabase SDK.

Request:
```json
{
  "email": "user@example.com",
  "password": "securepass123",
  "options": {
    "data": {
      "full_name": "Nguyen Van A"
    }
  }
}
```

Response:
```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com"
  },
  "session": null
}
```

## A2 - Register/Login With Google OAuth

Routing: Supabase SDK.

Request:
```json
{
  "provider": "google",
  "redirect_to": "meetastro://auth/callback"
}
```

Response:
```json
{
  "url": "https://supabase-project.supabase.co/auth/v1/authorize?provider=google"
}
```

## A3 - Verify Email

Routing: Supabase SDK.

Request:
```json
{
  "type": "email_verification_link"
}
```

Response:
```json
{
  "session": {
    "access_token": "jwt",
    "refresh_token": "jwt",
    "user": {
      "id": "uuid",
      "email": "user@example.com"
    }
  }
}
```

## A4 - Login With Email/Password

Routing: Supabase SDK.

Request:
```json
{
  "email": "user@example.com",
  "password": "securepass123"
}
```

Response:
```json
{
  "session": {
    "access_token": "jwt",
    "refresh_token": "jwt",
    "user": {
      "id": "uuid",
      "email": "user@example.com"
    }
  }
}
```

## A5 - Login With Google OAuth

Routing: Supabase SDK.

Request:
```json
{
  "provider": "google",
  "redirect_to": "meetastro://auth/callback"
}
```

Response:
```json
{
  "url": "https://supabase-project.supabase.co/auth/v1/authorize?provider=google"
}
```

## A6 - Forgot Password

Routing: Supabase SDK.

Request:
```json
{
  "email": "user@example.com",
  "redirect_to": "meetastro://auth/reset-password"
}
```

Response:
```json
{
  "message": "If this email is registered, a reset link has been sent."
}
```

## A8 - Logout

Routing: Supabase SDK.

Request:
```json
{}
```

Response:
```json
{
  "session": null
}
```

## B1 - Save Provider Credentials

Routing: FastAPI (VPS). `POST /api/v1/settings/providers/{provider_name}`

Current implementation uses a generic provider endpoint for Jira, OpenAI, and future providers. UI must not write plaintext keys directly to Supabase.

Backend storage:
- Supabase table: `provider_configs`
- Columns used by backend: `user_id`, `provider_name`, `api_key`, `config_data`
- `api_key` is Fernet-encrypted before insert/update.
- `config_data` stores non-secret provider metadata.
- Saving an existing `{user_id, provider_name}` updates the existing provider row.

Supported request shape used by current UI:
```json
{
  "user_id": "uuid",
  "config": {
    "token": "jira-api-token",
    "url": "https://company.atlassian.net",
    "email": "user@example.com",
    "projectKey": "DEV"
  }
}
```

Also accepted by backend for contract-friendly callers:
```json
{
  "user_id": "uuid",
  "api_key": "provider-api-key",
  "config_data": {
    "site_url": "https://company.atlassian.net",
    "email": "user@example.com",
    "project_key": "DEV"
  }
}
```

Response:
```json
{
  "provider_name": "jira",
  "is_configured": true,
  "masked_key": "...abcd"
}
```

Notes:
- `is_configured=true` means an encrypted provider row exists in Supabase.
- It does not mean the key has been validated against Jira/OpenAI.
- `masked_key` may be `null` when no key exists or when the key cannot be decrypted for preview. The plaintext key is never returned.

## B2 - View Provider Config Status

Routing: FastAPI (VPS). `GET /api/v1/settings/providers/{provider_name}?user_id={uuid}`

Response when configured:
```json
{
  "provider_name": "jira",
  "is_configured": true,
  "masked_key": "...abcd"
}
```

Response when not configured:
```json
{
  "provider_name": "jira",
  "is_configured": false,
  "masked_key": null
}
```

## B3 - Delete Provider Config

Routing: FastAPI (VPS). `DELETE /api/v1/settings/providers/{provider_name}?user_id={uuid}`

Response:
```json
{
  "message": "Provider 'jira' deleted."
}
```

## B4 - Test Provider Connection

Routing: Future / not implemented in current backend.

Current UI should treat provider status as "saved" rather than "validated". A future endpoint can be added per provider:
- Jira: `POST /api/v1/settings/providers/jira/test`
- OpenAI: `POST /api/v1/settings/providers/openai/test`

Expected future response shape:
```json
{
  "success": true,
  "provider_name": "jira",
  "display_name": "Nguyen Van A",
  "error": null
}
```

## C1 - Create Meeting

Routing: Supabase SDK.

Request:
```json
{
  "title": "Sprint Planning",
  "status": "pending",
  "storage_provider": "local",
  "audio_storage_path": null,
  "audio_duration_seconds": null
}
```

Response:
```json
{
  "meeting": {
    "id": "uuid",
    "user_id": "uuid",
    "title": "Sprint Planning",
    "status": "pending",
    "storage_provider": "local",
    "audio_storage_path": null,
    "audio_duration_seconds": null
  }
}
```

## C2/C3 - Upload Audio or Video

Routing: FastAPI (VPS). `POST /api/v1/meetings/{meeting_id}/upload`

Chấp nhận audio (mp3/wav/m4a/ogg) và video (mp4/mkv/webm). Backend infer loại file từ MIME type và tự extract audio nếu là video.

Request (multipart/form-data):
```json
{
  "file": "multipart-binary",
  "language": "vi",
  "diarize": true
}
```

- `language`: optional, default `"vi"`
- `diarize`: optional, default `true`

Response:
```json
{
  "meeting_id": "uuid",
  "job_id": "celery-task-id",
  "status": "queued"
}
```

## C4 - Start Live Recording

Routing: Future / research. Not part of Phase 1.1 contract.

Request:
```json
{}
```

Response:
```json
{
  "status": "deferred"
}
```

## C7 - Stop Recording

Routing: Future / research. Not part of Phase 1.1 contract.

Request:
```json
{}
```

Response:
```json
{
  "status": "deferred"
}
```

## C9 - View Pipeline Status

Routing: Supabase Realtime for meeting status. FastAPI job endpoint is temporary fallback.

Request:
```json
{
  "meeting_id": "uuid"
}
```

Response:
```json
{
  "meeting": {
    "id": "uuid",
    "status": "transcribed",
    "error_message": null,
    "updated_at": "2026-05-05T10:30:00Z"
  }
}
```

## C10 - Stream Transcription (WhisperLiveKit SSE)

Routing: FastAPI (VPS). `GET /api/v1/meetings/{meeting_id}/transcribe/stream`

Real-time transcription streaming qua Server-Sent Events (SSE). Backend kết nối tới WhisperLiveKit WebSocket server (LightningAI), nhận partial transcripts và forward tới frontend qua SSE.

### Flow

```
Local Audio → ffmpeg decode → PCM chunks → WebSocket → WhisperLiveKit Server
                                                              ↓
Frontend (SSE) ← Backend (SSE endpoint) ← on_partial callback ← partial transcript
```

### Endpoint

```
GET /api/v1/meetings/{meeting_id}/transcribe/stream
```

Query parameters:
- `ws_url` (optional): Custom WhisperLiveKit WebSocket URL. Default: `WHLK_WEBSOCKET_URL` env var.

### SSE Response Format

```text
event: partial
data: {
  "segments": [
    {
      "speaker": "Speaker 1",
      "start": 0.0,
      "end": 8.4,
      "text": "Hello everyone..."
    }
  ],
  "done": false
}
```

```text
event: done
data: {
  "segments": [
    {
      "speaker": "Speaker 1",
      "start": 0.0,
      "end": 8.4,
      "text": "Hello everyone, thank you for joining..."
    }
  ],
  "done": true,
  "full_transcript": "..."
}
```

```text
event: error
data: {
  "error": "WebSocket connection failed",
  "code": "WLK_CONNECTION_ERROR"
}
```

### SSE Events

| Event | Description |
|-------|-------------|
| `partial` | Partial transcript segments as they arrive |
| `done` | Transcription complete, full transcript included |
| `error` | Error occurred during streaming |

### Request Headers

```
Accept: text/event-stream
```

### Response Headers

```
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

### Frontend Integration

```javascript
const eventSource = new EventSource(`/api/v1/meetings/${meetingId}/transcribe/stream`);

eventSource.addEventListener('partial', (e) => {
  const data = JSON.parse(e.data);
  // Append segments to UI
  data.segments.forEach(seg => appendTranscript(seg));
});

eventSource.addEventListener('done', (e) => {
  const data = JSON.parse(e.data);
  // Transcription complete
  console.log('Full transcript:', data.full_transcript);
});

eventSource.addEventListener('error', (e) => {
  const data = JSON.parse(e.data);
  // Handle error
  showError(data.error);
});

// Cleanup when done
eventSource.addEventListener('done', () => eventSource.close());
```

### Error Codes

| Code | Description |
|------|-------------|
| `WLK_CONNECTION_ERROR` | Cannot connect to WhisperLiveKit WebSocket server |
| `WLK_TRANSCRIPTION_ERROR` | Error during transcription |
| `MEETING_NOT_FOUND` | Meeting ID not found |
| `AUDIO_FILE_MISSING` | Audio file not found for meeting |

### Rate / Limits

- SSE connection: max 1 concurrent per meeting
- Frontend should close connection after `done` event

## D1 - View Realtime Transcript

Routing: Supabase Realtime on `transcript_segments`.

Request:
```json
{
  "meeting_id": "uuid"
}
```

Response:
```json
{
  "event": "INSERT",
  "segment": {
    "id": "uuid",
    "meeting_id": "uuid",
    "speaker": "Speaker A",
    "start_time": 0.0,
    "end_time": 8.4,
    "content": "Transcript text."
  }
}
```

## D2 - View Final Transcript

Routing: Supabase SDK.

Request:
```json
{
  "meeting_id": "uuid"
}
```

Response:
```json
{
  "segments": [
    {
      "id": "uuid",
      "speaker": "Speaker A",
      "start_time": 0.0,
      "end_time": 8.4,
      "content": "Transcript text."
    }
  ]
}
```

## D3 - View Diarization

Routing: Supabase SDK.

Request:
```json
{
  "meeting_id": "uuid"
}
```

Response:
```json
{
  "segments": [
    {
      "speaker": "Speaker A",
      "start_time": 0.0,
      "end_time": 8.4,
      "content": "Transcript text."
    }
  ]
}
```

## D4 - Rename Speaker

Routing: Supabase SDK.

Request:
```json
{
  "meeting_id": "uuid",
  "from_speaker": "Speaker A",
  "to_speaker": "Minh"
}
```

Response:
```json
{
  "updated_count": 12
}
```

## D5 - Edit Transcript Text

Routing: Supabase SDK.

Request:
```json
{
  "segment_id": "uuid",
  "content": "Corrected transcript text."
}
```

Response:
```json
{
  "segment": {
    "id": "uuid",
    "content": "Corrected transcript text."
  }
}
```

## E1 - Trigger Analysis

Routing: FastAPI (VPS). `POST /api/v1/meetings/{meeting_id}/analyze`

Request:
```json
{
  "meeting_id": "uuid"
}
```

Response:
```json
{
  "meeting_id": "uuid",
  "job_id": "celery-task-id",
  "status": "queued"
}
```

## E2 - View Meeting Summary

Routing: Supabase SDK.

Request:
```json
{
  "meeting_id": "uuid"
}
```

Response:
```json
{
  "analysis_result": {
    "summary_text": "Short summary."
  }
}
```

## E3 - View Analysis Result

Routing: Supabase SDK.

Request:
```json
{
  "meeting_id": "uuid"
}
```

Response:
```json
{
  "analysis_result": {
    "summary_text": "Short summary.",
    "key_decisions": ["Decision 1"],
    "parking_lot": ["Question 1"],
    "raw_response": {}
  },
  "action_items": []
}
```

## E6 - View Confidence Score

Routing: Supabase SDK.

Request:
```json
{
  "meeting_id": "uuid"
}
```

Response:
```json
{
  "action_items": [
    {
      "id": "uuid",
      "title": "Finalize checklist",
      "confidence_score": 0.84
    }
  ]
}
```

## F1 - Edit Epic/Task/Subtask

Routing: Supabase SDK.

Request:
```json
{
  "action_item_id": "uuid",
  "title": "Updated title",
  "description": "Updated description",
  "assignee": "Minh",
  "deadline": "2026-05-10",
  "priority": "high",
  "review_status": "edited"
}
```

Response:
```json
{
  "action_item": {
    "id": "uuid",
    "review_status": "edited"
  }
}
```

## F5 - Approve Action Item

Routing: Supabase SDK.

Request:
```json
{
  "action_item_id": "uuid",
  "review_status": "approved",
  "is_selected": true
}
```

Response:
```json
{
  "action_item": {
    "id": "uuid",
    "review_status": "approved",
    "is_selected": true
  }
}
```

## F6 - Reject Action Item

Routing: Supabase SDK.

Request:
```json
{
  "action_item_id": "uuid",
  "review_status": "rejected",
  "is_selected": false
}
```

Response:
```json
{
  "action_item": {
    "id": "uuid",
    "review_status": "rejected",
    "is_selected": false
  }
}
```

## F8 - Add Manual Action Item

Routing: Supabase SDK.

Request:
```json
{
  "meeting_id": "uuid",
  "parent_id": null,
  "item_type": "task",
  "title": "Manual task",
  "description": "Added by user.",
  "assignee": null,
  "deadline": null,
  "priority": "medium",
  "context": "Manual item",
  "confidence_score": 1.0,
  "review_status": "edited",
  "is_selected": false,
  "sync_status": "pending"
}
```

Response:
```json
{
  "action_item": {
    "id": "uuid",
    "title": "Manual task"
  }
}
```

## G1 - Push Selected Items To Jira

Routing: FastAPI (VPS). `POST /api/v1/meetings/{meeting_id}/jira/push`

Current implementation queues a Celery job and pushes only approved action items that are not already synced.

Preconditions:
- Jira provider config must exist for the meeting owner. Missing or incomplete config returns `400`.
- Main path does not use Jira stub mode.
- All reviewable items must be finalized before push. If any item is still pending review, the endpoint returns `409`.
- At least one approved unsynced item must exist. Items with `sync_status="synced"` are skipped to avoid duplicate Jira issues.

Push behavior:
- Jira hierarchy is preserved: Epic -> Task -> Subtask.
- Processing is best-effort per item. A failed item does not roll back successful items.
- Each item is updated in Supabase as it moves through `syncing`, `synced`, or `failed`.
- Successful items store `jira_issue_key` and `jira_issue_url`.
- Failed items store `sync_error`.
- Final meeting status is `pushed`, `partial_success`, or `failed`.

Phase 1: does not set Jira assignee field. Assignee is written into issue description/context only.

Request:
```json
{
  "meeting_id": "uuid"
}
```

Response:
```json
{
  "meeting_id": "uuid",
  "job_id": "celery-task-id",
  "status": "queued",
  "is_stub": false,
  "epic_keys": [],
  "task_count": 0,
  "subtask_count": 0,
  "message": "Jira push job queued"
}
```

Job result shape from `GET /api/v1/jobs/{job_id}`:
```json
{
  "meeting_id": "uuid",
  "epic_keys": ["DEV-123"],
  "task_count": 3,
  "subtask_count": 2,
  "synced_count": 6,
  "failed_count": 1,
  "skipped_synced_count": 4,
  "is_stub": false
}
```

## G2 - View Push Status

Routing: Supabase Realtime on `action_items`, with Supabase SDK fallback/refetch.

Request:
```json
{
  "meeting_id": "uuid"
}
```

Response:
```json
{
  "action_items": [
    {
      "id": "uuid",
      "sync_status": "synced",
      "sync_error": null,
      "jira_issue_key": "DEV-123",
      "jira_issue_url": "https://company.atlassian.net/browse/DEV-123"
    }
  ]
}
```

## G3 - Retry Failed Push

Routing: FastAPI (VPS). Reuse `POST /api/v1/meetings/{meeting_id}/jira/push`.

There is no separate retry endpoint in the current implementation. Re-push uses the same endpoint and skips every item already marked `sync_status="synced"`. Approved items with `sync_status="failed"` or `sync_status="pending"` can be attempted again after the underlying cause is fixed.

Request:
```json
{
  "meeting_id": "uuid"
}
```

Response:
```json
{
  "meeting_id": "uuid",
  "job_id": "celery-task-id",
  "status": "queued",
  "is_stub": false,
  "message": "Jira push job queued"
}
```

## G4 - View Jira Issue Links

Routing: Supabase SDK.

Request:
```json
{
  "meeting_id": "uuid"
}
```

Response:
```json
{
  "items": [
    {
      "id": "uuid",
      "jira_issue_key": "DEV-123",
      "jira_issue_url": "https://company.atlassian.net/browse/DEV-123"
    }
  ]
}
```

## H1 - View Meetings History

Routing: Supabase SDK.

Request:
```json
{
  "limit": 20,
  "offset": 0
}
```

Response:
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Sprint Planning",
      "status": "draft",
      "audio_duration_seconds": 1830,
      "created_at": "2026-05-05T10:00:00Z",
      "updated_at": "2026-05-05T10:30:00Z"
    }
  ],
  "total": 1
}
```

## H4 - View Old Meeting Detail

Routing: Supabase SDK.

Request:
```json
{
  "meeting_id": "uuid"
}
```

Response:
```json
{
  "meeting": {},
  "analysis_result": {},
  "transcript_segments": [],
  "action_items": []
}
```

## H5 - Delete Meeting

Routing: Supabase SDK.

Request:
```json
{
  "meeting_id": "uuid"
}
```

Response:
```json
{
  "deleted": true
}
```

