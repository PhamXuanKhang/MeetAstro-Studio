# Evaluation Metrics

Các chỉ số đo lường chất lượng AI và product health.

---

## Chiến lược đánh giá

**Optimize:** Recall (không sót action item) > Precision (không thừa).

**Lý do:** Sót task quan trọng (false negative) → không ai follow-up → miss deadline. Thừa task (false positive) → user bỏ đi chỉ mất vài giây khi review.

---

## Metrics & Thresholds

### AI Quality Metrics

| # | Metric | Định nghĩa | Threshold | Red Flag | Đo bằng cách nào |
|---|--------|------------|-----------|----------|-------------------|
| 1 | **Action Item Recall** | Số action items AI extract đúng / Tổng action items thực tế trong transcript | ≥ 85% | < 70% trên 3 transcripts liên tiếp | So sánh AI output với human-labeled ground truth |
| 2 | **Action Item Precision** | Số action items AI extract đúng / Tổng action items AI đưa ra | ≥ 75% | < 60% (quá nhiều hallucinated tasks) | So sánh AI output với human-labeled ground truth |
| 3 | **Transcription WER** | Word Error Rate — so sánh Whisper output với human transcript | ≤ 20% cho tiếng Việt | > 35% | Dùng `jiwer` hoặc manual spot-check |
| 4 | **Schema Validity** | % responses từ GPT-4o parse được thành `MeetingAnalysis` | ≥ 95% | < 85% trong 1 tuần | Log parse errors trong `OpenAIAnalyzer` |
| 5 | **Field Completeness** | % tasks có đủ assignee + deadline (không null) | ≥ 60% | < 40% | Count non-null fields trong analysis output |

### Performance Metrics

| # | Metric | Threshold | Red Flag |
|---|--------|-----------|----------|
| 6 | **Transcription Latency** | ≤ 15s cho audio ≤ 5 phút | > 30s |
| 7 | **Analysis Latency** | ≤ 10s | > 20s |
| 8 | **End-to-end Latency** | ≤ 60s (upload → analysis hiển thị) | > 120s consistently |
| 9 | **Diarization Fallback Rate** | % diarization requests fallback sang plain OpenAI Whisper transcription | Tracking only | > 30% (diarization provider có vấn đề) |

### Product Health Metrics (khi có user)

| # | Metric | Ý nghĩa | Target |
|---|--------|---------|--------|
| 10 | **Transcript Edit Rate** | % sessions user chỉnh transcript trước analyze | Thấp = transcribe tốt. Target: < 30% |
| 11 | **Push-to-Jira Rate** | % sessions user nhấn Push Jira sau analyze | Cao = analysis chất lượng. Target: > 50% |
| 12 | **Re-analyze Rate** | % sessions user analyze cùng transcript > 1 lần | Thấp = hài lòng. Target: < 15% |

---

## Current Implementation Status

### Đã có

- [x] **Unit tests** cho tất cả services và providers (14 test files)
- [x] **E2E script** (`test_e2e.sh`) cho full pipeline test
- [x] **Mock infrastructure** cho OpenAI, Whisper, Jira trong tests
- [x] **Container với MockAnalyzer** khi `OPENAI_API_KEY` không set
- [x] **Jira stub mode** khi credentials thiếu

### Chưa có / Cần implement

- [ ] **Automated eval pipeline** với ground truth samples
- [ ] **WER calculation** tự động (hiện tại manual spot-check)
- [ ] **Recall/Precision tracking** với dashboard
- [ ] **Latency monitoring** trong production

---

## Evaluation Pipeline

### Cách eval hiện tại: Manual spot-check

1. Chuẩn bị ≥ 5 audio files cuộc họp thật (hoặc giả lập)
2. Tạo human-labeled ground truth cho mỗi file:
   - Transcript chuẩn (human transcribe)
   - Action items chuẩn (human extract)
3. Chạy pipeline: audio → transcribe → analyze
4. So sánh output vs ground truth → tính recall, precision, WER

### Cách eval tương lai: Automated eval

```
audio_samples/
├── meeting_01.wav
├── meeting_01_transcript.txt     ← human transcript
├── meeting_01_actions.json       ← human-labeled action items
├── meeting_02.wav
├── ...
```

Script eval:

```python
# [TBD] Chưa implement
def eval_recall(ai_actions, human_actions) -> float: ...
def eval_precision(ai_actions, human_actions) -> float: ...
def eval_wer(ai_transcript, human_transcript) -> float: ...
```

---

## Confidence Scoring

AI extract action items kèm confidence score (0-1). Items có confidence < 0.7 được **flag** để user review trước khi push Jira.

| Confidence Range | Behavior |
|-----------------|----------|
| ≥ 0.9 | Auto-approved (high confidence) |
| 0.7 - 0.9 | Draft, recommend review |
| < 0.7 | Flagged, require review before Jira push |

---

## Kill Criteria

Dừng dự án hoặc thay đổi hướng tiếp cận khi:

1. **Cost > benefit** 2 tháng liên tiếp
2. **Recall < 70%** sau khi đã optimize prompt 3 lần
3. **User adoption < 30%** sau 1 tháng trial (khi có user thật)
4. **API cost** vượt $100/tháng cho < 100 cuộc họp

---

## Logging & Monitoring

Để track metrics, thêm logging trong `src/services/`:

```python
# Transcription
logger.info(f"Transcription completed", extra={
    "meeting_id": meeting_id,
    "duration_seconds": elapsed,
    "segments_count": len(segments),
    "diarization_enabled": diarize,
    "fallback_used": fallback
})

# Analysis
logger.info(f"Analysis completed", extra={
    "meeting_id": meeting_id,
    "duration_seconds": elapsed,
    "epics_count": len(result.epics),
    "tasks_count": sum(len(e.tasks) for e in result.epics),
    "avg_confidence": avg_confidence
})
```

Tích hợp với logging aggregation (Datadog, Grafana, etc.) để dashboard hóa metrics.
