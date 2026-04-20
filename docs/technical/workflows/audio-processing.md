# Audio Processing Workflow

Luồng xử lý âm thanh trong hệ thống, bắt đầu từ File Âm Thanh nguyên gốc cho tới khi phân tách ra văn bản thô (Transcript).

---

## 1. Kiến trúc hiện hành (Current Workflow)

Hiện hành, quá trình xử lý âm thanh trong dự án theo tiêu chí Đơn Giản, Chạy Nhanh, và Tập trung vào cấu trúc Transcript. 

**STT (Speech-To-Text) Workflow:**
1. Trích xuất Input File: Upload `.mp3`/`.wav`. Hoặc sử dụng tính năng Record `recording_service.py` để thâu băng từ System Desktop + Microphone Mixing.
2. STT Engine: Gọi qua `transcription_service.py`. Dùng Provider Pattern định sẵn:
   - Thử sử dụng `OpenAITranscriber` (Whisper API qua request đám mây).
   - *Fallback:* Nếu gặp Timeout hoặc Network lỗi, chuyển sang `LocalTranscriber` (mô hình base của Whisper được lưu local).
3. Output: Hệ thống xuất ra duy nhất 1 chuỗi string `transcript` hoàn chỉnh lưu nội dung toàn bộ văn bản gốc mà không phân biệt ai đang nói câu nào. 

---

## 2. Kiến trúc tương lai: Diarization & Alignment (Roadmap)

Khi hệ thống quy mô (Scale up), việc chỉ có văn bản Text thô mà không có người nói sẽ dẫn đến AI tạo ra các Task bị lộn xộn, sai chủ thể nhận việc (Assignee). Do đó, luồng Audio sẽ phải thêm bước Diarization.

**Quy trình dự kiến:**
1. **Parallel Computing**: Cùng một file âm thanh Input, hệ thống sẽ đẩy vào 2 tiến trình chạy song song (Parallels):
   - Nhánh 1: Transcription (Speech-To-Text) - lấy nguyên con Text.
   - Nhánh 2: Diarization Engine (Ví dụ dùng thư viện Pyannote Audio) để quét và ngắt thời gian từng người nói: `(Speaker A: 00:00 -> 00:20)`, `(Speaker B: 00:21 -> 00:25)`.
2. **Alignment (So khớp)**: So gộp Transcript Text có timestamps (Word-level timestamps của Whisper) vào với Diarization Labels. 
3. **Data Transform**: Đúc ra bộ object kiểu `[{"speaker": "Speaker A", "text": "Hôm nay chúng ta họp về..."}]`.
4. **LLM Intake**: Đẩy Object đã phân tách người nói vào nhánh LLM Analysis.

*P/S: Việc cài đặt Diarization sẽ kéo theo nhu cầu deploy một model Voice-Recognition tương đối nặng trong background, tuỳ thuộc vào Server Resources để đưa ra quyết định Scale cho phù hợp.*
