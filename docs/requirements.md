# Requirements & System Specifications: College AI Help Desk

## 1. Executive Summary & Purpose
The **College AI Help Desk** is an enterprise-grade, multilingual (English & Tamil) conversational AI and support ticketing platform designed to serve prospective students, enrolled students, parents, and faculty. It integrates into any existing college web portal via a lightweight, zero-dependency embeddable widget while maintaining a completely isolated, role-based administrative portal for admissions, hostel, examinations, and accounts staff.

The system delivers verified, cited answers derived exclusively from college-approved institutional documents (curricula, fee structures, hostel rules, academic regulations, scholarship circulars). When verified context is absent or confidence falls below a calibrated threshold, the system explicitly rejects hallucination, acknowledges the limitation, and seamlessly transitions the user to an audited support ticketing workflow.

---

## 2. Stakeholders & User Personas

| Persona | Access Level | Primary Goals | Key Pain Points |
| :--- | :--- | :--- | :--- |
| **Prospective Student / Parent** | Public (Unauthenticated / Anonymous Session) | Query admission criteria, cut-offs, fee schedules, hostel amenities in English or Tamil. | Outdated PDFs, inconsistent circulars, slow telephone responses. |
| **Enrolled Student** | Public Widget / Authenticated Portal | Inquire about exam schedules, revaluation rules, hall ticket issues, scholarship deadlines. | Need rapid answers with explicit section/page citations to college rules. |
| **Help Desk Agent** | Admin Portal (Role: `SUPPORT_AGENT`) | Triage, assign, respond to, and resolve escalated tickets; inspect chat context that prompted ticket. | High ticket volume on repetitive queries; lack of prior chat context. |
| **Department Content Approver** | Admin Portal (Role: `CONTENT_APPROVER`) | Upload, verify, and approve official departmental circulars and handbooks with academic year tags. | Risk of outdated documents being retrieved by students. |
| **College Super Administrator** | Admin Portal (Role: `SUPER_ADMIN`) | Manage users, RBAC roles, system configuration, audit logs, OpenAI token quotas, and analytics. | Data governance, system uptime, cloud AI cost control, security compliance. |
| **Compliance & Auditor** | Admin Portal (Role: `AUDITOR`) | Review access logs, document version history, ticket SLAs, and RAG accuracy benchmarks. | Verifiable audit trail for statutory compliance (e.g., NAAC/NIRF). |

---

## 3. Functional Requirements

### 3.1 Public Conversational AI & Widget
- **FR-PUB-01: Zero-Dependency Embeddable Widget**: Embeddable via a single `<script>` tag into WordPress, Drupal, PHP, plain HTML, or modern SPA portals. Renders in an isolated Shadow DOM or sandboxed iframe to prevent CSS/JS clashes with the host site.
- **FR-PUB-02: Bilingual Language Support**: Automatic language detection and fluent response generation in English and Tamil (including transliterated "Tanglish" query normalization).
- **FR-PUB-03: Strict Grounding & Anti-Hallucination**: Answers must be generated solely from approved document chunks with similarity and cross-encoder score exceeding minimum confidence thresholds ($\tau \ge 0.72$). If context is insufficient, the chatbot must output a standardized fallback response.
- **FR-PUB-04: Verifiable Citations**: Every factual statement must cite the source document name, document version, publication date, academic year, and page/section number. No fabricated citations are permitted.
- **FR-PUB-05: Dynamic Academic Year Filtering**: Users can query specific academic years (e.g., "What was the 2024-2025 hostel fee?"). By default, the system filters for the currently active academic year.
- **FR-PUB-06: Seamless Escalation to Ticket**: When the bot cannot answer or the user explicitly expresses dissatisfaction ("This did not help" / "Connect to human"), the widget opens a ticket creation form pre-populated with conversation history.
- **FR-PUB-07: Session Privacy & Ephemeral State**: Public sessions require no login. Conversations are assigned UUID session IDs stored in secure client sessionStorage, expiring after inactivity.

### 3.2 Document Ingestion, OCR & Knowledge Base
- **FR-DOC-01: Multi-Format Parsing**: Ingest digital PDFs, scanned PDFs, DOCX, and high-resolution images (PNG, JPEG, TIFF) of circulars.
- **FR-DOC-02: Bilingual OCR Pipeline**: Integrated Tesseract OCR with English (`eng`) and Tamil (`tam`) models for scanned circulars, with automated DPI normalization and deskewing.
- **FR-DOC-03: Chunking & Hierarchy Preservation**: Semantic recursive chunking (500–800 tokens with 15% overlap) preserving header hierarchies, tables, and page boundaries.
- **FR-DOC-04: Document Lifecycle & Governance**: Documents transition through states: `DRAFT` $\to$ `PENDING_REVIEW` $\to$ `APPROVED` $\to$ `PUBLISHED` $\to$ `ARCHIVED`. Only `PUBLISHED` documents are indexed for public retrieval.
- **FR-DOC-05: Versioning & Soft Invalidation**: Re-uploading a revised circular marks the previous version as `SUPERSEDED` or `ARCHIVED`, immediately updating vector index metadata without breaking historical ticket references.

