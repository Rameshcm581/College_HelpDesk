# College AI Help Desk Platform

An enterprise-grade, multilingual (English & Tamil) AI-powered help desk and support ticketing platform for higher-education institutions. Answers prospective students, enrolled students, parents, and faculty with verified source citations strictly grounded on approved college circulars and regulations.

---

## 1. Architectural Highlights

- **Bilingual RAG Core**: Fluent responses in English and Tamil (தமிழ்), grounded exclusively in official institutional circulars.
- **Strict Anti-Hallucination Guardrails**: Refuses to guess or hallucinate when retrieval confidence score is below threshold ($\tau < 0.72$); automatically routes ungrounded queries to student support tickets.
- **Isolated Embeddable Widget**: Public widget operates inside a closed **Shadow DOM** for zero CSS/JS collisions with the host college website.
- **Modular Monolith Backend**: Organised according to the clean modular service pattern (`Services/HelpdeskService/` with dedicated `configs/`, `models/`, `resources/`, `routes/`, and `tests/`).
- **PostgreSQL 16 with pgvector & Hybrid Search**: Combines dense vector embeddings (`text-embedding-3-small`, 1536 dims, HNSW index) with sparse PostgreSQL `tsvector` full-text search using Reciprocal Rank Fusion (RRF).
- **Asynchronous Task Workers**: Celery + Redis for CPU/memory-heavy tasks (bilingual Tesseract OCR and PDF parsing).

---

## 2. Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Lucide React, Vitest |
| **Backend** | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 (asyncio), Alembic |
| **Database** | PostgreSQL 16 + `pgvector` (HNSW indexing) + PostgreSQL Full-Text Search (GIN) |
| **Cache & Queue** | Redis 7 Alpine, Celery (ingestion & notification queues) |
| **Security** | Argon2id password hashing, JWT access tokens with rotation, PII redaction |
| **DevOps** | Docker, Docker Compose, automated backup snapshots with `pg_dump` |

---

## 3. Project Directory Structure

```text
college-ai-helpdesk/
├── docs/                           # Architecture, DB schema, API specs, security
├── backups/                        # Database snapshots (.dump files)
├── logs/                           # Runtime log files
├── scripts/                        # Operational automation
│   ├── start_all.sh                # Boots DB, Redis, runs migrations
│   ├── stop_all.sh                 # Graceful teardown
│   ├── smoke_test.sh               # Health check and endpoint verification
│   ├── backup.sh                   # Automated pg_dump snapshot
│   ├── restore_drill.sh            # Disaster recovery restoration test
│   └── lint_all.sh                 # End-to-end frontend & backend QA suite
├── docker-compose.yml              # Local development stack (Postgres + Redis)
├── .env.example                    # Environment variable configuration template
├── backend/
│   ├── requirements.txt            # Python dependencies
│   ├── .venv/                      # Python virtual environment
│   └── Services/
│       └── HelpdeskService/        # Core backend service package
│           ├── main.py             # FastAPI entry point & lifespan manager
│           ├── celery_app.py       # Celery worker definition
│           ├── alembic.ini         # Alembic migration configuration
│           ├── alembic/            # Database migration scripts
│           ├── configs/            # Hierarchical settings (base, dev, local)
│           ├── models/             # SQLAlchemy 2.0 ORM models
│           ├── resources/          # Controllers, schemas, errors, utilities
│           ├── routes/             # Canonical API route registrations
│           └── tests/              # Pytest test suite
└── frontend/
    ├── package.json                # Frontend dependencies
    ├── vite.config.ts              # Vite config with API proxy
    ├── tailwind.config.js          # Tailwind CSS styling tokens
    └── src/
        ├── App.tsx                 # Router & layout
        ├── components/             # Navbar, Footer, StatusBadge
        ├── pages/                  # PublicChatbot, AdminDashboard, Documents, Tickets
        ├── services/               # API clients
        └── types/                  # TypeScript interface definitions
```

---

## 4. Local Quickstart Guide

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- Docker Engine & Docker Compose

### Step 1: Environment Setup
```bash
# Clone and enter directory
cd college-ai-helpdesk

# Create local environment configuration from template
cp .env.example .env
```

### Step 2: Start PostgreSQL with pgvector & Redis
```bash
# Spin up healthy containers in background
docker compose up -d helpdesk_db helpdesk_redis
```
*Note: To avoid local port conflicts with other running services, PostgreSQL is exposed on port **`5435`** and Redis on port **`6380`**.*

### Step 3: Run Database Migrations
```bash
# Activate virtual environment
source backend/.venv/bin/activate

# Apply all Alembic migrations
cd backend/Services/HelpdeskService
alembic upgrade head
```

### Step 4: Start the FastAPI Backend
```bash
# From backend/Services/HelpdeskService:
uvicorn main:app --host 0.0.0.0 --port 8005 --reload
```
The backend API is now accessible at `http://localhost:8005`.
- Interactive API Docs (Swagger): `http://localhost:8005/docs`
- Health Check: `http://localhost:8005/api/v1/public/health`

