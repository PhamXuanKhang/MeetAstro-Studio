# Quy Trình Kiểm Thử App — AI Meeting Assistant

> Tài liệu này mô tả **quy trình kiểm thử toàn diện** cho AI Meeting Assistant, bao gồm cách xây dựng dataset, chạy các loại test, tính metrics, và đánh giá chất lượng AI output.

**Người đọc mặc định:** Developer / QA engineer.

**Thứ tự đọc khuyến nghị:**
```
1. Tổng quan quy trình (Phần 1)
2. Chuẩn bị dataset (Phần 2) ← ĐỌC KỸ PHẦN NÀY
3. Chạy unit tests (Phần 3)
4. Chạy eval tests (Phần 4)
5. Đo latency & monitoring (Phần 5)
6. Smoke test thủ công (Phần 6)
7. CI/CD integration (Phần 7)
```

---

## Phần 1 — Tổng quan quy trình kiểm thử

### 1.1 Các tầng kiểm thử

```
┌─────────────────────────────────────────────────────────────┐
│  Tầng 1: Unit Tests (pytest)                                │
│  - Schema, services, providers, validation                  │
│  - Chạy: mỗi lần sửa code                                   │
│  - Tool: pytest tests/ -v                                    │
├─────────────────────────────────────────────────────────────┤
│  Tầng 2: Eval Tests (ground truth + automated metrics)       │
│  - Recall, Precision, WER, Field Completeness                 │
│  - Chạy: mỗi lần sửa prompt hoặc thay đổi AI provider      │
│  - Tool: pytest tests/test_eval_metrics.py -v                 │
├─────────────────────────────────────────────────────────────┤
│  Tầng 3: Integration Tests (mocked E2E)                     │
│  - Full pipeline: upload → transcribe → analyze → Jira push  │
│  - Chạy: trước khi merge PR                                  │
│  - Tool: pytest tests/test_integration.py -v                  │
├─────────────────────────────────────────────────────────────┤
│  Tầng 4: Manual Smoke Test                                  │
│  - UI + API thật, audio mẫu                                 │
│  - Chạy: khi có thay đổi lớn hoặc release                  │
│  - Tool: Checklist trong Phần 6                              │
├─────────────────────────────────────────────────────────────┤
│  Tầng 5: Performance & Latency                             │
│  - Đo tốc độ transcription, analysis, E2E                    │
│  - Chạy: khi nghi ngờ có regression về tốc độ               │
│  - Tool: timing logs + manual stopwatch                       │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Bảng tổng hợp metrics

| # | Metric | Tầng | Threshold | Red Flag | Tool |
|---|--------|------|-----------|----------|------|
| 1 | Action Item Recall | 2 | ≥ 85% | < 70% | `test_eval_metrics.py` |
| 2 | Action Item Precision | 2 | ≥ 75% | < 60% | `test_eval_metrics.py` |
| 3 | Transcription WER | 2 | ≤ 20% (VI) | > 35% | `jiwer` |
| 4 | Schema Validity | 2 | ≥ 95% | < 85% | `test_eval_metrics.py` |
| 5 | Field Completeness | 2 | ≥ 60% | < 40% | `test_eval_metrics.py` |
| 6 | Transcription Latency | 5 | ≤ 15s | > 30s | Timing logs |
| 7 | Analysis Latency | 5 | ≤ 10s | > 20s | Timing logs |
| 8 | E2E Latency | 5 | ≤ 60s | > 120s | Timing logs |
| 9 | Validation Overall Confidence | 1 | ≥ 0.7 | < 0.4 | `test_validation_service.py` |
| 10 | Transcript Edit Rate | 4 | < 30% | > 50% | User tracking |
| 11 | Push-to-Jira Rate | 4 | > 50% | < 30% | User tracking |
| 12 | Re-analyze Rate | 4 | < 15% | > 30% | User tracking |

---

## Phần 2 — Dataset Kiểm thử (Chi tiết)

Phần này mô tả **toàn bộ** những gì cần để tạo một bộ dataset chất lượng: cấu trúc file, nguồn dữ liệu, số lượng khuyến nghị, quy trình thu thập, và cách xử lý.

### 2.1 Tổng quan dataset cần xây dựng

Dataset phục vụ 2 mục đích:
1. **Eval analysis** (transcript → AI analysis): đo Recall, Precision, Schema Validity, Validation Confidence
2. **Eval transcription** (audio → transcript): đo WER (Word Error Rate) — **cần audio file thật**

> Dataset eval analysis không cần audio, chỉ cần `transcript.txt` và `ground_truth.json`.
> Dataset eval transcription cần thêm `audio.wav` (hoặc `audio.mp3`) và `transcript.txt`.

### 2.2 Scope sản phẩm quyết định cấu trúc dataset

Dựa trên `docs/product/spec.md` và `docs/product/roadmap.md`:

| Thông số | Giá trị | Ý nghĩa cho dataset |
|----------|---------|---------------------|
| **Ngôn ngữ** | Tiếng Việt (60%) + Tiếng Anh (40%) | Phân bổ dataset theo tỷ lệ này |
| **Độ dài audio** | 5–30 phút (target E2E ≤ 60s) | Chỉ lấy họp 5–30 phút |
| **Loại họp** | Sprint planning, standup, retro, product review, brainstorm, informal, decision, incident | Đủ 8 loại để cover edge cases |
| **Tasks/họp** | 2–8 tasks thực tế | Ground truth cũng phải có 2–8 tasks |
| **Recall target** | ≥ 85% | Cần ≥ 15 samples mới đủ statistical significance |
| **WER target** | ≤ 20% (tiếng Việt), ≤ 15% (tiếng Anh) | Chỉ đo được với audio thật |

---

### 2.3 Cấu trúc thư mục toàn bộ dataset

```
data/
└── eval/
    └── samples/                                    ← Thư mục gốc của dataset
        │
        ├── vi_sprint_01/                         ← Sample 1: Sprint planning tiếng Việt
        │   ├── transcript.txt                     ← ✅ Bắt buộc (cho cả eval analysis + eval transcription)
        │   ├── ground_truth.json                 ← ✅ Bắt buộc (cho eval analysis)
        │   ├── metadata.json                      ← ✅ Bắt buộc
        │   └── audio.wav                         ← ⚠️ Tùy chọn (chỉ cần nếu đo WER)
        │
        ├── vi_sprint_02/                         ← Sample 2
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │   └── audio.wav
        │
        ├── vi_standup_01/                         ← Sample 3: Daily standup tiếng Việt
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │   └── audio.wav
        │
        ├── vi_standup_02/
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │
        ├── vi_retro_01/                          ← Sample 5: Retrospective tiếng Việt
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │
        ├── vi_product_review_01/
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │
        ├── vi_brainstorm_01/
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │
        ├── vi_decision_01/                        ← Decision-making meeting
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │
        ├── vi_incident_01/                        ← Incident review (edge case)
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │
        ├── vi_no_action_01/                       ← Negative case: không có action item
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │
        ├── vi_short_01/                           ← Edge case: < 5 phút
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │
        ├── en_sprint_01/                          ← Tiếng Anh
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │   └── audio.wav
        │
        ├── en_standup_01/
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │
        ├── en_retro_01/
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │
        ├── en_product_review_01/
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │
        ├── en_client_call_01/                    ← Client meeting
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │
        ├── en_decision_01/
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │
        ├── en_no_action_01/                       ← Negative case
        │   ├── transcript.txt
        │   ├── ground_truth.json
        │   ├── metadata.json
        │
        └── en_short_01/                           ← Edge case: < 5 phút
            ├── transcript.txt
            ├── ground_truth.json
            └── metadata.json
