# MeetAstro Phase 1 MVP — Use Case Diagrams

> Split into 4 journey-based diagrams for readability.

---

## Diagram 1 — Setup Journey

**Authentication + Settings (10 use cases)**

**Actor:** User

### A. Authentication

| Use Case | ID |
|---|---|
| Đăng ký email/pass | A1 |
| Đăng ký Google | A2 |
| Xác thực email | A3 |
| Đăng nhập email/pass | A4 |
| Đăng nhập Google | A5 |
| Quên mật khẩu | A6 |
| Đăng xuất | A8 |

### B. Settings

| Use Case | ID |
|---|---|
| Cấu hình Jira | B1 |
| Test Jira connection | B2 |
| Cấu hình OpenAI key | B4 |

### Relationships

| From | To | Type |
|---|---|---|
| User | A1, A2, A4, A5, A6, A8, B1, B4 | association |
| A1 | A3 | `<<include>>` |
| A2 | A3 | `<<include>>` |
| B1 | B2 | `<<extend>>` |

```
User ──→ (A1) Đăng ký email/pass ──[include]──→ (A3) Xác thực email
User ──→ (A2) Đăng ký Google    ──[include]──→ (A3) Xác thực email
User ──→ (A4) Đăng nhập email/pass
User ──→ (A5) Đăng nhập Google
User ──→ (A6) Quên mật khẩu
User ──→ (A8) Đăng xuất
User ──→ (B1) Cấu hình Jira     ──[extend]───→ (B2) Test Jira connection
User ──→ (B4) Cấu hình OpenAI key
```

---

## Diagram 2 — Capture Journey

**Meeting Input + Transcript (11 use cases)**

**Actor:** User

### C. Meeting Input

| Use Case | ID |
|---|---|
| Tạo meeting | C1 |
| Upload audio file | C2 |
| Upload video file | C3 |
| Bắt đầu recording | C4 |
| Dừng recording | C7 |
| Xem progress pipeline | C9 |

### D. Transcript

| Use Case | ID |
|---|---|
| Xem transcript streaming | D1 |
| Xem transcript hoàn chỉnh | D2 |
| Xem diarization | D3 |
| Đổi tên/màu speaker | D4 |
| Sửa nội dung transcript | D5 |

### Relationships

| From | To | Type |
|---|---|---|
| User | C1, C2, C3, C4, C7, C9, D1, D2, D4, D5 | association |
| C2 | C9 | `<<extend>>` |
| C3 | C9 | `<<extend>>` |
| C7 | C9 | `<<extend>>` |
| D2 | D3 | `<<include>>` |

```
User ──→ (C1) Tạo meeting
User ──→ (C2) Upload audio file  ──[extend]───→ (C9) Xem progress pipeline
User ──→ (C3) Upload video file  ──[extend]───→ (C9) Xem progress pipeline
User ──→ (C4) Bắt đầu recording
User ──→ (C7) Dừng recording    ──[extend]───→ (C9) Xem progress pipeline
User ──→ (C9) Xem progress pipeline
User ──→ (D1) Xem transcript streaming
User ──→ (D2) Xem transcript hoàn chỉnh ──[include]──→ (D3) Xem diarization
User ──→ (D4) Đổi tên/màu speaker
User ──→ (D5) Sửa nội dung transcript
```

---

## Diagram 3 — Analyze Journey

**Analysis + Review (9 use cases)**

**Actor:** User

### E. Analysis

| Use Case | ID |
|---|---|
| Trigger analysis | E1 |
| Xem meeting summary | E2 |
| Xem key decisions | E4 |
| Xem action items tree | E3 |
| Xem confidence score | E6 |

### F. Review

| Use Case | ID |
|---|---|
| Sửa Epic/Task/Subtask | F1 |
| Duyệt action item | F5 |
| Từ chối action item | F6 |
| Thêm action item thủ công | F8 |

### Relationships

| From | To | Type |
|---|---|---|
| User | E1, E2, E4, E3, E6, F1, F5, F6, F8 | association |
| E1 | E2 | `<<include>>` |
| E1 | E4 | `<<include>>` |
| E1 | E3 | `<<include>>` |
| E1 | E6 | `<<include>>` |

```
User ──→ (E1) Trigger analysis ──[include]──→ (E2) Xem meeting summary
                               ──[include]──→ (E4) Xem key decisions
                               ──[include]──→ (E3) Xem action items tree
                               ──[include]──→ (E6) Xem confidence score
User ──→ (F1) Sửa Epic/Task/Subtask
User ──→ (F5) Duyệt action item
User ──→ (F6) Từ chối action item
User ──→ (F8) Thêm action item thủ công
```

---

## Diagram 4 — Deliver Journey

**Push to Jira + History (7 use cases)**

**Actor:** User

### G. Push to Jira

| Use Case | ID |
|---|---|
| Push items lên Jira | G1 |
| Xem trạng thái push | G2 |
| Retry khi push fail | G3 |
| Xem link Jira issues | G4 |

### H. History

| Use Case | ID |
|---|---|
| Xem danh sách meetings | H1 |
| Xem chi tiết meeting | H4 |
| Xóa meeting | H5 |

### Relationships

| From | To | Type |
|---|---|---|
| User | G1, G2, G3, G4, H1, H4, H5 | association |
| G1 | G2 | `<<include>>` |
| G1 | G4 | `<<include>>` |
| G2 | G3 | `<<extend>>` |
| H1 | H4 | `<<extend>>` |
| H1 | H5 | `<<extend>>` |

```
User ──→ (G1) Push items lên Jira ──[include]──→ (G2) Xem trạng thái push ──[extend]──→ (G3) Retry khi push fail
                                  ──[include]──→ (G4) Xem link Jira issues
User ──→ (G2) Xem trạng thái push
User ──→ (G3) Retry khi push fail
User ──→ (G4) Xem link Jira issues
User ──→ (H1) Xem danh sách meetings ──[extend]──→ (H4) Xem chi tiết meeting
                                      ──[extend]──→ (H5) Xóa meeting
User ──→ (H4) Xem chi tiết meeting
User ──→ (H5) Xóa meeting
```

---

## Summary

| Journey | Packages | Use Cases |
|---|---|---|
| Setup | A. Authentication, B. Settings | 10 |
| Capture | C. Meeting Input, D. Transcript | 11 |
| Analyze | E. Analysis, F. Review | 9 |
| Deliver | G. Push to Jira, H. History | 7 |
| **Total** | **8 packages** | **37** |

### Relationship Legend

| Symbol | Meaning |
|---|---|
| `──→` | Association (actor triggers use case) |
| `[include]` | `<<include>>` — base use case always invokes the included use case |
| `[extend]` | `<<extend>>` — extension use case optionally extends the base |
