### 🟢 PHASE 1 — MVP (P0) — 36 use cases

| ID | Tên | Nhóm |
|----|-----|------|
| A1 | Đăng ký bằng email/password | Auth |
| A2 | Đăng ký bằng Google OAuth | Auth |
| A3 | Xác thực email | Auth |
| A4 | Đăng nhập bằng email/password | Auth |
| A5 | Đăng nhập bằng Google OAuth | Auth |
| A6 | Quên mật khẩu / Reset password | Auth |
| A8 | Đăng xuất | Auth |
| B1 | Cấu hình Jira credentials | Settings |
| B2 | Test kết nối Jira | Settings |
| B4 | Cấu hình OpenAI API key (BYOK) ⬆️ | Settings |
| C1 | Tạo meeting mới | Input |
| C2 | Tải lên file audio | Input |
| C3 | Tải lên file video | Input |
| C4 | Bắt đầu live recording | Input |
| C7 | Dừng recording | Input |
| C9 | Xem trạng thái pipeline | Input |
| D1 | Xem transcript streaming real-time | Transcript |
| D2 | Xem transcript hoàn chỉnh | Transcript |
| D3 | Xem diarization (phân biệt speaker) | Transcript |
| D4 | Đổi tên speaker (with màu sắc) 🔄 | Transcript |
| D5 | Chỉnh sửa nội dung transcript | Transcript |
| E1 | Trigger analysis | Analysis |
| E2 | Xem meeting summary | Analysis |
| E3 | Xem kết quả analysis (action items + decisions + parking lot) 🔀 | Analysis |
| E6 | Xem confidence score | Analysis |
| F1 | Sửa Epic / Task / Subtask 🔄 | Review |
| F5 | Duyệt action item | Review |
| F6 | Từ chối action item | Review |
| F8 | Thêm action item thủ công | Review |
| G1 | Push items lên Jira | Push |
| G2 | Xem trạng thái push real-time | Push |
| G3 | Retry khi push fail | Push |
| G4 | Xem link Jira issues | Push |
| H1 | Xem danh sách meetings | History |
| H4 | Xem chi tiết meeting cũ | History |
| H5 | Xóa meeting | History |

### 🟡 PHASE 2 — Enhancement (P1) — 20 use cases

| ID | Tên | Nhóm |
|----|-----|------|
| A7 | Đổi mật khẩu | Auth |
| A11 | Đồng ý điều khoản trước đăng ký ➕ | Auth |
| B3 | Xem hướng dẫn lấy Jira API token | Settings |
| B5 | Chọn ngôn ngữ transcription ⬇️ | Settings |
| B6 | Chọn tab/app để ghi âm 🔄⬇️ | Settings |
| B7 | Xem usage hiện tại | Settings |
| C5 | Pause recording | Input |
| C6 | Resume recording | Input |
| C10 | Hủy pipeline đang chạy | Input |
| D7 | Re-run transcription | Transcript |
| D8 | Tải xuống transcript (txt/srt) | Transcript |
| E5 | Xem parking lot | Analysis |
| E8 | Xem context (transcript) cho action item | Analysis |
| E9 | Ghi note thủ công ➕ | Analysis |
| E11 | AI dùng cả note + transcript ➕ | Analysis |
| F2 | Gán/sửa assignee (với mapping speaker→Jira) ⬇️ | Review |
| F7 | Bulk approve | Review |
| G5 | Override default Jira project | Push |
| H6 | Re-push meeting cũ | History |
| H7 | Export với template + preview 🔄 | History |

### 🔵 PHASE 3 — Future (P2) — 13 use cases

| ID | Tên | Nhóm |
|----|-----|------|
| A9 | Cập nhật profile (avatar) | Auth |
| A10 | Xóa tài khoản (GDPR) ⬇️ | Auth |
| B8 | Quản lý subscription/billing | Settings |
| D9 | Search trong transcript | Transcript |
| E7 | Re-run analysis với prompt khác | Analysis |
| E10 | Note templates ➕ | Analysis |
| F10 | Filter items theo confidence ⬇️ | Review |
| F11 | Drag-drop tasks giữa Epics | Review |
| G7 | Pull existing Jira tasks (check duplicate) | Push |
| G8 | Bidirectional sync (update existing tasks) | Push |
| H2 | Search meetings ⬇️ | History |
| H3 | Filter meetings theo status ⬇️ | History |
| H8 | Bulk export | History |