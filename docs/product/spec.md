# SPEC — AI Meeting Assistant

**Nhóm:** A20-App-089
**Track:** ☑ Open
**Problem statement:** Nhân viên văn phòng và team lead mất 20–40 phút sau mỗi cuộc họp để nghe lại, ghi chép và tạo Jira tickets — AI Meeting Assistant tự động transcribe audio và extract action items có cấu trúc, giảm thời gian xuống còn 2 phút.

---

## 1. AI Product Canvas

> Chi tiết đầy đủ: [canvas.md](canvas.md)

|   | Value | Trust | Feasibility |
|---|-------|-------|-------------|
| **Trả lời** | Giảm 30 phút → 2 phút tạo action items sau họp. Không sót task nhờ AI extract toàn bộ transcript. | User review transcript + analysis trước khi push Jira. Sai → sửa text → re-analyze. | ~$0.03/cuộc họp, latency 20–30s, risk hallucinate action items. |

**Automation hay augmentation?** ☑ Augmentation
Justify: User luôn review và confirm trước khi export — cost of reject = 0.

**Learning signal:**
1. User correction đi vào đâu? → Transcript sửa tay được dùng làm input cho analyzer. [TBD] Log corrections.
2. Signal: tỷ lệ user push Jira (cao = analysis tốt), tỷ lệ re-analyze (thấp = hài lòng).
3. Data: ☑ User-specific · ☑ Domain-specific · ☑ Human-judgment
   Có marginal value — ngữ cảnh nội bộ công ty mà model chung không biết.

---

## 2. User Stories — 4 paths

### Feature 1: Transcribe Audio

**Trigger:** User upload file audio (.wav/.mp3/.m4a) → nhấn "Transcribe" → Whisper API xử lý → hiển thị transcript.

| Path | Mô tả |
|------|-------|
| **Happy — AI đúng, tự tin** | Transcript hiển thị chính xác, user đọc lướt thấy đúng, tiếp tục nhấn "Phân tích". |
| **Low-confidence — AI không chắc** | Whisper API fail (network/quota) → fallback Local Whisper + hiện warning "Đang dùng local model, chất lượng có thể thấp hơn". User đọc transcript, quyết định chấp nhận hoặc re-upload. |
| **Failure — AI sai** | Transcript sai nhiều (accent nặng, nhiều tiếng ồn) → user thấy text vô nghĩa. User chỉnh tay trong text area hoặc upload lại file audio khác. |
| **Correction — user sửa** | User edit trực tiếp transcript trong text area trước khi analyze. Bản sửa được dùng làm input cho bước phân tích. |

### Feature 2: Analyze → Extract Action Items

**Trigger:** User có transcript (tự động hoặc đã chỉnh sửa) → nhấn "Phân tích" → GPT-4o extract → hiển thị Epic/Task/Subtask.

| Path | Mô tả |
|------|-------|
| **Happy — AI đúng, tự tin** | Analysis hiển thị Epic/Task/Subtask chính xác, đúng assignee/deadline/priority. User nhấn export hoặc push Jira. |
| **Low-confidence — AI không chắc** | GPT-4o trả về assignee = `null` hoặc deadline = `null` cho nhiều tasks → UI hiện "TBD" / "N/A". User biết cần bổ sung thông tin. |
| **Failure — AI sai** | GPT-4o hallucinate action item không có trong transcript, hoặc gán sai priority. User thấy bất thường khi review → không push Jira, sửa transcript → re-analyze. |
| **Correction — user sửa** | User sửa transcript → re-analyze. [TBD] Cho phép edit trực tiếp analysis output trước khi export. |

### Feature 3: Export & Push to Jira

**Trigger:** User có analysis kết quả → chọn Download (MD/JSON/CSV) hoặc "Push to Jira".

| Path | Mô tả |
|------|-------|
| **Happy** | Download file thành công / Jira tickets tạo đúng (Epic → Task → Subtask với đúng fields). |
| **Low-confidence** | Jira credentials chưa cấu hình → stub mode, UI hiện warning "Jira STUB mode — chưa gửi API thật". User biết cần config `.env`. |
| **Failure** | Jira API trả lỗi (permission, invalid fields) → UI hiện error message. Không có data loss vì analysis vẫn còn trong session. |
| **Correction** | User export lại sau khi sửa analysis. Jira tickets đã tạo cần sửa trực tiếp trên Jira. |

---

## 3. Eval metrics + threshold