```

**Tổng cộng: 20 samples** (11 tiếng Việt + 9 tiếng Anh).

---

### 2.4 Chi tiết từng file trong mỗi sample

#### 2.4.1 `transcript.txt` — Transcript chuẩn

**Mục đích:** Làm input cho AI analyzer trong eval test. Cũng là ground truth để so sánh với Whisper output khi đo WER.

**Quy tắc viết:**

| Quy tắc | Chi tiết |
|---------|----------|
| **Ngôn ngữ** | Giữ nguyên ngôn ngữ gốc. Tiếng Việt thì viết tiếng Việt, tiếng Anh thì viết tiếng Anh. Không dịch. |
| **Format** | Mỗi dòng = lời của 1 speaker, theo định dạng `SpeakerName: nội dung` |
| **Giọng nói** | SpeakerName = tên thật hoặc giả (Alice, Bob, Hùng, Lan...) — dùng nhất quán xuyên suốt |
| **Thứ tự** | Giữ nguyên thứ tự theo thời gian thực của cuộc họp |
| **Không sửa** | Không chỉnh sửa sau khi tạo. Sai thì tạo lại sample mới. |
| **Không paraphrase** | Giữ nguyên cách nói của người tham gia, kể cả câu chưa hoàn chỉnh |
| **Không thêm** | Không thêm thông tin không có trong audio/original source |

**Ví dụ tiếng Việt đúng format:**

```
Minh: Chào cả nhà, hôm nay chúng ta họp sprint planning cho Q2.
Hùng: Mình nghĩ chúng ta nên ưu tiên feature thanh toán trước.
Lan: Đồng ý. Minh sẽ implement thanh toán, deadline là cuối tháng.
Minh: OK. Hùng phụ trách test, Lan review code.
Hùng: Mình sẽ viết test cases vào tuần sau.
Lan: Mình cần API specs từ Minh trước thứ Hai.
Minh: Không vấn đề gì, mình sẽ gửi vào thứ Hai sáng.
Hùng: Còn phần refund thì sao?
Minh: Refund sẽ làm sau, hiện tại ưu tiên thanh toán đã.
Lan: Vậy mình sẽ để refund vào backlog.
```

**Ví dụ tiếng Anh đúng format:**

```
Sarah: Let's start the sprint review. John, can you share the demo?
John: Sure. So we've completed the login feature this sprint.
Sarah: Great. And what about the dashboard?
John: The dashboard is at 80%, Mike is finishing the charts.
Sarah: When will it be done?
John: By end of this week, hopefully.
Sarah: Okay. Mike, can you have it shipped by Friday?
Mike: I'll try. I need test data from John first.
John: I can have the test data ready by Wednesday.
Sarah: Perfect. Anything else to discuss?
Mike: The API is sometimes slow. Should we add caching?
John: Yes, let's add Redis caching. I'll create a ticket for that.
Sarah: Good idea. John, assign it to yourself and let's aim for next sprint.
```

**Độ dài khuyến nghị:**

| Loại | Độ dài transcript | Tương đương audio | Số dòng ước tính |
|------|-------------------|---------------------|-------------------|
| **Short** | 100–300 từ | 2–5 phút | 6–15 dòng |
| **Medium** | 300–800 từ | 5–15 phút | 15–40 dòng |
| **Long** | 800–2000 từ | 15–30 phút | 40–100 dòng |

---

#### 2.4.2 `ground_truth.json` — Action Items chuẩn

**Mục đích:** Ground truth để so sánh với AI output, tính Recall và Precision.

**Cấu trúc JSON đầy đủ:**

```json
{
  "meeting_id": "vi_sprint_01",
  "language": "vi",
  "duration_minutes": 15,
  "summary": "Sprint planning Q2 tập trung vào feature thanh toán. Minh implement, Hùng test, Lan review. Refund được để vào backlog.",
  "epics": [
    {
      "summary": "Payment Feature",
      "description": "Xây dựng feature thanh toán cho Q2 launch",
      "tasks": [
        {
          "summary": "Implement thanh toán",
          "assignee": "Minh",
          "deadline": "2024-01-31",
          "priority": "High",
          "context": "Minh implement feature thanh toán, deadline cuối tháng. Đây là feature ưu tiên cao nhất của sprint Q2."
        },
        {
          "summary": "Viết test cases cho thanh toán",
          "assignee": "Hùng",
          "deadline": "2024-01-15",
          "priority": "High",
          "context": "Hùng viết test cases vào tuần sau, cần API specs từ Minh trước thứ Hai."
        },
        {
          "summary": "Review code cho feature thanh toán",
          "assignee": "Lan",
          "deadline": "2024-01-25",
          "priority": "Medium",
          "context": "Lan review code sau khi Minh implement xong."
        }
      ]
    },
    {
      "summary": "Refactoring",
      "description": "Các công việc cải thiện hệ thống",
      "tasks": [
        {
          "summary": "Add Redis caching cho API",
          "assignee": "Minh",
          "deadline": null,
          "priority": "Medium",
          "context": "API đang chậm, cần thêm Redis caching. Sẽ làm trong sprint sau."
        }
      ]
    }
  ],
  "key_decisions": [
    "Ưu tiên feature thanh toán trước refund",
    "Refunds được để vào backlog"
  ],
  "discussion_points": [
    "Team thảo luận về tech stack cho thanh toán",
    "API cần cải thiện tốc độ"
  ],
  "parking_lot": [
    "Investigate third-party payment providers (để follow-up sau)"
  ]
}
```

**Chi tiết từng trường:**

| Trường | Kiểu | Bắt buộc | Mô tả | Ví dụ |
|--------|-------|---------|-------|-------|
| `meeting_id` | string | ✅ | ID duy nhất, trùng với tên folder | `"vi_sprint_01"` |
| `language` | string | ✅ | Ngôn ngữ của transcript | `"vi"` hoặc `"en"` |
| `duration_minutes` | number | ✅ | Thời lượng ước tính (phút) | `15` |
| `summary` | string | ✅ | Tóm tắt 3–8 câu, viết bằng ngôn ngữ của transcript | `"Sprint planning Q2..."` |
| `epics` | array | ✅ | Danh sách Epic. Empty array `[]` nếu không có action item. | Xem bên dưới |
| `key_decisions` | array[string] | ✅ | Các quyết định quan trọng có ảnh hưởng lớn | `["Ưu tiên login trước"]` |
| `discussion_points` | array[string] | ✅ | Các điểm thảo luận không có action cụ thể | `["Team thảo luận tech stack"]` |
| `parking_lot` | array[string] | ✅ | Những thứ cần follow-up sau, không phải task hiện tại | `["Investigate third-party auth"]` |

**Chi tiết `epics[].tasks[]`:**

| Trường | Kiểu | Bắt buộc | Mô tả | Ví dụ |
|--------|-------|---------|-------|-------|
| `summary` | string | ✅ | Tên task dạng Jira-style, bắt đầu bằng động từ | `"Implement login feature"` |
| `assignee` | string \| null | ✅ | Người phụ trách. `null` nếu không được đề cập. | `"Minh"` hoặc `null` |
| `deadline` | string \| null | ✅ | Ngày định dạng `YYYY-MM-DD`. `null` nếu không đề cập. | `"2024-01-15"` hoặc `null` |
| `priority` | string | ✅ | Một trong 4 giá trị: `"Critical"`, `"High"`, `"Medium"`, `"Low"` | `"High"` |
| `context` | string | ✅ | 1–3 câu giải thích: tại sao task tồn tại, hoàn thành nghĩa là gì, chi tiết nào từ transcript | `"Minh implement login, deadline thứ Sáu"` |

**Quy tắc khi annotate ground truth:**

1. **Mỗi Epic phải có ít nhất 1 Task**
2. **Mỗi Task phải có:** `summary`, `assignee`, `deadline`, `priority`, `context`
3. **`assignee = null`** khi transcript không nói rõ ai làm
4. **`deadline = null`** khi transcript không đề cập deadline
5. **`priority`** đánh theo quy tắc:
   - `"Critical"`: blocker, incident, deadline rất gần, ảnh hưởng release
   - `"High"`: ưu tiên cao, ảnh hưởng nhiều users/teams
   - `"Medium"`: quan trọng nhưng không gấp, investigation
   - `"Low"`: ideas, improvements, nice-to-have
6. **Không tạo Task** cho insight/discussion không có action cụ thể → cho vào `discussion_points`
7. **Context** phải có thật trong transcript, không bịa đặt

**Priority đánh sai phổ biến cần tránh:**
- Đánh `"High"` cho mọi task → không có ý nghĩa phân biệt
- Đánh `"Low"` cho task có deadline cụ thể và quan trọng
- Đánh `"Critical"` cho task bình thường

**Ví dụ ground_truth cho negative case (không có action item):**

```json
{
  "meeting_id": "vi_no_action_01",
  "language": "vi",
  "duration_minutes": 5,
  "summary": "Cuộc họp informal check-in, không có quyết định hay action item nào.",
  "epics": [],
  "key_decisions": [],
  "discussion_points": [
    "Team hỏi thăm nhau về công việc",
    "Không có nội dung cụ thể cần follow-up"
  ],
  "parking_lot": []
}
```

---

#### 2.4.3 `metadata.json` — Thông tin bổ sung

**Mục đích:** Lưu thông tin về nguồn gốc và đặc điểm của sample, phục vụ phân tích kết quả eval theo nhóm (theo ngôn ngữ, loại họp, độ dài).

**Cấu trúc JSON đầy đủ:**

```json
{
  "meeting_id": "vi_sprint_01",
  "language": "vi",
  "meeting_type": "sprint_planning",
  "duration_minutes": 15,
  "duration_category": "medium",
  "participant_count": 3,
  "participant_names": ["Minh", "Hùng", "Lan"],
  "meeting_date": "2024-01-05",
  "source": "synthetic",
  "source_detail": "Script generate_eval_samples.py",
  "audio_available": false,
  "audio_path": null,
  "audio_format": null,
  "annotation_status": "done",
  "annotator": "Khang",
  "annotation_date": "2024-01-10",
  "notes": "Synthetic meeting — action items clear and well-structured"
}
```

**Chi tiết từng trường:**

| Trường | Kiểu | Bắt buộc | Mô tả | Ví dụ |
|--------|-------|---------|-------|-------|
| `meeting_id` | string | ✅ | Trùng với tên folder và `ground_truth.json` | `"vi_sprint_01"` |
| `language` | string | ✅ | `"vi"` hoặc `"en"` | `"vi"` |
| `meeting_type` | string | ✅ | Loại cuộc họp (xem bảng bên dưới) | `"sprint_planning"` |
| `duration_minutes` | number | ✅ | Thời lượng phút | `15` |
| `duration_category` | string | ✅ | `"short"` (< 5 phút), `"medium"` (5–15 phút), `"long"` (15–30 phút) | `"medium"` |
| `participant_count` | number | ✅ | Số người tham gia | `3` |
| `participant_names` | array[string] | ✅ | Danh sách tên người tham gia | `["Minh", "Hùng", "Lan"]` |
| `meeting_date` | string | ✅ | Ngày họp định dạng `YYYY-MM-DD` | `"2024-01-05"` |
| `source` | string | ✅ | Nguồn gốc sample | Xem bảng bên dưới |
| `source_detail` | string | ✅ | Chi tiết nguồn gốc | `"AMI Meeting Corpus ES2005a"` |
| `audio_available` | boolean | ✅ | Có audio file không | `false` hoặc `true` |
| `audio_path` | string \| null | ✅ | Đường dẫn audio, `null` nếu không có | `null` hoặc `"vi_sprint_01/audio.wav"` |
| `audio_format` | string \| null | ✅ | Format audio, `null` nếu không có | `null` hoặc `"wav"` |
| `annotation_status` | string | ✅ | `"pending"`, `"in_progress"`, `"done"` | `"done"` |
| `annotator` | string \| null | ✅ | Người annotate | `"Khang"` hoặc `null` |
| `annotation_date` | string \| null | ✅ | Ngày annotate | `"2024-01-10"` hoặc `null` |
| `notes` | string | ❌ | Ghi chú bổ sung | `"Edge case: no deadline mentioned"` |

**Giá trị hợp lệ cho `meeting_type`:**

| Giá trị | Mô tả |
|---------|-------|
| `sprint_planning` | Sprint planning — nhiều tasks, deadline rõ ràng |
| `daily_standup` | Daily standup — ngắn, nhiều tasks nhỏ, status update |
| `retrospective` | Retrospective — what went well, what didn't, action items |
| `product_review` | Product review — demo, feedback, priorities |
| `brainstorm` | Brainstorm — nhiều ideas, không phải tất cả đều thành task |
| `decision_meeting` | Decision-making — quyết định quan trọng, assignee + deadline |
| `client_call` | Client meeting — thường tiếng Anh, technical discussion |
| `incident_review` | Incident review — bug/incident, ưu tiên Critical/High |
| `informal_checkin` | Informal check-in — **negative case**: không có action item |
| `one_on_one` | 1-on-1 meeting |
| `all_hands` | Company-wide meeting |

**Giá trị hợp lệ cho `source`:**

| Giá trị | Mô tả |
|---------|-------|
| `synthetic` | Tạo bằng script, không có audio thật |
| `self_recorded` | Tự record cuộc họp thật có consent |
| `ami_corpus` | Từ AMI Meeting Corpus |
| `icsi_corpus` | Từ ICSI Meeting Corpus |
| `common_voice` | Từ Mozilla Common Voice dataset |
| `youtube` | Từ transcript YouTube video |

---

#### 2.4.4 `audio.wav` (hoặc `audio.mp3`) — File âm thanh

**Mục đích:** Chỉ cần thiết khi đo **Transcription WER**.

**Quy định:**
- **Format khuyến nghị:** WAV, 16kHz, mono (để tương thích với Whisper API)
- **Độ dài:** Tương ứng với transcript (2–30 phút)
- **Chất lượng:** Càng gần thực tế càng tốt (nhiều người nói, có tiếng ồn nền)
- **Tên file:** Luôn đặt là `audio.wav` hoặc `audio.mp3` (cố định, không đổi tên)
- **Vị trí:** Đặt trong folder của sample: `vi_sprint_01/audio.wav`

> **Lưu ý:** Nếu không có audio, vẫn chạy được eval tests cho analysis. Chỉ cần bỏ skip WER test.

---

### 2.5 Bảng tổng hợp files bắt buộc cho mỗi sample

| File | Bắt buộc | Dùng cho |
|------|-----------|---------|
| `transcript.txt` | ✅ Luôn | Eval analysis + Eval transcription (WER) |
| `ground_truth.json` | ✅ Luôn | Eval analysis (Recall, Precision) |
| `metadata.json` | ✅ Luôn | Phân nhóm kết quả, trace nguồn gốc |
| `audio.wav` / `audio.mp3` | ⚠️ Chỉ khi đo WER | Eval transcription (WER) |

---

### 2.6 Nguồn lấy dataset

#### 2.6.1 Tiếng Việt — Không có dataset cuộc họp tiếng Việt có sẵn

**Khuyến nghị:** Kết hợp 3 phương án

| Phương án | Số lượng | Ưu điểm | Nhược điểm |
|-----------|---------|---------|-----------|
| **Tự record cuộc họp team** | 5–8 samples | Dữ liệu thực tế nhất, đúng domain | Cần consent từ người tham gia, mất thời gian |
| **Synthetic generation** | 3–5 samples | Nhanh, kiểm soát được complexity | Không thực tế bằng dữ liệu thật |
| **Common Voice (vi)** | 0–2 samples | Miễn phí, nhiều giọng | Không phải cuộc họp, phải ghép thành cuộc họp giả lập |

**Quy trình tự record cho tiếng Việt:**

```
1. Xin consent từ tất cả người tham gia (email hoặc chat)
2. Record cuộc họp thật bằng chính app này
3. Export transcript từ app
4. Human annotation ground_truth.json
5. Đặt vào folder: data/eval/samples/vi_<loại>_<số>
6. Nếu có audio: giữ lại file audio gốc → đặt vào sample folder
```

**Lưu ý consent:** Vì dataset này dùng cho eval nội bộ (không công bố public), consent đơn giản có thể là tin nhắn trong nhóm chat team: *"Mình sẽ dùng transcript cuộc họp hôm nay để test app. Ai không đồng ý thì reply nhé."*

#### 2.6.2 Tiếng Anh — Phong phú và miễn phí

| Nguồn | Link | Đặc điểm | Phù hợp cho | Số lượng khuyến nghị |
|--------|------|-----------|------------|---------------------|
| **AMI Meeting Corpus** | `corpus2.ml` hoặc `github.com/cypher002/ami-process` | ~100h audio, 171 cuộc họp, transcript word-level timestamps, speaker labels | ✅ Best choice: sprint, decision, brainstorm | 5–7 samples |
| **ICSI Meeting Corpus** | `icsi.meetingbuffer` | ~72h audio, 75 cuộc họp, có transcript chuẩn | ✅ Rất tốt: decision, product review | 2–3 samples |
| **VoxConverse** | `github.com/joonson/voxconverse` | ~120h multi-speaker audio, có transcript | ⚠️ Không phải cuộc họp chuẩn, dùng cho WER test | 0–2 samples |
| **TED-LIUM** | `mistral-data` | ~450h TED talks | ❌ Không phải cuộc họp | 0 |
| **Common Voice** | `commonvoice.mozilla.org` | ~100k giờ audio đa ngôn ngữ | ⚠️ Không phải cuộc họp | 0–1 |

#### 2.6.3 Quy trình lấy từ AMI Meeting Corpus

AMI là nguồn tốt nhất cho tiếng Anh vì:
- Miễn phí, cho mục đích nghiên cứu
- Có transcript chuẩn chi tiết đến từng từ + timestamp
- Đa dạng loại cuộc họp (sprint, brainstorm, decision)
- Có speaker labels

**Bước 1: Download**

```bash
# Cách 1: Download toàn bộ corpus (~10GB)
wget https://corpus2.ml/ami/ami-corpus-0.0.1.tar.gz
tar -xzf ami-corpus-0.0.1.tar.gz

