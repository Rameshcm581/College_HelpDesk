# Phased Implementation Roadmap & Acceptance Criteria
**Document Version:** 2.0 (Post-Audit Verified)  
**Status:** All 8 Engineering Phases Complete; Pre-Launch Operational Checklist Pending  

---

## 1. Roadmap Overview & Timeline

The implementation of the **College AI Help Desk** is structured across eight disciplined phases.

```mermaid
gantt
    title College AI Help Desk Engineering Roadmap
    dateFormat  YYYY-MM-DD
    section Core Infrastructure
    Phase 1: Environment & Foundation      :done, p1, 2026-10-23, 3d
    Phase 2: Ingestion & OCR Pipeline     :done, p2, 2026-10-26, 5d
    section RAG & Public Chat
    Phase 3: Hybrid RAG & Anti-Hallucination :done, p3, after p2, 5d
    Phase 4: Support Ticketing & Email       :done, p4, after p3, 3d
    section Portals & Clients
    Phase 5: Admin Dashboard & RBAC          :done, p5, after p4, 6d
    Phase 6: Embeddable Widget (Shadow DOM)  :done, p6, after p5, 4d
    section QA & Delivery
    Phase 7: Testing, RAG Benchmark & Audit  :done, p7, after p6, 4d
    Phase 8: Production Containerization     :done, p8, after p7, 2d
```

---

## 2. Phase-by-Phase Completion & Acceptance Criteria

### Phase 1: Environment, Database & Foundation [COMPLETED]
- [x] Service layout matches ARC100 conventions (`Services/HelpdeskService/` with `configs/`, `models/`, `resources/`, `routes/`, `tests/`).
- [x] Docker Compose stack with PostgreSQL 16 (`pgvector`), Redis 7, and FastAPI.
- [x] Alembic migrations with HNSW and GIN full-text search indexes.
- [x] Async connection pooling via SQLAlchemy 2.0.

### Phase 2: Document Ingestion & RAG Vertical Slice [COMPLETED]
- [x] Page-by-page PDF text extraction preserving 1-based page numbers.
- [x] Scanned page detection with Tesseract OCR fallback (supporting Tamil & English).
- [x] 1536-dimensional unit embeddings stored in pgvector.
- [x] Gated retrieval ($\tau \ge 0.72$) and safe refusal fallback.

### Phase 3: Hybrid Search & Anti-Hallucination RAG Engine [COMPLETED]
- [x] Hybrid search combining dense semantic search and sparse PostgreSQL tsvector search.
- [x] Metadata pre-filtering: Academic Year, Department, Document Type, Version, and Validity dates.
- [x] Bilingual English, Tamil, and Tanglish retrieval.
- [x] Benchmark evaluation over 115 test queries (Hit@1: 88.0%, Hit@3: 100%, MRR: 0.9383).

### Phase 4: Support Ticketing System & Notifications [COMPLETED]
- [x] Public ticket creation with automatic routing to Admissions, Fees, Hostel, Examinations, Scholarships, Placements, or General Administration.
- [x] Zero-password visitor OTP verification for ticket tracking.
- [x] Staff ticket lifecycle (Open $\to$ In Progress $\to$ Resolved $\to$ Closed), SLA calculation, and overdue indicators.
- [x] Modular email notification provider interface with mock mode for testing.

### Phase 5: Admin Dashboard & RBAC [COMPLETED]
- [x] Secure staff authentication using Argon2id password hashing and short-lived JWT tokens.
- [x] Role-Based Access Control enforcing `SUPER_ADMIN`, `ADMIN`, `CONTENT_APPROVER`, `DEPARTMENT_STAFF`, and `VIEWER`.
- [x] Department boundary isolation ensuring staff cannot view or download other departments' documents or tickets.
- [x] Document version management, approval workflow, and knowledge gap triage.

### Phase 6: Embeddable Website Chatbot [COMPLETED]
- [x] Floating toggle button, animated panel, streaming response reader.
- [x] Verified citation pills with document title, version, and page number.
- [x] English / Tamil language switcher with bilingual suggested questions.
- [x] Lightweight loader snippet (`college-helpdesk.js`) and iframe embed option.

### Phase 7: Testing, RAG Benchmark & Audit [COMPLETED]
- [x] 58 backend pytest unit and integration tests passing.
- [x] 18 frontend vitest component and workflow tests passing.
- [x] TypeScript compiler check passing with 0 errors.
- [x] Comprehensive 25-area production-readiness security and architecture audit completed.

### Phase 8: Production Hardening & Containerization [COMPLETED]
- [x] Multi-stage non-root `Dockerfile` created for backend service.
- [x] Prompt injection defenses with XML delimiter isolation (`<user_inquiry>`) and constitutional refusal directives.
- [x] Rate limiting updated with `X-Forwarded-For` proxy IP extraction and memory eviction.
- [x] PII redaction updated to mask 10-digit, 5+5 Indian mobile numbers and email addresses in server logs.
- [x] Database disaster recovery drill verified (`scripts/backup.sh` and `scripts/restore_drill.sh`).

---

## 3. Pre-Launch Production Operational Checklist (Remaining Items)

Before switching DNS traffic to production:

| Priority | Action Item | Responsible Party | Notes |
| :---: | :--- | :--- | :--- |
| **P1** | **Supply Production Secrets in `.env`** | College DevOps | Replace default `SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD` with 32+ character random strings. |
| **P1** | **Configure Production OpenAI API Key & Spending Quota** | College IT Admin | Set `OPENAI_API_KEY` with hard monthly spending limit ($50-$200) in OpenAI dashboard to prevent cost spikes. |
| **P1** | **Configure Institutional SMTP Credentials** | College System Admin | Populate `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` for live email notifications. |
| **P2** | **Deploy Nginx with Let's Encrypt SSL** | College DevOps | Point public domain `helpdesk.college.edu` to server IP with HTTP $\to$ HTTPS redirect. |
| **P2** | **Schedule Nightly Backup Cron** | College System Admin | Add `0 2 * * * /path/to/scripts/backup.sh` to root crontab. |
| **P3** | **Embed Loader Snippet on College Portal** | College Webmaster | Add `<script src="https://helpdesk.college.edu/widget/college-helpdesk.js"></script>` to college portal header. |
