# Cấu trúc Hệ thống Màn hình (Screen Navigation & Routing)

### 1. Phân chia Module & Components (Modules)

Hệ thống được chia thành 6 module chính, mỗi module chứa các loại component khác nhau (Screen, Modal, Process state, Action).

* **Authentication (Xác thực)**
    * `Login Page` (Screen): Trang đăng nhập.
    * `Register Page` (Screen): Trang đăng ký tài khoản.
    * `Forgot Password` (Screen): Trang quên mật khẩu.
    * `Reset Link Sent` (Screen): Trạng thái thông báo đã gửi link khôi phục.
* **Main Navigation (Điều hướng chính)**
    * `APP Node` (Root Component/Layout): Layout chính sau khi đăng nhập.
    * `New Meeting Page / Home` (Screen): Màn hình chính để bắt đầu phiên mới.
    * `History Page` (Screen): Màn hình lịch sử các cuộc họp.
    * `Settings Page` (Screen): Màn hình cấu hình (chứa cấu hình tích hợp Jira).
* **Upload Workflow (Luồng tải file)**
    * `Transcribing State` (Process): Trạng thái xử lý nền (Audio -> Text).
    * `Review Transcript` (Screen): Màn hình xem trước nội dung text trước khi phân tích.
    * `AI Analyzing State` (Process): Trạng thái AI đang phân tích (Tóm tắt & Tìm Action items).
* **Live Record Workflow (Luồng thu âm trực tiếp)**
    * `Live Recording Screen` (Screen): Màn hình thu âm chính.
    * `Mini Pop-up` (Modal): Cửa sổ nhỏ gọn (PIP) hiển thị Transcript & Task realtime khi app bị ẩn/thu nhỏ.
    * `Finalizing AI Processing` (Process): Trạng thái tổng hợp sau khi kết thúc thu âm.
* **Core Workspace / Meeting Detail (Không gian làm việc chính)**
    * `Meeting Detail Screen` (Screen): Giao diện chi tiết cuộc họp (chứa 3 tab chính).
        * *Tab 1: Summary* (Tóm tắt cuộc họp).
        * *Tab 2: Transcript* (Nội dung bóc băng - User có thể edit).
        * *Tab 3: Action Items* (Danh sách công việc).
* **Jira Sync Workflow (Luồng đồng bộ Jira)**
    * `Review Action Items` (Action/View): Xem lại các task đã tạo.
    * `Edit + Add Item` (Action/Modal): Sửa hoặc thêm task mới (Inline hoặc Modal).
    * `Approve` (Action): Xác nhận task (qua Checkbox).
    * `Push to Jira API` (Action): Đẩy dữ liệu sang Jira.
    * `Export Modal` (Modal): Hộp thoại xuất file (hỗ trợ MD, JSON, CSV).

---

## 2. Các luồng người dùng (User Journeys)

### 2.1 Luồng Xác thực (Auth Flow)
* **Khởi động** vào `Login Page`.
* Từ `Login Page` có thể chuyển qua lại với `Register Page`.
* Từ `Login Page` có thể đi tới `Forgot Password` ➔ Chuyển sang `Reset Link Sent` ➔ Quay lại `Login Page`.
* **Auth Success**: Từ `Login Page` đăng nhập thành công sẽ điều hướng vào `APP Node`.

### 2.2 Luồng Điều hướng Chính (Main Navigation Path)
* Từ `APP Node`, người dùng có thể truy cập 3 màn hình chính: `New Meeting Page` (Home), `History Page`, hoặc `Settings Page`.

### 2.3 Luồng 1: Tải file lên (Upload File Flow)
1.  Tại `New Meeting Page`, user chọn **Upload File**.
2.  Chuyển sang trạng thái `Transcribing State` (Audio -> Text).
3.  Khi thành công, chuyển đến `Review Transcript` để user kiểm tra.
4.  User bấm **Analyze** ➔ Chuyển sang trạng thái `AI Analyzing State`.
5.  Khi phân tích xong ➔ Điều hướng tới `Meeting Detail Screen`.

### 2.4 Luồng 2: Thu âm trực tiếp (Live Record Flow)
1.  Tại `New Meeting Page`, user chọn **Start Record** ➔ Mở `Live Recording Screen`.
2.  Nếu user **Minimize App** (Thu nhỏ app) ➔ Chuyển thành `Mini Pop-up` (chứa dữ liệu realtime).
3.  Từ `Mini Pop-up`, user **Maximize** (Phóng to) ➔ Quay lại `Live Recording Screen`.
4.  User chọn **Stop Record** (từ màn hình chính hoặc Mini Pop-up) ➔ Chuyển sang trạng thái `Finalizing AI Processing`.
5.  Khi hoàn tất ➔ Điều hướng tới `Meeting Detail Screen`.

### 2.5 Luồng Xem Lịch sử (History Revisit Flow)
* Tại `History Page`, user chọn một cuộc họp trong quá khứ ➔ Điều hướng trực tiếp tới `Meeting Detail Screen`.

### 2.6 Luồng Xử lý Action Items & Đồng bộ Jira (Workspace & Jira Sync Flow)
* Tại `Meeting Detail Screen`, user truy cập **Tab 3: Action Items**.
* **Chỉnh sửa**: Từ danh sách Action Items ➔ Vào bước `Review` ➔ Nếu cần thay đổi, mở `Edit + Add Item` ➔ Quay lại `Review`.
* **Đồng bộ Jira**: Người dùng chọn các items (checkboxes) ở bước `Review` ➔ Chuyển qua trạng thái `Approve` ➔ Trigger action `Push to Jira API`.
* **Xuất File**: Từ **Tab 3: Action Items**, bấm **Export** ➔ Mở `Export Modal` để tải file (MD/JSON/CSV).
