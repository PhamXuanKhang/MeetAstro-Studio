# Database Schema Architecture: MeetSync AI

## 1. Entity Relationships Overview
*   **`AUTH_USERS`** 1 ── 1 **`PROFILES`** (extends auth)
*   **`PROFILES`** 1 ── N **`PROVIDER_CONFIGS`** (configures)
*   **`PROFILES`** 1 ── N **`MEETINGS`** (owns)
*   **`MEETINGS`** 1 ── 1 **`ANALYSIS_RESULTS`** (has analysis)
*   **`MEETINGS`** 1 ── N **`TRANSCRIPT_SEGMENTS`** (has segments)
*   **`MEETINGS`** 1 ── N **`ACTION_ITEMS`** (generates tasks)
*   **`ACTION_ITEMS`** 1 ── N **`ACTION_ITEMS`** (parent_id: Epic/Task/Subtask)

---

## 2. Entities Detail

### 2.1. AUTH_USERS
Bảng mặc định do Supabase quản lý để xử lý Authentication.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | uuid | Primary Key | Supabase managed |
| `email` | string | | |

### 2.2. PROFILES
Mở rộng thông tin người dùng từ `auth.users`.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | uuid | PK, FK | FK -> `auth.users.id` |
| `full_name` | text | | |
| `avatar_url` | text | | |
| `created_at` | timestamp | | |

### 2.3. PROVIDER_CONFIGS
Lưu trữ cấu hình tích hợp với các nền tảng bên thứ ba.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | uuid | Primary Key | |
| `user_id` | uuid | Foreign Key | FK -> `profiles.id` |
| `provider_name`| string | | e.g., jira, openai, linear |
| `api_key` | text | | Protected by RLS |
| `config_data` | jsonb | | Store domain, email, default keys... |
| `created_at` | timestamp | | |
| `updated_at` | timestamp | | |

### 2.4. MEETINGS
Lưu trữ thông tin cốt lõi và metadata của từng cuộc họp.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | uuid | Primary Key | |
| `user_id` | uuid | Foreign Key | FK -> `profiles.id` |
| `title` | text | | |
| `status` | string | | Enum: pending, transcribed, draft, approved, pushed, failed |
| `error_message` | text | | For AI/Whisper debug |
| `storage_provider`| string | | Enum: local, cloud |
| `audio_storage_path`| text | | |
| `audio_duration_seconds`| int | | |
| `created_at` | timestamp | | |
| `updated_at` | timestamp | | |

### 2.5. ANALYSIS_RESULTS
Chứa toàn bộ kết quả phân tích JSON trả về từ AI Model.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | uuid | Primary Key | |
| `meeting_id` | uuid | Foreign Key | FK -> `meetings.id` (1:1 relation) |
| `summary_text` | text | | |
| `key_decisions`| jsonb | | |
| `parking_lot` | jsonb | | |
| `raw_response` | jsonb | | Full GPT-4o response for debug |
| `ai_model` | string | | Track which model produced this |
| `input_tokens` | int | | |
| `output_tokens`| int | | |
| `created_at` | timestamp | | |

### 2.6. TRANSCRIPT_SEGMENTS
Quản lý các đoạn hội thoại bóc băng chi tiết.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | uuid | Primary Key | |
| `meeting_id` | uuid | Foreign Key | FK -> `meetings.id` |
| `speaker` | text | | e.g., Speaker A |
| `start_time` | float | | |
| `end_time` | float | | |
| `content` | text | | |

### 2.7. ACTION_ITEMS
Lõi của hệ thống, quản lý công việc và đồng bộ trạng thái với Jira.
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | uuid | Primary Key | |
| `meeting_id` | uuid | Foreign Key | FK -> `meetings.id` |
| `parent_id` | uuid | Foreign Key | Self-referencing for hierarchy |
| `item_type` | string | | Enum: epic, task, subtask |
| `title` | text | | |
| `description` | text | | |
| `assignee` | text | | |
| `deadline` | date | | AI extracted, user can edit |
| `priority` | string | | Enum: critical, high, medium, low |
| `context` | text | | Đoạn transcript được trích để extract item này |
| `confidence_score`| float | | Lưu độ tin cậy của task đó |
| `review_status`| string | | Enum: draft, edited, approved, rejected |
| `is_selected` | boolean | | UI Checkbox state |
| `sync_status` | string | | Enum: pending, synced, failed |
| `sync_error` | text | | Lỗi từ Jira API |
| `jira_issue_key`| text | | e.g., DEV-123 |
| `jira_issue_url`| text | | |
| `created_at` | timestamp | | |
| `updated_at` | timestamp | | |