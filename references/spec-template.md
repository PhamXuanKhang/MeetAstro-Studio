# SPEC — AI Product Hackathon

**Nhóm:** ___
**Track:** ☐ VinFast · ☐ Vinmec · ☐ VinUni-VinSchool · ☐ XanhSM · ☐ Open
**Problem statement (1 câu):** *Ai gặp vấn đề gì, hiện giải thế nào, AI giúp được gì*

---

## 1. AI Product Canvas

|   | Value | Trust | Feasibility |
|---|-------|-------|-------------|
| **Câu hỏi** | User nào? Pain gì? AI giải gì? | Khi AI sai thì sao? User sửa bằng cách nào? | Cost/latency bao nhiêu? Risk chính? |
| **Trả lời** | *Nhân viên văn phòng mất 30 phút/ngày phân loại email — AI gợi ý nhãn, giảm còn 5 phút* | *AI gắn sai nhãn → user thấy ngay, sửa 1 click, hệ thống học từ correction* | *~$0.01/email, latency <2s, risk: hallucinate nội dung nhạy cảm* |

**Automation hay augmentation?** ☐ Automation · ☐ Augmentation
Justify: *Augmentation — user thấy gợi ý và chấp nhận/từ chối, cost of reject = 0*

**Learning signal:**

1. User correction đi vào đâu? ___
2. Product thu signal gì để biết tốt lên hay tệ đi? ___
3. Data thuộc loại nào? ☐ User-specific · ☐ Domain-specific · ☐ Real-time · ☐ Human-judgment · ☐ Khác: ___
   Có marginal value không? (Model đã biết cái này chưa?) ___

---

## 2. User Stories — 4 paths

Mỗi feature chính = 1 bảng. AI trả lời xong → chuyện gì xảy ra?

### Feature: *tên feature*

**Trigger:** *VD: User nhận email mới → AI phân loại → ...*

| Path | Câu hỏi thiết kế | Mô tả |
|------|-------------------|-------|
| Happy — AI đúng, tự tin | User thấy gì? Flow kết thúc ra sao? | *Email tự gắn nhãn "Urgent", user thấy đúng, tiếp tục làm việc* |
| Low-confidence — AI không chắc | System báo "không chắc" bằng cách nào? User quyết thế nào? | *Hiện 2 nhãn gợi ý + confidence %, user chọn 1* |
| Failure — AI sai | User biết AI sai bằng cách nào? Recover ra sao? | *Email quan trọng bị gắn "FYI" → user thấy khi review → sửa nhãn* |
| Correction — user sửa | User sửa bằng cách nào? Data đó đi vào đâu? | *Kéo thả sang nhãn đúng → correction log → cải thiện model* |

*Lặp lại cho feature thứ 2-3 nếu có.*

---

## 3. Eval metrics + threshold

**Optimize precision hay recall?** ☐ Precision · ☐ Recall
Tại sao? ___
Nếu sai ngược lại thì chuyện gì xảy ra? *VD: Nếu chọn precision nhưng low recall → user không tìm thấy kết quả cần → bỏ dùng*

| Metric | Threshold | Red flag (dừng khi) |
|--------|-----------|---------------------|
| *VD: Accuracy phân loại đúng* | *≥85%* | *<70% trong 1 tuần* |
|   |   |   |
|   |   |   |

---

## 4. Top 3 failure modes

*Liệt kê cách product có thể fail — không phải list features.*
*"Failure mode nào user KHÔNG BIẾT bị sai? Đó là cái nguy hiểm nhất."*

| # | Trigger | Hậu quả | Mitigation |
|---|---------|---------|------------|
| 1 | *VD: Email chứa thuật ngữ ngoài domain* | *AI gắn nhãn sai, tự tin cao* | *Detect low-confidence → hỏi user xác nhận* |
| 2 |   |   |   |
| 3 |   |   |   |

---

## 5. ROI 3 kịch bản

|   | Conservative | Realistic | Optimistic |
|---|-------------|-----------|------------|
| **Assumption** | *100 user/ngày, 60% hài lòng* | *500 user/ngày, 80% hài lòng* | *2000 user/ngày, 90% hài lòng* |
| **Cost** | *$50/ngày inference* | *$200/ngày* | *$500/ngày* |
| **Benefit** | *Giảm 2h support/ngày* | *Giảm 8h/ngày* | *Giảm 20h, tăng retention 5%* |
| **Net** |   |   |   |

**Kill criteria:** *Khi nào nên dừng? VD: cost > benefit 2 tháng liên tục*

---

## 6. Mini AI spec (1 trang)

*Tóm tắt tự do — viết bằng ngôn ngữ tự nhiên, không format bắt buộc.*
*Gom lại: product giải gì, cho ai, AI làm gì (auto/aug), quality thế nào (precision/recall), risk chính, data flywheel ra sao.*
