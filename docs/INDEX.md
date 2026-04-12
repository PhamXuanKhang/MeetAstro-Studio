# Docs — AI Meeting Assistant

Hệ thống tài liệu dự án, tổ chức theo 3 nhóm chính.

---

## Cấu trúc

```
docs/
├── INDEX.md                    ← Bạn đang ở đây
├── llms.txt                    ← Context tổng hợp cho AI Agents
│
├── product/                    ← Product — PM & Stakeholders đọc
│   ├── canvas.md               ← AI Product Canvas (Value / Trust / Feasibility)
│   ├── spec.md                 ← Product Spec (User Stories, Eval, ROI, Failure Modes)
│   └── roadmap.md              ← Roadmap & Milestones
│
├── technical/                  ← Technical — Developers & AI Agents đọc
│   ├── architecture.md         ← System architecture + module map
│   ├── data-flow.md            ← Luồng dữ liệu end-to-end
│   ├── api-reference.md        ← Public interfaces & schemas
│   └── deployment.md           ← Setup, cài đặt, chạy app
│
└── evaluation/                 ← Evaluation — QA & Review đọc
    ├── eval-metrics.md         ← Metrics, thresholds, red flags
    └── test-plan.md            ← Test strategy & checklist
```

---

## Ai đọc gì?

| Vai trò | Đọc trước | Tham khảo thêm |
|---------|-----------|-----------------|
| **PM / Stakeholder** | `product/canvas.md` → `product/spec.md` | `product/roadmap.md` |
| **Developer** | `technical/architecture.md` → `technical/api-reference.md` | `technical/data-flow.md`, `technical/deployment.md` |
| **AI Agent** | `llms.txt` (auto-loaded) | `technical/architecture.md`, `technical/api-reference.md` |
| **QA / Reviewer** | `evaluation/eval-metrics.md` → `evaluation/test-plan.md` | `product/spec.md` (failure modes) |

---

## Quy ước viết tài liệu

1. **Ngôn ngữ**: Tiếng Việt cho mô tả, tiếng Anh cho thuật ngữ kỹ thuật
2. **Cập nhật**: Sửa code → cập nhật docs tương ứng trong cùng PR
3. **Cross-reference**: Dùng relative links (`[Architecture](technical/architecture.md)`)
4. **Đánh dấu giả thuyết**: `[?]` cho thông tin chưa xác nhận, `[TBD]` cho mục chưa hoàn thành
