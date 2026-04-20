# LLM Analysis Workflow

Quá trình não bộ AI (LLM) phân tách từ một văn bản thô dài dằng dặc thành các object có cấu trúc (Epic, Task, Subtask).

---

## 1. Kiến trúc hiện hành (Single Stage Workflow)

Hệ thống đang gọi trực tiếp mô hình GPT qua một Pipeline ngắn gọn và được tối ưu hoá chi phí API 1 lần:
1. `analysis_service.py` tiếp nhận `transcript`.
2. Gắn kèm System Prompt (nút thắt tạo khuôn được lưu tại thư mục `/prompts/`).
3. Kích hoạt tính năng **JSON Mode**: Yêu cầu OpenAI API bắt buộc phải trả về object JSON theo định dạng Pydantic chuẩn hoá `MeetingAnalysis`.
4. Tái cấu trúc JSON đó thông qua `MeetingAnalysis.from_dict()` và kết thúc luồng.

---

## 2. Kiến trúc tương lai: Multi-Stage Agent (Roadmap)

Khi cuộc họp kéo dài hàng giờ (Over 1-2 hours) và Transcript chứa đầy các đoạn hội thoại "um, uh", ngập ngừng, sai ngữ pháp vì STT lỗi, việc đẩy nguyên con vào 1 LLM lấy Task và Epic sẽ giảm đáng kể độ chính xác. Bức tranh tương lai đó là áp dụng Multi-Stage Agents (Chain of Agents).

**Quy trình dự kiến:**
*   **Stage 1: Cleaning & Formatting (Lọc tín hiệu nhiễu)**
    - Agent thứ 1 (Ví dụ: `gpt-4o-mini` - Model nhỏ gọn giá rẻ) tiếp nhận toàn bộ Transcript.
    - Nhiệm vụ: Xoá bỏ các từ ngập ngừng (stuttering), sửa lỗi sai chính tả của Whisper, gom gọn các ý lặp lại.
    - Output 1: `Clean_Transcript.txt`.
*   **Stage 2: Core Analysis & Extraction (Tìm Task/Epic)**
    - Agent thứ 2 (Ví dụ: `gpt-4o` bản max power). Có khả năng nhạy bén lấy chính xác Task.
    - Đọc vào tệp tin đã sạch rác ở Stage 1 để tạo Action Item (Epic -> Task -> Subtask).
    - Phân quyền Assignee và Deadline dựa trên thông tin Meeting.
*   **Stage 3: Decision Summarize (Chắt lọc Tóm tắt)**
    - Agent thứ 3: Chuyên viết lại Summary Executive (Báo cáo đánh giá tóm tắt).
    - Sẽ chạy stream response về client song song với Stage 2.

Hệ thống đa tầng này giúp giải quyết các nút thắt về Token Limits và tăng tính ổn định của JSON đầu ra lên tối đa.