# Cách 2: Download chỉ phần English Headset (~3GB)
wget https://corpus2.ml/ami/ami- headset-oh-3.2.tar.gz
tar -xzf ami-headset-oh-3.2.tar.gz
```

**Bước 2: Cấu trúc thư mục AMI**

```
ami-corpus/
├── ami/ # Audio
│   └── en/ # English only
│       ├── audio/ # Headset audio
│       │   ├── ES2005a.wav
│       │   ├── ES2005b.wav
│       │   └── ...
│       └── ...
├── doc/ # Documentation
└── output/ # Transcripts
    ├── words/ # Word-level transcripts
    │   ├── ES2005a.words
    │   └── ...
    └── md/ # Markdown transcripts
        ├── ES2005a.md
        └── ...
```

**Bước 3: Chọn các cuộc họp phù hợp**

Mỗi cuộc họp AMI có prefix:
- `ES` = Engineering design (decision, design)
- `IS` = Interview
- `TS` = Training
- `BM` = Business meeting

Ưu tiên các prefix `ES` cho dataset vì gần nhất với use case.

Danh sách khuyến nghị:

| Meeting ID | Loại | Độ dài | Đặc điểm |
|-----------|------|--------|----------|
| `ES2005a` | Decision | ~25 phút | 4 speakers, thiết kế máy |
| `ES2005b` | Decision | ~25 phút | 4 speakers, cùng chủ đề ES2005a |
| `ES2005c` | Decision | ~25 phút | 4 speakers, cùng chủ đề |
| `ES2006a` | Decision | ~25 phút | 4 speakers, thiết kế máy khác |
| `ES2015a` | Brainstorm | ~30 phút | 5 speakers, nhiều ideas |
| `ES2016a` | Decision | ~20 phút | 4 speakers |
| `ES2016b` | Decision | ~20 phút | 4 speakers |
| `IS1005a` | Interview | ~15 phút | 2 speakers |
| `IS1005b` | Interview | ~15 phút | 2 speakers |
| `TS3005a` | Training | ~20 phút | Nhiều speakers |

**Bước 4: Trích xuất transcript từ AMI**

File `.md` trong `output/md/` đã có format gần với `SpeakerName: text`:

```bash
# Xem trước 20 dòng đầu của 1 transcript
head -20 ami-corpus/output/md/ES2005a.md
```

Output sẽ có dạng:

```
# ES2005a
...
Person A # [42:19] - 42:22
I think the first thing we need to decide is...
...
```

Cần viết script để:
1. Đọc file `.md` → clean → format thành `Speaker: text`
2. Tạo `transcript.txt` chuẩn
3. Tạo `metadata.json` với `source: "ami_corpus"`, `source_detail: "ES2005a"`
4. Copy audio file `.wav` vào sample folder

**Bước 5: Human annotation ground_truth.json**

Vì AMI transcript đã có sẵn đầy đủ nội dung, annotation nhanh hơn:
1. Đọc transcript
2. Trích xuất action items → annotate vào `ground_truth.json`
3. Đánh dấu `annotation_status: "done"`

---

### 2.7 Số lượng và phân bổ dataset khuyến nghị

#### 2.7.1 Tổng số samples: 20

| Nhóm | Số lượng | Tỷ lệ | Lý do |
|------|---------|--------|-------|
| Tiếng Việt | 11 | 55% | Ngôn ngữ chính của sản phẩm |
| Tiếng Anh | 9 | 45% | Ngôn ngữ secondary, dùng để verify prompt EN |

#### 2.7.2 Phân bổ theo độ dài

| Loại | Độ dài | Số VI | Số EN | Tổng |
|------|--------|-------|-------|-------|
| `short` | < 5 phút | 2 | 2 | 4 |
| `medium` | 5–15 phút | 6 | 5 | 11 |
| `long` | 15–30 phút | 3 | 2 | 5 |

#### 2.7.3 Phân bổ theo loại cuộc họp

| Loại họp | VI | EN | Tổng | Ghi chú |
|-----------|----|----|------|--------|
| `sprint_planning` | 2 | 1 | 3 | Nhiều action items rõ ràng |
| `daily_standup` | 2 | 1 | 3 | Ngắn, nhiều tasks nhỏ |
| `retrospective` | 1 | 1 | 2 | Mixed action + insight |
| `product_review` | 1 | 1 | 2 | Technical depth |
| `brainstorm` | 1 | 0 | 1 | Nhiều ideas, lọc action items |
| `decision_meeting` | 1 | 1 | 2 | Ai quyết định, assignee + deadline |
| `client_call` | 0 | 1 | 1 | Tiếng Anh, formal |
| `incident_review` | 1 | 0 | 1 | Edge case: priority Critical |
| `informal_checkin` | 1 | 1 | 2 | **Negative case**: không có action |
| `one_on_one` | 0 | 0 | 0 | Có thể bổ sung sau |
| `all_hands` | 0 | 0 | 0 | Có thể bổ sung sau |
| `short` (< 5 phút) | 1 | 1 | 2 | Edge case: < 5 phút |
| **Tổng** | **11** | **9** | **20** | |

#### 2.7.4 Phân bổ theo nguồn

| Nguồn | Số lượng | Ngôn ngữ | Ghi chú |
|--------|---------|----------|--------|
| Synthetic (script) | 5 | VI + EN | Đã có sẵn trong `generate_eval_samples.py` |
| AMI Meeting Corpus | 7 | EN | Download + filter |
| ICSI Meeting Corpus | 2 | EN | Download + filter |
| Tự record team | 5–6 | VI | Record thật + annotate |
| **Tổng** | **19–20** | | |

---

### 2.8 Quy trình xử lý dataset từ nguồn trên mạng

#### Bước 1: Thu thập sơ bộ

```bash
# 1. Tạo thư mục
mkdir -p data/eval/samples