### Step 5: Start the Frontend React Application
```bash
cd frontend
npm install
npm run dev # or npm run preview -- --port 5175 --host 127.0.0.1
```
The frontend portal is now accessible at `http://localhost:5175`.

---

## 5. Embeddable Website Chatbot Widget

The platform provides a lightweight, zero-dependency embeddable chatbot widget that can be installed on **any external college website** (WordPress, static HTML, PHP, Drupal, React, Angular, or Vue) **without rebuilding the site in React**.

### 5.1 Host Website Embed Snippet
Paste the following snippet just before the closing `</body>` tag of any webpage:

```html
<!-- College AI Help Desk Virtual Assistant -->
<script
  src="http://127.0.0.1:5175/widget.js"
  data-chatbot-id="college-helpdesk"
  data-api-base="http://127.0.0.1:8005"
  data-position="bottom-right"
  defer
></script>
```

### 5.2 Configurable Options (HTML Attributes)

| Attribute | Default | Description |
|:---|:---|:---|
| `data-chatbot-id` | `college-helpdesk` | Identifies the tenant / bot configuration profile. |
| `data-api-base` | Host origin | Base URL of the FastAPI backend service (`http://127.0.0.1:8005`). |
| `data-position` | `bottom-right` | Widget anchor position (`bottom-right` or `bottom-left`). |
| `data-primary-color` | `#1e3a8a` | Brand primary color applied to header and launcher button. |
| `data-widget-url` | Script origin + `/widget` | Optional custom URL pointing to the isolated widget iframe. |

### 5.3 Host JavaScript Control API
Host pages can programmatically trigger the widget:

```javascript
// Open the chat window
window.CollegeHelpdesk.open();

// Close the chat window
window.CollegeHelpdesk.close();

// Toggle open / closed state
window.CollegeHelpdesk.toggle();
```

### 5.4 Standalone Host Verification Test Page
A test page simulating an external host website with aggressive global CSS overrides is available at:
`http://127.0.0.1:5175/standalone_test_host.html`

This page verifies:
1. **Total CSS Isolation**: Host global resets and aggressive styles cannot bleed into the widget.
2. **Interactive RAG**: Questions reach the FastAPI backend and return verified citations.
3. **Bilingual Toggle**: Switching between English and தமிழ் immediately updates greetings and prompt chips.
4. **Safe Fallback**: Questions outside approved circulars trigger an amber refusal card and ticket suggestion.
5. **Keyboard Accessibility**: Pressing `ESC` closes the open chat panel.

---

## 6. Verification & Testing

Run the automated QA test suite across both frontend and backend:
```bash
# Backend pytest suite (45 tests covering RAG, widget API, rate limiting, and admin dashboard RBAC)
cd backend
PYTHONPATH=Services/HelpdeskService .venv/bin/pytest Services/HelpdeskService/tests -v

# Frontend vitest suite (13 tests covering routing, widget protocol, and admin dashboard permissions)
cd frontend
npm test

# Production build verification
npm run build
```

Execute the live endpoint smoke test:
```bash
# Verifies /health, /api/v1/public/health (pgvector + redis), /config, /live
bash scripts/smoke_test.sh http://localhost:8005
```

Create and verify a database backup snapshot:
```bash
bash scripts/backup.sh
bash scripts/restore_drill.sh
```

---

## 7. Administrative Dashboard & Role-Based Access Control

The platform provides an administrative dashboard for institutional staff accessible at `http://localhost:5175/admin`.

### 7.1 Seeded Administrative Credentials

The database migration seeds 4 sample staff accounts demonstrating the full RBAC permission hierarchy:

| Role | Email | Password | Privileges & Scope |
|:---|:---|:---|:---|
| **Super Admin** | `admin@college.edu` | `DevAdminSecret123#!` | Universal campus access, user provisioning, role assignments, branding configuration. |
| **Admin (Dean)** | `dean_admin@college.edu` | `DeanAdminSecret123#!` | Upload circulars, stage versions, preview chunks, approve/reject versions, archive. |
| **Department Staff** | `staff_hostel@college.edu` | `StaffSecret123#!` | Scoped to Hostel Administration (`dept-hostel`). Can view relevant circulars and gaps. |
| **Viewer / Auditor** | `auditor_viewer@college.edu` | `ViewerSecret123#!` | Read-only oversight of live telemetry, knowledge gaps, and documents. Mutation routes rejected. |

### 7.2 Functional Dashboard Sections

