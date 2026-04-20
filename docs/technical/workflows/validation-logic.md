# Validation Logic Workflow

Tài liệu này giải thích cách hoạt động của hệ thống kiểm tra chéo (Cross-Validation). Mục đích của hệ thống này là tính toán độ Cậy Mức (Confidence Score) cho từng Action Item mà AI sinh ra, qua đó chặn AI bị "ảo giác" (hallucinate - tự bịa ra task).

---

## 1. Tầm quan trọng của Cross Validation

LLM bản chất là các trình dự đoán từ tiếp theo. Khi phải trích xuất Task, đôi khi nó tự tưởng tượng thêm hành động hoặc giao sai người. `validation_service.py` đóng vai trò là "Giám thị" dò bài làm của AI trước khi trả ra report.

## 2. Kỹ thuật chấm điểm

Hệ thống hoạt động theo 2 luồng: 1 luồng nhốt Transcript vào Regex thông thường (Rule-based), 1 luồng gọi AI. Trải qua các thuật tính toán sau:

### 2.1. Rule-based Extraction (Thợ cơ bản)
Dùng biểu thức chính quy (Regex) quét toàn bộ transcript xem có rớt lại các dấu hiệu công việc không.
- Bắt pattern giao việc: Tên Người + `(will | to | must | should)` + Hành động.
  VD: *Long will implement the API.*
- Chụp thời hạn (Deadline): Dùng regex quét `by [thời gian]`, `next week`, `tomorrow`.
- Output: Quy đổi ra list các Task Mẫu của máy tính. (Thường độ chính xác là 50% vì câu nói trong meeting rất phức tạp).

### 2.2. Điểm kiểm chứng chéo AI vs. Regex (Cross-validation Score)
Tính dựa trên **35% trọng số tổng điểm**.
- Thuật toán so khớp chữ (Text Similarity / Jaccard Index).
- So bài tập làm của AI và bài làm của Rule-base Regex. Nếu giống nhau trên 60% về chữ, chứng tỏ Task đó chắc chắn đã được nhắc tới một cách rõ ràng trong buổi họp.

### 2.3. Điểm bám sát ngữ cảnh (Context Coherence Score)
Tính dựa trên **35% trọng số tổng điểm**.
- Thuật toán lọc trích xuất 8 từ khoá chính (Core Words lớn hơn 3 ký tự) trong Action Task sinh ra từ con AI.
- Đem đối chiếu thẳng 8 từ này xem nó "Có mặt" trong đoạn băng Transcript gốc hay không. Nếu TỶ LỆ từ vựng trùng khớp cao, chứng tỏ AI không tự sáng tác ra thêm từ vựng ngoài, độ bám sát xuất sắc.

### 2.4. Điểm hình thức cấu trúc (Structural Validation Score)
Tính dựa trên **30% trọng số tổng điểm**.
- Bắt buộc Title/Description phải có một Động từ hành động (Action verb): `implement`, `create`, `fix`, `review`...
- Độ dài vừa phải (6-200 char). 
- Đạt chuẩn thì lấy trọn 30% điểm này.

## 3. Luật Trừ Điểm Bổ Sung (Penalty Rules)

Sau khi trộn thành `overall_score` ra hệ số tối đa 1.0 (ví dụ 0.85). Hệ thống "Giám Thị" sẽ phạt nguội các tật xấu của con AI hiện tại:
*   Trừ **-15% điểm (0.15)** nếu Title quá ngắn, thể hiện nội dung hời hợt.
*   Trừ **-5% điểm (0.05)** nếu AI tạo Task nhưng không tìm ra người làm, bỏ không dòng Assignee.
*   Trừ **-10% điểm (0.10)** nếu cuối Title là dấu `?` vì như thế nó là một thắc mắc treo của nhân sự, không phải một "Action item" để làm JIRA.

Mỗi ticket lưu lại một cục `validation_notes` liệt kê vì sao bị trừ điểm, kèm số `confidence` Float. Kỹ thuật này giúp Team Developer tối ưu model an toàn mà không phải phụ thuộc mù quáng vào kết quả JSON của GPT-4o.