# 2. Download AMI corpus
wget https://corpus2.ml/ami/ami-corpus-0.0.1.tar.gz
tar -xzf ami-corpus-0.0.1.tar.gz

# 3. Download ICSI corpus (nếu cần)
# wget https://...
```

#### Bước 2: Trích xuất transcript từ nguồn

Với **AMI corpus**:
- File `output/md/ESXXXXx.md` chứa transcript đã có speaker labels
- Cần clean: loại bỏ timestamp, format lại thành `Speaker: text`
- Độ dài ước tính từ số dòng hoặc metadata trong file

Với **ICSI corpus**:
- File `.mrt` chứa transcript XML-style
- Parse để lấy speaker + text

Với **tự record**:
- Export transcript từ app hoặc dùng transcript tự đánh máy từ audio
- Nếu dùng app để record → transcript có sẵn trong Supabase

#### Bước 3: Tạo `transcript.txt`

```bash
# Copy transcript đã clean vào folder sample
# Ví dụ: chọn ES2005a từ AMI corpus
cp ami-corpus/output/md/ES2005a.md data/eval/samples/en_sprint_01/transcript_raw.md

# Sau đó clean bằng tay hoặc script → transcript.txt
```

#### Bước 4: Human annotation ground_truth.json

**Thời gian ước tính:**
- 1 cuộc họp 15–20 phút: **15–25 phút** để annotate
- 20 cuộc họp: **5–8 giờ** annotation tổng cộng
- Nên chia cho 2 người để giảm fatigue

**Quy trình annotation từng sample:**

```
1. Mở transcript.txt trong folder sample
2. Đọc toàn bộ transcript (1–2 lần)
3. Đọc từng câu, hỏi:
   a. Có ai nhận việc làm gì không? (assignee)
   b. Có deadline không? (deadline)
   c. Độ ưu tiên nào? (priority)
   d. Tại sao việc này tồn tại? (context)