1. **Overview**: Live PostgreSQL KPI statistics (documents, background jobs, tickets, unanswered queries, grounding rate %, median latency). Fully connects to `/api/v1/admin/overview`.
2. **Document Management**: Upload PDF documents, specify academic year and metadata, view ingestion status, inspect extracted text and chunks, approve or reject versions, stage replacement versions, and archive. Connects to `/api/v1/admin/documents`.
3. **Knowledge Gaps**: Live tracking of student questions the chatbot could not answer (confidence $< 0.72$), negative student ratings, and automated topic clusters with department assignments. Connects to `/api/v1/admin/knowledge-gaps`.
4. **User Management**: Staff account provisioning, role assignment, and department scoping. Protected strictly for `SUPER_ADMIN` with backend 403 Forbidden enforcement. Connects to `/api/v1/admin/users`.
5. **Configuration**: Institution branding (name, acronym, tagline, color), multilingual welcome messages in English & Tamil, suggested starter prompts, and approved widget embed origins. Connects to `/api/v1/admin/config`.
6. **Monitoring & Latency**: Detailed background ingestion failures log with retry actions, application 4xx/5xx error audit, gateway response latency percentiles (p50, p95, p99), and AI token consumption with estimated costs in USD ($) and INR (₹). Connects to `/api/v1/admin/monitoring`.

---

## 8. Support Ticketing & Visitor OTP Case Tracking

The support ticketing system provides end-to-end case resolution for questions ungrounded by the chatbot, explicit human assistance requests, student issue reporting, and escalations.

### 8.1 Public Case Portal & Zero-Password OTP Tracking
- **Public Ticket Submission (`/tickets` or chatbot fallback)**:
  - Captures student name, email, optional phone, category, priority, subject, and message.
  - Automatically routes tickets to designated departments:
    - **Admissions** $\to$ Admissions Cell (`ADM`)
    - **Fees** $\to$ Accounts & Finance (`FIN`)
    - **Examinations** $\to$ Controller of Examinations (`EXM`)
    - **Hostel** $\to$ Hostel Administration (`HST`)
    - **Scholarships** $\to$ Student Welfare & Scholarships (`SCH`)
    - **Placements** $\to$ Career Guidance & Placement Cell (`PLC`)
    - **General enquiries** $\to$ General Administration (`GEN`)
  - Calculates institutional SLA targets: `URGENT` (4h), `HIGH` (12h), `MEDIUM` (24h), `LOW` (48h).
  - Assigns unique, sequential ticket identifiers: `TCK-YYYY-XXXXX`.
- **Zero-Password Secure OTP Verification**:
  - Allows visitors without college accounts to track case progress securely.
  - Generates cryptographically secure 6-digit one-time passcodes (OTP).
  - Rate-limited to max 3 OTP generation requests per 10 minutes.
  - Max 3 verification attempts before passcode invalidation and rate lockout.
  - Passcodes expire in 15 minutes and are stored using salted SHA-256 hashes.
  - **Zero Secret Logging**: Plaintext passcodes and auth tokens are never written to server logs.
  - Grants short-lived scoped visitor JWT tokens (`visitor_ticket_access`).
  - Visitors can post follow-up replies which automatically move tickets from `WAITING_FOR_USER` back to `IN_PROGRESS`.

### 8.2 Email Notification Abstraction
- Configurable `EmailProvider` interface with support for:
  - `SmtpEmailProvider`: Production SMTP delivery with TLS/SSL authentication.
  - `UnconfiguredEmailProvider`: Gracefully handles environments without SMTP credentials without failing requests or falsely simulating delivery.
  - `MockTestEmailProvider`: In-memory capture for automated testing.
- Dispatches notifications on:
  - Ticket creation receipt with tracking identifier and SLA deadline.
  - Status lifecycle transitions.
  - College staff responses.
  - Case resolution with official resolution summary.

### 8.3 Staff Triage & State Machine
Integrated into `/tickets` (Staff mode) and `/admin?tab=tickets`:
- **Backend-Enforced State Transitions**:
  - `OPEN` $\to$ `ASSIGNED` $\to$ `IN_PROGRESS` $\to$ `WAITING_FOR_USER` $\to$ `RESOLVED` $\to$ `CLOSED`
  - Rejects illegal state jumps (e.g. `OPEN` directly to `RESOLVED`).
  - Mandatory resolution notes enforced when resolving tickets.
- **Role Scoping**: Department staff (`staff_hostel@college.edu`) are scoped exclusively to their department or assigned tickets.
- **Pre-Escalation Chatbot Transcript**: Authorized staff can inspect the exact conversation history and confidence scores that preceded ticket creation.
- **Internal Staff Notes**: Staff can record internal notes (amber highlighted, lock icon) strictly invisible to students.

### 8.4 Running Ticketing Tests
```bash
# Run backend support ticketing test suite (8 tests)
PYTHONPATH=Services/HelpdeskService backend/.venv/bin/pytest Services/HelpdeskService/tests/test_ticket_workflow.py -v

# Run complete backend test suite (26 tests)
PYTHONPATH=Services/HelpdeskService backend/.venv/bin/pytest Services/HelpdeskService/tests -v

# Run frontend ticketing test suite
cd frontend && npm test
```

