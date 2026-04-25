# Docs — AI Meeting Assistant

Project documentation organized by audience.

---

## Structure

```
docs/
├── INDEX.md                    <- You are here
├── llms.txt                    <- Context for AI Agents (auto-loaded)
├── CONTRIBUTING.md             <- Contributor guidelines
├── GLOSSARY.md                 <- Terms and definitions
│
├── product/                    <- Product — PM & Stakeholders
│   ├── canvas.md               <- AI Product Canvas (Value / Trust / Feasibility)
│   ├── spec.md                 <- Product Spec (User Stories, Eval, ROI, Failure Modes)
│   └── roadmap.md              <- Roadmap & Milestones
│
├── technical/                  <- Technical — Developers & AI Agents
│   ├── architecture.md         <- System architecture + module map
│   ├── data-flow.md            <- End-to-end data flow
│   ├── api-reference.md        <- REST endpoints + data models
│   ├── database-schema.md      <- PostgreSQL schema + migrations
│   ├── celery-tasks.md         <- Celery background tasks
│   ├── frontend.md             <- Flet desktop app docs
│   ├── security.md             <- Security considerations
│   ├── deployment.md           <- Setup, installation, deployment
│   └── workflows/              <- Detailed workflow documentation
│       ├── audio-processing.md <- Audio processing & Diarization
│       ├── llm-analysis.md     <- LLM analysis & Multi-stage agents
│       ├── validation-logic.md <- Cross-validation scoring algorithm
│       └── jira-upload-flow.md <- Jira upload flow
│
└── evaluation/                 <- Evaluation — QA & Review
    ├── eval-metrics.md         <- Metrics, thresholds, red flags
    └── test-plan.md            <- Test strategy & checklist
```

---

## Who Reads What?

| Role | Start With | Then Read |
|------|------------|-----------|
| **PM / Stakeholder** | `product/canvas.md` -> `product/spec.md` | `product/roadmap.md` |
| **Developer** | `technical/architecture.md` -> `technical/api-reference.md` | `technical/data-flow.md`, `technical/database-schema.md`, `technical/workflows/*`, `technical/deployment.md` |
| **AI Agent** | `llms.txt` (auto-loaded) | `technical/architecture.md`, `technical/api-reference.md` |
| **QA / Reviewer** | `evaluation/eval-metrics.md` -> `evaluation/test-plan.md` | `product/spec.md` (failure modes) |
| **New Contributor** | `CONTRIBUTING.md` | `technical/architecture.md`, `technical/security.md` |

---

## Quick Links

### Getting Started
- [README.md](../README.md) — Quick start guide
- [CONTRIBUTING.md](CONTRIBUTING.md) — How to contribute
- [Deployment Guide](technical/deployment.md) — Setup & installation

### Architecture
- [System Architecture](technical/architecture.md) — High-level overview
- [Data Flow](technical/data-flow.md) — Pipeline diagram
- [Database Schema](technical/database-schema.md) — PostgreSQL tables
- [API Reference](technical/api-reference.md) — REST endpoints
- [Celery Tasks](technical/celery-tasks.md) — Background task processing

### Workflows
- [Audio Processing](technical/workflows/audio-processing.md) — Transcription & diarization
- [LLM Analysis](technical/workflows/llm-analysis.md) — GPT-4o extraction
- [Validation Logic](technical/workflows/validation-logic.md) — Confidence scoring
- [Jira Upload](technical/workflows/jira-upload-flow.md) — Jira integration

### Product
- [AI Product Canvas](product/canvas.md) — Value, Trust, Feasibility
- [Product Spec](product/spec.md) — User stories, metrics, failure modes
- [Roadmap](product/roadmap.md) — Milestones & phases

### Quality
- [Evaluation Metrics](evaluation/eval-metrics.md) — AI quality metrics
- [Test Plan](evaluation/test-plan.md) — Test strategy

### Security
- [Security Guide](technical/security.md) — Security considerations

---

## Documentation Conventions

1. **Language**: Vietnamese for descriptions, English for technical terms
2. **Updates**: Update docs when changing code in the same PR
3. **Cross-reference**: Use relative links (`[Architecture](technical/architecture.md)`)
4. **Uncertainty markers**: 
   - `[?]` for unconfirmed information
   - `[TBD]` for incomplete sections

---

## File Descriptions

| File | Purpose |
|------|---------|
| `INDEX.md` | This documentation index |
| `llms.txt` | Structured context for AI coding agents |
| `CONTRIBUTING.md` | Contributor guidelines, code style, PR process |
| `product/canvas.md` | AI Product Canvas — Value, Trust, Feasibility analysis |
| `product/spec.md` | Product specification with user stories, metrics, failure modes |
| `product/roadmap.md` | Project phases, milestones, dependency graph |
| `technical/architecture.md` | System architecture, layer diagram, module map |
| `technical/api-reference.md` | REST API endpoints, Pydantic models, provider interfaces |
| `technical/database-schema.md` | PostgreSQL schema, table definitions, CRUD operations |
| `technical/celery-tasks.md` | Celery background tasks, retry logic, monitoring |
| `technical/data-flow.md` | End-to-end data pipeline, transformations, state management |
| `technical/frontend.md` | Flet desktop app structure, views, state management |
| `technical/security.md` | Security measures, credential vault, threat mitigations |
| `technical/deployment.md` | Installation, Docker setup, production deployment |
| `technical/workflows/audio-processing.md` | Audio capture, Whisper API, diarization |
| `technical/workflows/llm-analysis.md` | GPT-4o analysis, JSON mode, multi-stage agents |
| `technical/workflows/validation-logic.md` | Cross-validation algorithm, confidence scoring |
| `technical/workflows/jira-upload-flow.md` | Jira REST API integration, stub mode |
| `evaluation/eval-metrics.md` | Quality metrics, thresholds, kill criteria |
| `evaluation/test-plan.md` | Test strategy, unit/integration/smoke tests |