4. Nhóm các tasks có liên quan vào cùng 1 Epic
5. Điền vào ground_truth.json
6. Điền summary (3–8 câu tóm tắt)
7. Điền key_decisions, discussion_points, parking_lot
8. Đánh dấu annotation_status = "done"
```

#### Bước 5: Tạo `metadata.json`

```bash
# Tạo nhanh metadata.json cho từng sample
# (Sau khi đã hoàn thành annotation)
```

#### Bước 6: Validate dataset

Sau khi tạo xong toàn bộ dataset, chạy validation:

```python
# Kiểm tra dataset có lỗi không
# (Viết script validate riêng hoặc dùng pytest fixture)

import json
from pathlib import Path

def validate_sample(folder: Path) -> list[str]:
    errors = []
    sid = folder.name

    # Check required files
    for fname in ["transcript.txt", "ground_truth.json", "metadata.json"]:
        if not (folder / fname).exists():
            errors.append(f"{sid}: missing {fname}")

    # Validate transcript length
    transcript = (folder / "transcript.txt").read_text(encoding="utf-8")
    if len(transcript.strip()) < 50:
        errors.append(f"{sid}: transcript too short ({len(transcript)} chars)")

    # Validate ground truth JSON
    gt = json.loads((folder / "ground_truth.json").read_text(encoding="utf-8"))
    if "language" not in gt:
        errors.append(f"{sid}: missing 'language'")
    if "summary" not in gt:
        errors.append(f"{sid}: missing 'summary'")
    for epic in gt.get("epics", []):
        if not epic.get("tasks"):
            errors.append(f"{sid}: epic '{epic.get('summary','')}' has no tasks")
        for task in epic.get("tasks", []):
            if "summary" not in task:
                errors.append(f"{sid}: task missing 'summary'")
            priority = task.get("priority", "Medium")
            if priority not in {"Critical", "High", "Medium", "Low"}:
                errors.append(f"{sid}: invalid priority '{priority}'")

    # Validate metadata
    meta = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    if meta.get("annotation_status") != "done":
        errors.append(f"{sid}: annotation not done (status={meta.get('annotation_status')})")

    return errors