**Optimize precision hay recall?** ☑ Recall
**Tại sao:** Sót action item (low recall) nguy hiểm hơn thừa — task không ai follow-up có thể gây miss deadline. Thừa action item (low precision) chỉ mất vài giây để user bỏ đi khi review.
**Nếu sai ngược lại:** Nếu chọn precision nhưng low recall → sót task quan trọng → user mất tin tưởng, quay lại ghi tay.

| Metric | Threshold | Red flag (dừng khi) |
|--------|-----------|---------------------|
| **Recall — action items extracted / action items thực tế** | ≥ 85% | < 70% trên 3 cuộc họp liên tiếp |
| **Transcription WER** (Word Error Rate — so với human transcript) | ≤ 20% cho tiếng Việt | > 35% cho tiếng Việt chuẩn |
| **Structured output validity** — % responses parse được thành schema | ≥ 95% | < 85% trong 1 tuần |
| **Latency end-to-end** (upload → analysis hiển thị) | ≤ 60s cho audio ≤ 10 phút | > 120s consistently |

---

## 4. Top 3 failure modes

| # | Trigger | Hậu quả | Mitigation |
|---|---------|---------|------------|
| 1 | **Audio chất lượng kém** (nhiều người nói cùng lúc, tiếng ồn, accent nặng) | Whisper transcribe sai → analysis dựa trên transcript lỗi → action items vô nghĩa. User **có thể không biết** nếu không đọc kỹ transcript. | Hiển thị transcript để user verify trước khi analyze. [TBD] Thêm confidence score per segment. |
| 2 | **GPT-4o hallucinate action items** không có trong transcript | Tạo task giả, giao cho người không liên quan. Nếu user không review kỹ → push lên Jira → confusion. | Yêu cầu GPT-4o trích dẫn `context` từ transcript cho mỗi task. User cross-check context ↔ transcript. Augmentation mode bắt buộc review trước push. |
| 3 | **API outage** (OpenAI down hoặc rate limit) | User không transcribe/analyze được → workflow bị block. | Fallback chain: Whisper API → Local Whisper. [TBD] Cache analyzer — retry queue. Hiện error message rõ ràng thay vì fail im lặng. |

---

## 5. ROI 3 kịch bản

|   | Conservative | Realistic | Optimistic |
|---|-------------|-----------|------------|
| **Assumption** | 1 team 5 người, 3 cuộc họp/tuần, 60% dùng tool | 3 teams (15 người), 10 cuộc họp/tuần, 80% dùng tool | 10 teams (50+ người), 30 cuộc họp/tuần, 90% dùng tool |
| **Cost** | ~$0.50/tuần (API) + hosting free (local) | ~$3/tuần (API) + $5/tháng (cloud hosting) | ~$10/tuần (API) + $20/tháng (cloud) |
| **Benefit** | Tiết kiệm ~1.5h/tuần (3 họp × 30 phút) | Tiết kiệm ~5h/tuần + giảm miss-task 50% | Tiết kiệm ~15h/tuần + Jira automation giảm admin work |
| **Net** | Dương nhẹ — cost thấp, benefit vừa | Dương rõ — $3/tuần cho 5h là rất hiệu quả | Dương mạnh — ROI > 10x |

**Kill criteria:** Cost > benefit 2 tháng liên tục, HOẶC recall < 70% sau khi đã optimize prompt 3 lần, HOẶC user adoption < 30% sau 1 tháng trial.

---

## 6. Mini AI spec

AI Meeting Assistant là tool **augmentation** giúp nhân viên văn phòng tự động hóa việc ghi chép cuộc họp. User upload audio → Whisper transcribe → GPT-4o extract action items (Epic → Task → Subtask) → export Markdown/JSON/CSV hoặc push Jira.

AI **không tự quyết** — user luôn review transcript và analysis trước khi hành động. Điều này quan trọng vì Whisper có thể sai với tiếng Việt accent nặng, và GPT-4o có thể hallucinate action items. Safety net: mỗi task có `context` field trích dẫn từ transcript để user verify.

Quality target: recall ≥ 85% (không sót task), WER ≤ 20%, structured output valid ≥ 95%. Risk chính: audio kém chất lượng và hallucination. Mitigation: augmentation mode bắt buộc, fallback chain transcription, context trích dẫn.

Data flywheel hiện chưa có — hướng phát triển: log user corrections (transcript edits, tasks bị bỏ) → improve prompt → fine-tune model domain-specific dài hạn.

---

*Dựa trên [Spec template](../../references/spec-template.md) — VinUni A20 — AI Thực Chiến · 2026*
