Quy trình đọc hiểu Project AI Meeting Assistant                                                               
                                                                                                                
  Giai đoạn 1: Tổng quan (30 phút)                                                                              
   
  1. README.md                          → Mục đích, cách cài đặt, chạy project                                  
  2. CLAUDE.md                          → Architecture, tech stack, workflow, rules
  3. docs/INDEX.md                      → Bản đồ documentation
  4. docs/GLOSSARY.md                   → Thuật ngữ (Epic, Task, Subtask, Review Item)

  Kết quả: Hiểu project làm gì, flow từ audio → transcript → analysis → Jira.

  ---
  Giai đoạn 2: Data Contracts (20 phút)

  5. src/schema.py                      → Pydantic models: MeetingAnalysis, Epic, Task, Subtask
  6. src/db/models.py                   → ORM models: Meeting, Transcript, AnalysisResult, ReviewItem
  7. docs/technical/database-schema.md  → ERD, quan hệ giữa các bảng

  Kết quả: Hiểu cấu trúc dữ liệu xuyên suốt hệ thống.

  ---
  Giai đoạn 3: Configuration (15 phút)

  8. .env.example                       → Tất cả biến môi trường cần thiết
  9. src/config.py                      → Settings class, cách load config
  10. src/db/base.py                    → Database connection setup

  Kết quả: Hiểu cách cấu hình và kết nối các service.

  ---
  Giai đoạn 4: API Layer (30 phút)

  11. src/api/main.py                   → FastAPI app factory, middleware, lifespan
  12. src/api/deps.py                   → Dependencies (DB session, auth)
  13. src/api/rate_limit.py             → Rate limiting setup

  Routers (đọc theo thứ tự workflow):
  14. src/api/routers/meetings.py       → CRUD meetings, upload audio
  15. src/api/routers/transcriptions.py → Trigger transcription
  16. src/api/routers/analysis.py       → Trigger GPT-4o analysis
  17. src/api/routers/reviews.py        → Human-in-the-loop review
  18. src/api/routers/jira.py           → Push approved items to Jira
  19. src/api/routers/exports.py        → Export MD/JSON/CSV
  20. src/api/routers/settings.py       → Provider config management

  21. docs/technical/api-reference.md   → API documentation đầy đủ

  Kết quả: Hiểu tất cả endpoints và request/response format.

  ---
  Giai đoạn 5: Providers - External APIs (25 phút)

  22. src/providers/base_transcriber.py      → ABC cho transcription
  23. src/providers/openai_transcriber.py    → Whisper API implementation
  24. src/providers/openai_diarize_transcriber.py → Whisper + speaker diarization

  25. src/providers/base_analyzer.py         → ABC cho analysis
  26. src/providers/openai_analyzer.py       → GPT-4o structured output

  27. src/prompts/extract_action_items.md    → Prompt template cho extraction

  Kết quả: Hiểu cách gọi OpenAI APIs và strategy pattern.

  ---
  Giai đoạn 6: Services - Business Logic (30 phút)

  28. src/services/transcription_service.py  → Orchestrate transcription flow
  29. src/services/analysis_service.py       → Orchestrate GPT-4o analysis
  30. src/services/summarization_service.py  → Generate meeting summary
  31. src/services/validation_service.py     → Cross-validate AI output với rules
  32. src/services/jira_service.py           → Orchestrate Jira push
  33. src/services/recording_service.py      → Audio recording management
  34. src/services/cleanup_service.py        → Expired data cleanup

  Kết quả: Hiểu business logic và orchestration.

  ---
  Giai đoạn 7: Modules - Integration (20 phút)

  35. src/modules/jira_client.py        → Jira REST API v3 client
  36. src/modules/credential_vault.py   → Fernet encryption cho secrets
  37. src/modules/audio_recorder.py     → PyAudio recording
  38. src/modules/exporter.py           → Export to MD/JSON/CSV

  Kết quả: Hiểu các integration và utility modules.

  ---
  Giai đoạn 8: Async Workers (25 phút)

  39. src/workers/celery_app.py              → Celery config, queues
  40. src/workers/tasks/transcribe_task.py   → Async transcription task
  41. src/workers/tasks/analyze_task.py      → Async analysis task
  42. src/workers/tasks/jira_push_task.py    → Async Jira push task
  43. src/workers/tasks/cleanup_task.py      → Scheduled cleanup task

  44. docs/technical/celery-tasks.md         → Task documentation

  Kết quả: Hiểu async pipeline và retry logic.

  ---
  Giai đoạn 9: Frontend - Flet Desktop (25 phút)

  45. frontend/main.py                  → Entry point
  46. frontend/app.py                   → App routing, layout
  47. frontend/config.py                → Frontend config
  48. frontend/core/state.py            → AppState dataclass
  49. frontend/core/http_backend.py     → HTTP client singleton

  Views (theo workflow):
  50. frontend/views/dashboard_view.py  → Landing page
  51. frontend/views/new_meeting_view.py → Record/upload audio
  52. frontend/views/results_view.py    → View transcript + analysis
  53. frontend/views/review_view.py     → Human-in-the-loop approve/reject
  54. frontend/views/history_view.py    → Past meetings
  55. frontend/views/settings_view.py   → Provider configuration

  56. frontend/components/sidebar.py    → Navigation
  57. frontend/components/topbar.py     → Header

  58. docs/technical/frontend.md        → Frontend architecture

  Kết quả: Hiểu Flet app structure và views.

  ---
  Giai đoạn 10: Database Layer (15 phút)

  59. src/db/crud/meeting_crud.py       → Meeting CRUD operations
  60. src/db/crud/review_crud.py        → ReviewItem CRUD (approve/reject)
  61. src/db/crud/provider_crud.py      → ProviderConfig CRUD
  62. src/db/migrations/versions/       → Alembic migrations

  Kết quả: Hiểu data access patterns.

  ---
  Giai đoạn 11: Tests - Examples (20 phút)

  63. tests/test_schema.py                   → Schema validation examples
  64. tests/test_openai_transcriber.py       → Mock OpenAI calls
  65. tests/test_openai_analyzer.py          → Mock GPT-4o responses
  66. tests/test_jira_client.py              → Mock Jira API
  67. tests/test_integration.py              → End-to-end flow tests

  Kết quả: Hiểu cách mock external APIs và test patterns.

  ---
  Giai đoạn 12: Security & Operations (10 phút)

  68. docs/technical/security.md        → Security best practices
  69. docs/CONTRIBUTING.md              → Development guidelines
  70. docker-compose.yml                → Production deployment

  Kết quả: Hiểu security và deployment.

  ---
  📊 Tóm tắt theo thời gian

  ┌───────────┬───────────┬────────────────────────┐
  │ Giai đoạn │ Thời gian │         Focus          │
  ├───────────┼───────────┼────────────────────────┤
  │ 1-2       │ 50 phút   │ Overview + Data Models │
  ├───────────┼───────────┼────────────────────────┤
  │ 3-4       │ 45 phút   │ Config + API           │
  ├───────────┼───────────┼────────────────────────┤
  │ 5-6       │ 55 phút   │ Providers + Services   │
  ├───────────┼───────────┼────────────────────────┤
  │ 7-8       │ 45 phút   │ Modules + Workers      │
  ├───────────┼───────────┼────────────────────────┤
  │ 9-10      │ 40 phút   │ Frontend + DB          │
  ├───────────┼───────────┼────────────────────────┤
  │ 11-12     │ 30 phút   │ Tests + Security       │
  └───────────┴───────────┴────────────────────────┘

  Tổng: ~4-5 giờ để đọc hiểu toàn bộ codebase.

  ---
  🎯 Quick Path (nếu chỉ có 1 giờ)

  README.md → CLAUDE.md → src/schema.py → src/api/main.py →
  src/services/analysis_service.py → src/workers/tasks/analyze_task.py →
  frontend/views/review_view.py

  Đây là critical path của workflow chính: Audio → Analysis → Review → Jira.