```

---

### 2.9 Checklist hoàn thiện dataset

Sau khi tạo mỗi sample, đánh dấu checklist:

- [ ] `transcript.txt` tồn tại và ≥ 50 ký tự
- [ ] `transcript.txt` đúng format `Speaker: text` mỗi dòng
- [ ] `transcript.txt` giữ nguyên ngôn ngữ gốc
- [ ] `ground_truth.json` tồn tại và valid JSON
- [ ] `ground_truth.json` có đúng trường: `meeting_id`, `language`, `summary`, `epics`, `key_decisions`, `discussion_points`, `parking_lot`
- [ ] Mỗi Epic trong `ground_truth.json` có ít nhất 1 Task
- [ ] Mỗi Task có: `summary`, `assignee`, `deadline`, `priority`, `context`
- [ ] `deadline` là `null` nếu không đề cập trong transcript
- [ ] `priority` là một trong: `"Critical"`, `"High"`, `"Medium"`, `"Low"`
- [ ] `metadata.json` tồn tại và valid JSON
- [ ] `metadata.json` có `annotation_status = "done"`
- [ ] `annotation_status = "done"` với `annotator` và `annotation_date` được điền
- [ ] `duration_minutes` trong `ground_truth.json` và `metadata.json` trùng nhau
- [ ] Nếu có audio: `audio.wav` hoặc `audio.mp3` tồn tại trong folder

---

## Phần 3 — Unit Tests

### 3.1 Chạy toàn bộ unit tests

```bash
# Tất cả tests
pytest tests/ -v

