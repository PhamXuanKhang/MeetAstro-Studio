# Audio Processing Workflow

Luồng xử lý âm thanh trong hệ thống, từ audio upload/record cho tới transcript lưu trong PostgreSQL.

---

## 1. Kiến trúc hiện hành

Audio được xử lý bất đồng bộ qua FastAPI + Celery:

```text
Flet desktop
  -> POST /api/v1/meetings/{id}/audio
  -> Celery run_pipeline
  -> transcribe_audio
  -> OpenAI transcription provider
  -> Transcript row in PostgreSQL
```

### Input

- Upload file `.wav`, `.mp3`, `.m4a` từ Flet desktop app.
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

Transcript được lưu vào bảng `transcripts`:

- `raw_text`: transcript dùng cho analysis.
- `diarized_text`: transcript có speaker labels nếu có.
- `language`: mã ngôn ngữ.
- `char_count`: số ký tự transcript.

---

## 2. Hướng mở rộng

Nếu cần speaker attribution chính xác hơn, có thể tách pipeline thành hai nhánh:

1. Transcription: lấy text/timestamps.
2. Diarization: xác định speaker segments.
3. Alignment: gộp word-level timestamps với speaker labels.
4. LLM intake: đưa structured speaker transcript vào analysis.

Việc thêm diarization engine riêng cần cân nhắc deploy resource, latency, privacy và chi phí vận hành. Nếu triển khai provider mới, provider đó phải kế thừa `BaseTranscriber` và có test riêng.
