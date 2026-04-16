# Jira Upload Flow

Mô tả chi tiết luồng đẩy action items từ app lên Jira, bao gồm điểm vào UI, mapping payload, chế độ STUB, và các rủi ro hiện tại.

---

## 1. Điểm vào trong ứng dụng

Luồng Jira được gọi từ Streamlit UI tại `src/app.py` thông qua service layer:

- Action bar chỉ hiển thị khi có `st.session_state.analysis`
- Người dùng bấm nút `🚀 Đẩy lên Jira`
- App gọi `push_analysis_to_jira(analysis)` trong `src/services/jira_service.py`
- Service tạo `JiraClient()` (nếu chưa truyền sẵn client)
- Service lặp `Epic -> Task -> Subtask` và gọi lần lượt:
  - `create_epic(epic)`
  - `create_task(task, epic_key)`
  - `create_subtask(subtask, task_key)`

Tức là: flow upload Jira đã được nối vào runtime qua UI và đã tách orchestration khỏi UI.

---

## 2. Trình tự thực thi (runtime sequence)

```text
User click "🚀 Đẩy lên Jira"
  -> Streamlit spinner: "Đang đẩy lên Jira..."
  -> jira_result = push_analysis_to_jira(analysis)
  -> jira_service tạo JiraClient() nếu cần
  -> jira_service for each epic in analysis.epics:
       epic_key = client.create_epic(epic)
       for each task in epic.tasks:
         task_key = client.create_task(task, epic_key)
         for each subtask in task.subtasks:
           client.create_subtask(subtask, task_key)
  -> if jira_result.is_stub:
       show warning "Jira STUB mode"
     else:
       show success with summary counts + epic keys
  -> any exception:
       show st.error("Lỗi Jira: ...")
```

Thứ tự phụ thuộc parent-child:
- Epic phải tạo trước để lấy `epic_key`
- Task tạo sau để tham chiếu Epic
- Subtask tạo cuối để tham chiếu Task

---

## 3. Cơ chế STUB mode

`JiraClient` tự vào STUB mode khi thiếu một trong các biến môi trường:

- `JIRA_BASE_URL`
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`
- `JIRA_PROJECT_KEY`

Hành vi STUB:
- Không gọi HTTP tới Jira
- Trả key giả `STUB-001`
- UI hiển thị warning thay vì success thật

Ý nghĩa:
- Team có thể demo flow end-to-end mà không cần Jira thật
- Có thể test luồng UI mà không tạo ticket rác

---

## 4. Mapping dữ liệu sang Jira payload

Mỗi request dùng endpoint:
- `POST /rest/api/3/issue`

Auth:
- Basic Auth với `JIRA_EMAIL` + `JIRA_API_TOKEN`

### 4.1 Epic payload

```json
{
  "fields": {
    "project": { "key": "<JIRA_PROJECT_KEY>" },
    "summary": "<epic.summary>",
    "description": {
      "type": "doc",
      "version": 1,
      "content": [{"type":"paragraph","content":[{"type":"text","text":"<epic.description>"}]}]
    },
    "issuetype": { "name": "Epic" }
  }
}
```

### 4.2 Task payload

```json
{
  "fields": {
    "project": { "key": "<JIRA_PROJECT_KEY>" },
    "summary": "<task.summary>",
    "issuetype": { "name": "Task" },
    "parent": { "key": "<epic_key>" },
    "priority": { "name": "<task.priority.value>" },
    "duedate": "<task.deadline|bỏ qua nếu N/A hoặc TBD>",
    "assignee": { "name": "<task.assignee|bỏ qua nếu N/A hoặc TBD>" },
    "description": {
      "type": "doc",
      "version": 1,
      "content": [{"type":"paragraph","content":[{"type":"text","text":"<task.context>"}]}]
    }
  }
}
```

### 4.3 Subtask payload

```json
{
  "fields": {
    "project": { "key": "<JIRA_PROJECT_KEY>" },
    "summary": "<subtask.summary>",
    "issuetype": { "name": "Subtask" },
    "parent": { "key": "<task_key>" },
    "priority": { "name": "<subtask.priority.value>" },
    "duedate": "<subtask.deadline|bỏ qua nếu N/A hoặc TBD>",
    "assignee": { "name": "<subtask.assignee|bỏ qua nếu N/A hoặc TBD>" }
  }
}
```

### 4.4 Các lưu ý quan trọng về Payload trên Jira Cloud
- **Parent thay cho Epic Link:** Thay vì dùng `customfield_10xxx` để thiết lập cha con, Jira Cloud hiện sử dụng `parent: {"key": ...}` để liên kết Task vào Epic, và Subtask vào Task.
- **Xử lý giá trị trống:** Các trường `duedate` và `assignee` nếu nhận từ AI là "N/A", "TBD" hoặc "None" sẽ được module `jira_client.py` chủ động xóa khỏi payload để tránh lỗi `400 Bad Request` do sai format chuẩn của đối tượng Jira.
- **Assignee AccountId:** Hiện tại app đang map assignee qua field `"name"`. Đối với một số Jira Cloud API strict, có thể sẽ cần nâng cấp map sang `"accountId"`.

---

## 5. Error handling hiện tại

Trong `JiraClient._post`:
- Nếu response không OK: log status code + response text
- Sau đó `raise_for_status()` để ném exception

Ở UI:
- Toàn bộ block push Jira được bọc `try/except`
- Có lỗi bất kỳ sẽ hiện `st.error("Lỗi Jira: ...")`

Lưu ý quan trọng:
- Không có rollback khi fail giữa chừng
- Có thể tạo một phần dữ liệu trên Jira (partial success)

---

## 6. Điểm mạnh và giới hạn của flow hiện tại

### Điểm mạnh
- Luồng đã tích hợp vào UI qua service layer, bấm là chạy
- Có STUB mode để test nhanh khi thiếu credentials
- Có log lỗi HTTP giúp debug payload/field mismatch
- Có test cho stub mode và payload chính

### Giới hạn/rủi ro
- Chưa có idempotency, bấm lại có thể tạo duplicate issues
- `customfield_10014` phụ thuộc cấu hình Jira instance
- `assignee.name` có thể không hợp lệ với Jira Cloud mới (nhiều instance cần `accountId`)
- Không có rollback khi tạo Epic thành công nhưng Task/Subtask fail

---

## 7. Checklist vận hành Jira thật

1. Điền đủ 4 biến `JIRA_*` trong `.env`
2. Đảm bảo issue types tồn tại: `Epic`, `Task`, `Subtask`
3. Xác minh custom field Epic Link/Epic Name đúng ID cho instance hiện tại
4. Kiểm tra quyền account API token có quyền create issue trong project
5. Chạy thử với 1 transcript nhỏ trước khi dùng dữ liệu thật

---

## 8. Gợi ý nâng cấp (sau khi ổn định docs)

1. Trả về báo cáo chi tiết theo từng issue (`created`, `failed`, error message)
2. Thêm idempotency key (ví dụ hash theo meeting id + task summary)
3. Thêm chế độ dry-run hiển thị payload trước khi gửi thật
4. Chuẩn hóa mapping assignee cho Jira Cloud (`accountId`) và Jira Server/Data Center (`name`)
5. Bổ sung cơ chế rollback hoặc compensation khi fail giữa chừng