# Với coverage
pytest tests/ -v --cov=src --cov-report=term-missing

# Một file cụ thể
pytest tests/test_validation_service.py -v

# Một test class cụ thể
pytest tests/test_validation_service.py::TestValidateActionItems -v

# Một test cụ thể
pytest tests/test_validation_service.py::TestValidateActionItems::test_overlap_gives_higher_confidence -v
```

### 3.2 Danh sách test files hiện có

| File | Mô tả | Trạng thái |
|------|--------|-------------|
| `tests/test_schema.py` | Domain schema, enum, serialization round-trip | ✅ Pass |
| `tests/test_openai_analyzer.py` | Mock OpenAI analyzer, JSON parsing, retry | ✅ Pass |
| `tests/test_openai_transcriber.py` | Mock Whisper API transcriber | ✅ Pass |
| `tests/test_openai_diarize_transcriber.py` | Mock diarization transcriber | ✅ Pass |
| `tests/test_whisper_livekit_transcriber.py` | Mock WhisperLiveKit transcriber | ✅ Pass |
| `tests/test_transcription_service.py` | Transcription + diarization fallback | ✅ Pass |
| `tests/test_analysis_service.py` | Analysis orchestration, empty transcript | ✅ Pass |
| `tests/test_validation_service.py` | Confidence scoring, rule-based cross validation | ✅ Pass |
| `tests/test_recording_service.py` | Recording service orchestration | ✅ Pass |
| `tests/test_exporter.py` | Markdown/JSON/CSV export | ✅ Pass |
| `tests/test_jira_client.py` | Jira REST payloads, auth, stub mode | ✅ Pass |
| `tests/test_jira_service.py` | Jira push Epic → Task → Subtask | ✅ Pass |
| `tests/test_audio_ingestion.py` | Upload validation, ffmpeg, video-to-audio | ✅ Pass |
| `tests/test_integration.py` | Mocked integration flow | ✅ Pass |

### 3.3 Thứ tự chạy test đúng

```bash
# 1. Lint + type check trước
flake8 . --max-line-length=100
mypy . --ignore-missing-imports

# 2. Unit tests
pytest tests/ -v

# 3. Eval tests (sau khi có dataset)
pytest tests/test_eval_metrics.py -v

# 4. Integration tests
pytest tests/test_integration.py -v
```

### 3.4 Pass criteria

| Tool | Pass criteria |
|------|---------------|
| `flake8` | 0 warnings |
| `mypy` | 0 errors |
| `pytest` | All passing |

---

## Phần 4 — Evaluation Tests (Automated Metrics)

> Phần này cần dataset đã tạo ở **Phần 2**.

### 4.1 Chạy eval tests

```bash
# Tất cả eval tests
pytest tests/test_eval_metrics.py -v

# Chỉ recall tests
pytest tests/test_eval_metrics.py -v -k "recall"

# Chỉ validation metrics tests
pytest tests/test_eval_metrics.py -v -k "validation"

# Với verbose output (log metrics cho từng sample)
pytest tests/test_eval_metrics.py -v -k "per_sample" -s

# Chỉ test samples tiếng Việt
pytest tests/test_eval_metrics.py -v -k "vi_"
```

### 4.2 Thêm WER test (Transcription Quality)

WER test yêu cầu `jiwer` và audio files trong dataset.

```bash
# Cài jiwer
uv pip install jiwer

# Tạo audio files cho WER test
# (Copy audio từ AMI corpus vào các sample folders)

# Chạy WER tests
pytest tests/test_wer_metrics.py -v -s
```

---

## Phần 5 — Performance & Latency

### 5.1 Đo Transcription Latency

```python
import time
from src.providers.openai_transcriber import OpenAITranscriber

transcriber = OpenAITranscriber()
audio_path = "data/recordings/test_audio.mp3"

start = time.time()
result = transcriber.transcribe(audio_path)
elapsed = time.time() - start

print(f"Transcription latency: {elapsed:.2f}s")
assert elapsed <= 15.0, f"Transcription too slow: {elapsed:.2f}s > 15s"
```

### 5.2 Đo Analysis Latency

```python
import asyncio, time
from src.services.analysis_service import analyze_async

transcript = open("data/eval/samples/vi_sprint_01/transcript.txt").read()

start = time.time()
result = asyncio.run(analyze_async(transcript))
elapsed = time.time() - start

print(f"Analysis latency: {elapsed:.2f}s")
assert elapsed <= 10.0, f"Analysis too slow: {elapsed:.2f}s > 10s"
```

### 5.3 Đo End-to-End Latency

```python
import time, asyncio
from src.services.audio_ingestion_service import normalize_audio
from src.providers.openai_transcriber import OpenAITranscriber
from src.services.analysis_service import analyze_async

def measure_e2e(audio_path: str) -> float:
    start = time.time()
    normalized = normalize_audio(audio_path)
    transcript_result = OpenAITranscriber().transcribe(normalized)
    transcript = transcript_result["text"]
    asyncio.run(analyze_async(transcript))
    return time.time() - start
