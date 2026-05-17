# Audio Processing Workflow

Luồng xử lý âm thanh trong hệ thống, từ audio upload/record cho tới transcript lưu trong Supabase.

---

## 1. Kiến trúc hiện hành

Audio được xử lý bất đồng bộ qua FastAPI + Celery:

```text
Electron desktop
  -> POST /api/v1/meetings/{id}/audio
  -> Celery run_pipeline
  -> transcribe_audio
  -> OpenAI or WhisperLiveKit transcription provider
  -> transcript_segments rows in Supabase
```

### Input

- Upload file `.wav`, `.mp3`, `.m4a` từ Electron desktop app.
- Hoặc record local bằng `recording_service.py` / `audio_recorder.py`, sau đó upload file đã ghi.

### STT providers

- `OpenAITranscriber`: plain OpenAI Whisper API transcription.
- `OpenAIDiarizeTranscriber`: OpenAI diarization transcription với speaker labels.

Không dùng Local Whisper trong dự án này. Nếu plain OpenAI transcription fail, task fail và Celery retry/error handling xử lý theo cấu hình task.

### Diarization fallback

Khi `diarize=true`, `transcription_service.transcribe_diarized()` thử `OpenAIDiarizeTranscriber` trước. Nếu diarization lỗi hoặc trả text rỗng, service fallback sang `OpenAITranscriber` để pipeline vẫn có transcript plain text.

```text
diarize=true
  -> OpenAIDiarizeTranscriber
  -> success: "[Speaker 0]: ..."
  -> failure/empty: OpenAITranscriber plain transcript
```

### Output

Transcript được lưu vào bảng Supabase `transcript_segments`:

- `text`: transcript segment dùng cho analysis.
- `speaker`: speaker label nếu có.
- `start_time` / `end_time`: timestamp segment nếu provider trả về.
- `confidence`: confidence score nếu provider trả về.

---

## 2. Hướng mở rộng

Nếu cần speaker attribution chính xác hơn, có thể tách pipeline thành hai nhánh:

1. Transcription: lấy text/timestamps.
2. Diarization: xác định speaker segments.
3. Alignment: gộp word-level timestamps với speaker labels.
4. LLM intake: đưa structured speaker transcript vào analysis.

Việc thêm diarization engine riêng cần cân nhắc deploy resource, latency, privacy và chi phí vận hành. Nếu triển khai provider mới, provider đó phải kế thừa `BaseTranscriber` và có test riêng.
