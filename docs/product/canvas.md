# AI Product Canvas — AI Meeting Assistant

**Nhóm:** A20-App-089
**Ngày:** 12/04/2026

---

## Canvas

|   | Value | Trust | Feasibility |
|---|-------|-------|-------------|
| **Câu hỏi** | User nào? Pain gì? AI giải gì mà cách hiện tại không giải được? | Khi AI sai thì user bị ảnh hưởng thế nào? User biết AI sai bằng cách nào? User sửa bằng cách nào? | Cost bao nhiêu/request? Latency bao lâu? Risk chính là gì? |
| **Trả lời** | **User:** team lead / PM / operator điều phối cuộc họp. **Pain:** Mất 1 người điều phối, note nội dung meeting sẽ ghi chép action items, tạo Jira tickets thủ công. Người note đôi khi không có đủ kiến thức tổng quát về cuộc họp hoặc là không ghi chép kịp dẫn đến thường bị sót task hoặc ghi sai assignee/deadline. **AI giải:** Tự động transcribe audio → extract action items có cấu trúc (Epic/Task/Subtask) → đẩy thẳng Jira. Giảm từ 30 phút → 2 phút. | **Khi AI sai:** Sai assignee → task giao nhầm người. Sai priority → task quan trọng bị bỏ qua. Sót action item → không ai follow-up. **User biết sai bằng cách nào:** Transcript hiển thị ngay, user đọc verify nhanh lại so với nội dung cuộc họp vừa nghe. Analysis hiển thị structured (Epic/Task/Subtask), user review từng item trước khi export. **User sửa:** Chỉnh transcript text trực tiếp trước khi analyze. Review analysis output → chỉ push Jira khi đã confirm. | **Cost:** ~$0.02–0.05/cuộc họp (Whisper API ~$0.006/phút + GPT-4o ~$0.01–0.03/request). **Latency:** Transcribe 5 phút audio ≈ 10–15s. Analyze ≈ 5–10s. Tổng ≈ 20–30s. **Risk:** API key leak; Whisper transcribe sai tiếng Việt nặng accent; GPT-4o hallucinate action item không có trong transcript. |

---

## Automation hay augmentation?

☐ Automation — AI làm thay, user không can thiệp
☑ **Augmentation** — AI gợi ý, user quyết định cuối cùng

**Justify:** AI transcribe + extract action items, nhưng user **luôn review** transcript và analysis trước khi save/export/push Jira. Nếu AI sai (ghi nhầm assignee, sót task), user thấy ngay trên UI và sửa được. Cost of reject = 0 (chỉ cần không nhấn "Push to Jira"). Nếu làm automation hoàn toàn → task sai giao nhầm người → mất thời gian hơn là tự ghi.

---

## Learning signal

| # | Câu hỏi | Trả lời |
|---|---------|---------|
| 1 | User correction đi vào đâu? | User chỉnh transcript (text area) trước khi analyze → transcript đã sửa được dùng làm input cho analyzer. Hiện chưa lưu diff giữa bản gốc và bản sửa. **[TBD]** Log corrections vào DB để fine-tune prompt sau. |
| 2 | Product thu signal gì để biết tốt lên hay tệ đi? | **Trực tiếp:** Tỷ lệ user chỉnh transcript trước khi analyze (thấp = transcribe tốt). Tỷ lệ user nhấn "Push to Jira" sau khi analyze (cao = analysis chất lượng). **Gián tiếp:** Số lần user re-analyze cùng transcript (nhiều = chưa hài lòng). **[TBD]** Cần thêm analytics logging. |
| 3 | Data thuộc loại nào? | ☑ User-specific (audio cuộc họp nội bộ) · ☑ Domain-specific (ngữ cảnh công ty, tên nhân sự) · ☐ Real-time · ☑ Human-judgment (user review/sửa analysis) · ☐ Khác |

**Có marginal value không?**
Có. Model GPT-4o biết extract action items tổng quát, nhưng **không biết** ngữ cảnh nội bộ công ty (tên nhân sự, quy trình riêng, thuật ngữ ngành). Transcript + corrections của user là data domain-specific mà không ai khác có. Tuy nhiên, hiện tại chưa có feedback loop để tận dụng data này — đây là hướng phát triển dài hạn.

---

*Dựa trên [AI Product Canvas template](../references/canvas-template.md) — VinUni A20 — AI Thực Chiến · 2026*