```

### 5.4 Latency thresholds summary

| Metric | Threshold | Red Flag |
|--------|-----------|----------|
| Transcription (≤ 5 phút audio) | ≤ 15s | > 30s |
| Analysis | ≤ 10s | > 20s |
| End-to-end (upload → hiển thị) | ≤ 60s | > 120s |

---

## Phần 6 — Manual Smoke Test Checklist

> Chạy khi có thay đổi lớn hoặc trước release.

### 6.1 Chuẩn bị

1. Start backend: `uvicorn src.api.main:app --reload --port 8000`
2. Start Celery worker: `celery -A src.workers.celery_app worker -Q default --loglevel=info`
3. Start Electron app: `cd electron-app && npm run dev`
4. Chuẩn bị file audio mẫu: `data/recordings/test_audio.mp3`

### 6.2 Checklist

#### Upload & Transcribe

- [ ] Upload file `.wav` → job được queue → transcript hiển thị sau polling
- [ ] Upload file `.mp3` → job được queue → transcript hiển thị sau polling
- [ ] Upload file `.m4a`, `.ogg`, `.mp4`, `.mkv`, `.webm` → được convert và transcribe đúng
- [ ] Bật/tắt diarization → transcript vẫn trả về hợp lệ
- [ ] Transcript field editable → edits được lưu qua `PATCH /transcript`

#### Analyze

- [ ] Click "Analyze" → job được queue → Epic/Task/Subtask hiển thị
- [ ] Mỗi task hiển thị: summary, assignee (hoặc TBD), deadline (hoặc N/A), priority
- [ ] Low-confidence/flagged items được highlight để review
- [ ] `overall_confidence` hiển thị gần mỗi task

#### Review

- [ ] Approve một item → item chuyển sang trạng thái approved
- [ ] Reject một item → item bị loại khỏi Jira queue
- [ ] Edit item rồi approve → thay đổi được lưu
- [ ] Approve all → tất cả items được approve

#### Export

- [ ] "Export Markdown" → file `.md` mở đúng với format Epic → Task → Subtask
- [ ] "Export JSON" → valid JSON, có `epics`, `summary`, `key_decisions`
- [ ] "Export CSV" → header + data rows, parse được trong Excel/Google Sheets

#### Jira Push

- [ ] Meeting xuất hiện trong History sau khi analyze
- [ ] "Push to Jira" bị chặn nếu còn pending review items
- [ ] "Push to Jira" chạy STUB mode khi thiếu credentials (hiển thị mock output)
- [ ] "Push to Jira" thành công khi có đủ credentials

#### Edge Cases

- [ ] Transcribe khi chưa upload file → button disabled hoặc API trả lỗi rõ ràng
- [ ] Analyze khi transcript trống → button disabled hoặc API trả lỗi rõ ràng
- [ ] Upload file rất lớn (> 25MB) → xử lý hợp lý với error/warning
- [ ] Cuộc họp không có action item → vẫn trả về summary, không crash

---

## Phần 7 — CI/CD Integration

### 7.1 GitHub Actions workflow

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv pip install -e ".[all]"
      - name: Lint
        run: flake8 . --max-line-length=100
      - name: Type check
        run: mypy . --ignore-missing-imports
      - name: Unit tests
        run: pytest tests/ -v --tb=short

  eval-tests:
    name: Evaluation Tests
    runs-on: ubuntu-latest
    if: vars.OPENAI_API_KEY != ''
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv pip install -e ".[all]"
      - name: Create dataset
        run: python scripts/generate_eval_samples.py
      - name: Evaluation tests
        run: pytest tests/test_eval_metrics.py -v --tb=short
        env:
          OPENAI_API_KEY: ${{ vars.OPENAI_API_KEY }}
```

---

## Phụ lục A — Logging & Monitoring

Thêm logging vào `src/services/analysis_service.py`:

```python
logger.info(
    "Analysis completed",
    extra={
        "meeting_id": meeting_id,
        "duration_seconds": elapsed,
        "epics_count": len(analysis.epics),
        "tasks_count": sum(len(e.tasks) for e in analysis.epics),
        "avg_confidence": round(avg_confidence, 3),
        "metrics": metrics,
    }
)
```

| Metric | Log field | Alert threshold |
|--------|-----------|----------------|
| Recall | `eval.recall` | < 0.70 liên tiếp 3 lần |
| Precision | `eval.precision` | < 0.60 |
| WER | `eval.wer` | > 0.35 |
| Transcription Latency | `transcription.latency_s` | > 30s |
| Analysis Latency | `analysis.latency_s` | > 20s |

---

## Phụ lục B — Kill Criteria

Dừng dự án hoặc thay đổi hướng tiếp cận khi:

1. **Cost > Benefit**: API cost vượt $100/tháng cho < 100 cuộc họp
2. **Recall < 70%**: sau khi đã optimize prompt 3 lần mà không cải thiện
3. **User Adoption < 30%**: sau 1 tháng trial với user thật
4. **Schema Validity < 85%**: GPT-4o response không parse được

---

## Phụ lục C — Quick Reference

```bash
# ═══════════════════════════════════════════════════════
# QUICK START — Tạo dataset + chạy test
# ═══════════════════════════════════════════════════════

# 1. Tạo 5 samples synthetic (đã có sẵn)
python scripts/generate_eval_samples.py

# 2. Lint + type check
flake8 . --max-line-length=100
mypy . --ignore-missing-imports

# 3. Unit tests
pytest tests/ -v

# 4. Eval tests (cần OPENAI_API_KEY)
pytest tests/test_eval_metrics.py -v -s

# 5. WER tests (cần audio + jiwer)
uv pip install jiwer
pytest tests/test_wer_metrics.py -v -s

# ═══════════════════════════════════════════════════════
# KHI NÀO CHẠY GÌ?
# ═══════════════════════════════════════════════════════

# Mỗi lần sửa code nhỏ:
#   → pytest tests/ -v

# Mỗi lần sửa prompt/analyzer:
#   → pytest tests/test_eval_metrics.py -v -s

# Mỗi lần sửa Whisper provider:
#   → pytest tests/test_eval_metrics.py -v -s
#   → pytest tests/test_wer_metrics.py -v -s

# Trước khi merge PR:
#   → flake8 . && mypy . && pytest tests/ -v && pytest tests/test_eval_metrics.py -v

# Trước release:
#   → Full manual smoke test (Phần 6)
```