### 3.3 Search & Hybrid Retrieval (RAG)
- **FR-SRCH-01: Hybrid Search**: Combines dense semantic vector search (OpenAI `text-embedding-3-small` / `3-large` via `pgvector`) with sparse lexical search (PostgreSQL `tsvector` with English and Tamil dictionaries).
- **FR-SRCH-02: Reciprocal Rank Fusion (RRF)**: Merges sparse and dense search rankings using normalized RRF scoring ($k=60$) before reranking.
- **FR-SRCH-03: Metadata Filtering**: Pre-filtering chunks on `status = 'PUBLISHED'`, `academic_year = :year`, and `department = :dept`.

### 3.4 Support Ticketing System
- **FR-TCK-01: Ticket Creation**: Public users can submit tickets with name, email, phone number, category (Admissions, Fees, Exams, Hostel, General), priority, and message.
- **FR-TCK-02: Context Attachment**: Optional attachment of recent chat conversation transcript to the ticket with explicit user consent.
- **FR-TCK-03: Automated Notifications**: Async email dispatch via Redis worker to the user (with ticket tracking ID) and to the designated departmental inbox.
- **FR-TCK-04: Ticket Lifecycle Management**: Staff can update status (`OPEN`, `IN_PROGRESS`, `WAITING_FOR_USER`, `RESOLVED`, `CLOSED`), assign staff, add internal notes, and reply to users.

### 3.5 Administrative Portal & Security
- **FR-ADM-01: Secure Authentication**: Email/password authentication using Argon2id password hashing, JWT access tokens in short-lived memory, and HTTP-only, secure, SameSite refresh tokens. Optional TOTP 2FA for administrators.
- **FR-ADM-02: Role-Based Access Control (RBAC)**: Strict permission boundaries separating Super Admins, Department Approvers, Support Agents, and Auditors.
- **FR-ADM-03: Audit Logging**: Immutable audit logs capturing every document upload, approval, deletion, configuration change, and administrative login.
- **FR-ADM-04: Cost & Token Tracking**: Tracking of input/output token usage per query, aggregated by model, endpoint, and day, with alert triggers for budget limits.

---

## 4. Non-Functional Requirements (NFRs)

### 4.1 Performance & Latency
- **NFR-PERF-01: Widget Load Time**: Widget embed script must be $< 80\text{ KB}$ gzipped and execute in $< 150\text{ ms}$ on 4G networks.
- **NFR-PERF-02: Chatbot Response Latency**: Time to First Token (TTFT) $\le 1.2\text{ s}$; full streamed response completion $\le 3.5\text{ s}$ for 95th percentile under standard load.
- **NFR-PERF-03: Concurrent Chat Capacity**: Minimum 200 concurrent active chat sessions per worker instance without degradation.
- **NFR-PERF-04: Document Ingestion Throughput**: Ingest and index a 50-page digital PDF in $< 45\text{ s}$ via async Redis background workers.

### 4.2 Security & Compliance
- **NFR-SEC-01: Public vs. Admin Separation**: Public widget APIs (`/api/v1/public/*`) must be strictly segregated from Administrative APIs (`/api/v1/admin/*`) at routing, authentication, and rate-limiting layers.
- **NFR-SEC-02: Rate Limiting & Abuse Prevention**: IP-based and session-based rate limiting on public endpoints (e.g., max 15 chat queries/minute, max 3 ticket submissions/hour per IP).
- **NFR-SEC-03: Prompt Injection Guardrails**: Strict sanitization of user queries; system prompt delimiters; prompt defense against jailbreaks and instruction overrides.
- **NFR-SEC-04: Data Privacy**: PII redaction for phone numbers, student registration numbers, and email addresses in analytics logs. Public chat sessions can be purged after 30 days.

### 4.3 Reliability & Availability
- **NFR-REL-01: System Uptime**: 99.5% availability for the public chatbot widget and ticketing submission endpoint.
- **NFR-REL-02: Graceful Degradation**: If the vector database or OpenAI API is unreachable, the chatbot widget immediately falls back to ticketing mode without crashing.
- **NFR-REL-03: Transactional Integrity**: All document metadata updates and chunk vector deletions must occur in atomic database transactions.

---

## 5. Architectural Boundaries & Isolation
1. **Network Layer**: Public traffic reaches `/widget` and `/api/v1/public` endpoints through a reverse proxy (Nginx). Administrative routes (`/admin` and `/api/v1/admin`) are protected by JWT verification, IP whitelisting options, and strict CORS policies.
2. **Database Layer**: A single PostgreSQL database with separate logical schemas or table-level RBAC where unprivileged connections have no direct access to administrative audit logs or user credentials.
3. **Execution Layer**: Web servers run stateless FastAPI containers. Asynchronous parsing, OCR, and embedding generation execute exclusively on isolated background worker containers via Redis queues.
