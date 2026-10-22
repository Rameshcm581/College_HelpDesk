# API Specification: College AI Help Desk (OpenAPI 3.1 Standards)

## 1. Overview & Protocol Standards

The **College AI Help Desk API** provides RESTful JSON endpoints with Server-Sent Events (SSE) for real-time conversational streaming. All endpoints adhere to consistent response envelope patterns, standard HTTP status codes, and strict separation between public unauthenticated endpoints and protected administrative endpoints.

### 1.1 Base URLs
- **Public Widget API**: `https://api.college.edu/api/v1/public`
- **Admin Management API**: `https://api.college.edu/api/v1/admin`

### 1.2 Global Error Response Envelope
Every 4xx and 5xx response follows this standard JSON structure:
```json
{
  "success": false,
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "The requested document could not be located.",
    "details": {},
    "timestamp": "2026-10-22T10:45:00Z",
    "request_id": "req-92f7b4c8"
  }
}
```

---

## 2. Public Endpoints (`/api/v1/public`)

### 2.1 Send Chat Query (Streaming & Standard)
- **Method**: `POST`
- **Path**: `/chat`
- **Description**: Submits a user question to the RAG pipeline. Supports both Server-Sent Events streaming (`Accept: text/event-stream`) and standard JSON responses (`Accept: application/json`).
- **Rate Limit**: 15 requests / minute per client IP.

#### Request Body
```json
{
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "query": "What are the rules and late fee for hostel fee payment?",
  "language": "en",
  "academic_year": "2025-2026",
  "department_id": null,
  "department_code": "HOSTEL",
  "document_type": "REGULATION",
  "version_number": 1
}
```

#### JSON Response (`200 OK`)
```json
{
  "success": true,
  "data": {
    "message_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "response": "Hostel fees must be cleared on or before July 31st for the odd semester. A late penalty of ₹100 per day is charged up to 15 days, after which hostel allotment stands cancelled.",
    "language": "en",
    "confidence_score": 0.94,
    "fallback_triggered": false,
    "citations": [
      {
        "document_id": "b1e0f399-6e3e-4d0d-a344-9337222485f5",
        "document_title": "Hostel Rules and Fee Structure 2025-2026",
        "version_number": 2,
        "academic_year": "2025-2026",
        "page_number": 6,
        "section": "Section 4.1: Late Penalties",
        "snippet": "Late fee of ₹100/day will be levied up to 15 days from due date..."
      }
    ],
    "suggested_actions": ["Pay Hostel Fee Online", "View Hostel Mess Menu"]
  }
}
```

#### Low Confidence / Fallback JSON Response (`200 OK`)
```json
{
  "success": true,
  "data": {
    "message_id": "8d8e6679-7425-40de-944b-e07fc1f90ae8",
    "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "response": "I could not find verified information regarding this policy in the official college circulars for 2025-2026. Would you like me to open an official support ticket for the Administration Office?",
    "language": "en",
    "confidence_score": 0.42,
    "fallback_triggered": true,
    "citations": [],
    "suggested_ticket": {
      "default_category": "HOSTEL",
      "prefilled_query": "What are the rules and late fee for hostel fee payment?"
    }
  }
}
```

#### Server-Sent Events (SSE) Stream Protocol
When `Accept: text/event-stream` is requested:
```text
event: metadata
data: {"message_id": "7c9e...", "confidence_score": 0.94, "fallback_triggered": false}

event: delta
data: {"token": "Hostel "}

event: delta
data: {"token": "fees must "}

event: citation
data: {"document_title": "Hostel Rules 2025-2026", "page_number": 6, "version": 2}

event: done
data: {"latency_ms": 1180}
```

---

### 2.2 Submit Chat Feedback
- **Method**: `POST`
- **Path**: `/chat/feedback`
- **Description**: Records end-user thumbs-up/down feedback on an answer.
- **Request Body**:
```json
{
  "message_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "feedback": "helpful",
  "comments": "Accurate page reference."
}
```
- **Response**: `200 OK` `{"success": true, "message": "Feedback recorded."}`

---

### 2.3 Submit Support Ticket
- **Method**: `POST`
- **Path**: `/tickets`
- **Description**: Creates a new student support ticket and queues notification emails.
- **Rate Limit**: 3 requests / hour per client IP.

#### Request Body
```json
{
  "session_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "student_name": "R. Vignesh",
  "student_email": "vignesh.r@example.com",
  "student_phone": "+91 98765 43210",
  "category": "HOSTEL",
  "priority": "MEDIUM",
  "message": "I paid the hostel caution deposit yesterday via NEFT, but the transaction receipt is showing pending in portal.",
  "include_chat_history": true
}
```

#### Response (`201 Created`)
```json
{
  "success": true,
  "data": {
    "ticket_number": "TCK-2026-00382",
    "status": "OPEN",
    "created_at": "2026-10-22T10:48:00Z",
    "tracking_url": "https://college.edu/helpdesk/track?ticket=TCK-2026-00382",
    "estimated_response_hours": 24
  }
}
```

---

### 2.4 Track Ticket Status
- **Method**: `GET`
- **Path**: `/tickets/{ticket_number}`
- **Description**: Public verification of ticket progress without exposing internal staff notes.
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "data": {
    "ticket_number": "TCK-2026-00382",
    "student_name": "R. Vignesh",
    "category": "HOSTEL",
    "status": "IN_PROGRESS",
    "created_at": "2026-10-22T10:48:00Z",
    "messages": [
      {
        "sender": "STUDENT",
        "message": "I paid the hostel caution deposit yesterday...",
        "created_at": "2026-10-22T10:48:00Z"
      },
      {
        "sender": "STAFF",
        "message": "We have received your NEFT transaction reference. The accounts section is verifying UTR with bank.",
        "created_at": "2026-10-22T11:15:00Z"
      }
    ]
  }
}
```

---

### 2.5 Public Widget Bootstrap Configuration
- **Method**: `GET`
- **Path**: `/config`
- **Description**: Fetches institutional metadata for widget hydration.
- **Response (`200 OK`)**:
```json
{
  "success": true,
  "data": {
    "college_name": "College of Engineering & Technology",
    "current_academic_year": "2025-2026",
    "supported_languages": ["en", "ta"],
    "greeting_en": "Hello! Ask me anything about admissions, courses, fees, or hostel facilities.",
    "greeting_ta": "வணக்கம்! சேர்க்கை, கட்டணம், தேர்வுகள் அல்லது விடுதி பற்றி கேளுங்கள்.",
    "departments": [
      {"id": "d1e0f399-...", "name": "Admissions Cell", "code": "ADM"},
      {"id": "d2e0f399-...", "name": "Hostel Administration", "code": "HST"}
    ]
  }
}
```

---

## 3. Administrative Authentication Endpoints (`/api/v1/admin/auth`)

### 3.1 Staff Login
- **Method**: `POST`
- **Path**: `/auth/login`
- **Request Body**:
```json
{
  "email": "dean.academics@college.edu",
  "password": "SecurePassword123#!"
}
```
- **Response (`200 OK`)**:
  - Sets HTTP-only, Secure, SameSite=Strict cookie: `refresh_token=<token>; Path=/api/v1/admin/auth/refresh; Max-Age=604800`
  - Returns access token in JSON body:
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOi...",
    "token_type": "Bearer",
    "expires_in": 900,
    "user": {
      "id": "u1e0f399-...",
      "email": "dean.academics@college.edu",
      "full_name": "Dr. K. Ramanathan",
      "role": "CONTENT_APPROVER",
      "department_id": "d1e0f399-..."
    }
  }
}
```

### 3.2 Token Refresh & Logout
- **POST** `/auth/refresh`: Exchanges valid cookie refresh token for new access token.
- **POST** `/auth/logout`: Revokes refresh token in Redis and clears cookies.
- **GET** `/auth/me`: Returns current user details and RBAC permissions.

---

## 4. Administrative Document Lifecycle Endpoints (`/api/v1/admin/documents`)

### 4.1 Upload Institutional Document
- **Method**: `POST`
- **Path**: `/documents/upload`
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `file`: Binary PDF or DOCX file.
  - `title`: "UG Admission Regulations 2025-2026"
  - `department_id`: UUID
  - `academic_year_id`: UUID
  - `version_notes`: "Initial version approved by Academic Council."
- **Response (`202 Accepted`)**:
```json
{
  "success": true,
  "data": {
    "document_id": "b1e0f399-6e3e-4d0d-a344-9337222485f5",
    "status": "DRAFT",
    "job_id": "task-ce94821a",
    "message": "Document uploaded and ingestion pipeline queued."
  }
}
```

### 4.2 Document Management Actions
- **GET `/documents`**: Paginated listing with filtering by `status`, `department_id`, `academic_year_id`, and `search`.
- **GET `/documents/{id}`**: Detailed view including parsed chunk previews, OCR quality score, and version lineage.
- **POST `/documents/{id}/approve`**: (Requires `CONTENT_APPROVER` or `SUPER_ADMIN`) Advances status from `PENDING_REVIEW` to `APPROVED`.
- **POST `/documents/{id}/publish`**: (Requires `SUPER_ADMIN`) Activates chunks for public RAG retrieval and invalidates affected semantic caches.
- **POST `/documents/{id}/archive`**: Deactivates document chunks from retrieval index.
- **POST `/documents/{id}/reindex`**: Re-runs embedding generation or OCR pipeline on updated settings.

---

## 5. Administrative Ticket Management Endpoints (`/api/v1/admin/tickets`)

- **GET `/tickets`**: Filters by status (`OPEN`, `IN_PROGRESS`, `RESOLVED`, `CLOSED`), priority, department, and assigned agent.
- **GET `/tickets/{id}`**: Retrieves ticket details, public message thread, internal private staff notes, and associated chat session transcript.
- **PATCH `/tickets/{id}`**: Updates ticket priority, assignee, status, or department routing.
- **POST `/tickets/{id}/messages`**:
```json
{
  "message": "The payment has been confirmed by Bank. Receipt #RCT-9421 generated.",
  "is_internal_note": false,
  "attachment_urls": ["https://storage.college.edu/receipts/RCT-9421.pdf"]
}
```

---

## 6. Admin Analytics, Audit & Telemetry (`/api/v1/admin/analytics`)

- **GET `/analytics/overview`**: Total questions answered, top inquiry categories, average resolution latency, and user satisfaction percentage.
- **GET `/analytics/content-gaps`**: Aggregated list of high-frequency questions where confidence was $< 0.72$, highlighting missing institutional documentation.
- **GET `/analytics/costs`**: Daily OpenAI token breakdown by model (`text-embedding-3-small`, `gpt-4o-mini`, `gpt-4o`) with projected monthly cloud expenditure.
- **GET `/audit-logs`**: Immutable, filterable audit trail of staff actions, logins, and document state changes.

---

## 7. Administrative Dashboard & Role-Based Control (`/api/v1/admin`)

### 7.1 Role-Based Access Control (RBAC) Matrix
The API enforces backend authorization across four institutional roles:
- **`SUPER_ADMIN`**: Full universal access across all endpoints, configuration, and user management.
- **`ADMIN`** (alias: `CONTENT_APPROVER`): Can upload circulars, stage versions, preview chunks, approve/reject versions, archive documents, and modify branding/config.
- **`DEPARTMENT_STAFF`** (alias: `SUPPORT_AGENT`): Access scoped to assigned `department_id`. Can view overview metrics, knowledge gaps, and circulars for their department.
- **`VIEWER`** (alias: `AUDITOR`): Read-only institutional oversight across documents, monitoring metrics, and knowledge gaps. Cannot modify documents, users, or configuration.

### 7.2 Administrative Endpoints

#### `GET /api/v1/admin/overview`
- **Access**: `SUPER_ADMIN`, `ADMIN`, `DEPARTMENT_STAFF`, `VIEWER`
- **Description**: Returns live PostgreSQL calculated aggregates (documents, jobs, tickets, unanswered queries, grounding rate, and latency).
- **Response**:
```json
{
  "success": true,
  "data": {
    "documents": { "total": 4, "published": 2, "review_required": 1, "archived": 1, "failed": 0 },
    "ingestion_jobs": { "total": 4, "completed": 3, "processing": 0, "queued": 0, "failed": 1 },
    "support_tickets": { "total": 5, "open": 2, "in_progress": 1, "resolved": 2 },
    "unanswered_questions": { "total_unanswered_recent": 3, "negative_feedback_count": 1 },
    "usage_metrics": { "total_queries": 18, "fallback_count": 3, "grounding_rate_pct": 83.3, "avg_latency_ms": 1240 },
    "recent_fallbacks": [...],
    "is_demonstration_mode": false,
    "user_role": "SUPER_ADMIN",
    "department_scope": null
  }
}
```

#### `GET /api/v1/admin/knowledge-gaps`
- **Access**: `SUPER_ADMIN`, `ADMIN`, `DEPARTMENT_STAFF`, `VIEWER`
- **Description**: Identifies ungrounded questions below threshold (τ < 0.72), negative feedback ratings, and automatic topic clusters.

#### `GET /api/v1/admin/users`
- **Access**: `SUPER_ADMIN` only (403 Forbidden for other roles)
- **Description**: Returns list of all staff accounts with roles and departmental scoping.
- **Related Mutations**: `POST /users` (create), `PUT /users/{id}` (update/role assignment), `DELETE /users/{id}` (soft-deactivate).

#### `GET /api/v1/admin/config` & `PUT /api/v1/admin/config`
- **Access**: Read: all authenticated staff; Write: `SUPER_ADMIN`, `ADMIN` (403 Forbidden for `VIEWER`).
- **Description**: Manages college identity branding, welcome messages in English & Tamil, suggested questions, and approved embed origins.

#### `GET /api/v1/admin/monitoring`
- **Access**: `SUPER_ADMIN`, `ADMIN`, `VIEWER`
- **Description**: Exposes failed ingestion jobs, recent application error logs, latency percentiles (p50, p95, p99), and AI token expenditure (USD and INR).

#### `GET /api/v1/admin/metadata`
- **Access**: All authenticated staff
- **Description**: Dynamic dropdown metadata for roles, departments, and academic years.

---

## 8. Support Ticketing & Visitor OTP Security (`/api/v1/public/tickets` & `/api/v1/admin/tickets`)

### 8.1 Ticket Lifecycle State Machine
Tickets follow a backend-enforced transition model:
- `OPEN` $\to$ `ASSIGNED`, `IN_PROGRESS`, `CLOSED`
- `ASSIGNED` $\to$ `IN_PROGRESS`, `WAITING_FOR_USER`, `CLOSED`
- `IN_PROGRESS` $\to$ `WAITING_FOR_USER`, `RESOLVED`, `CLOSED`
- `WAITING_FOR_USER` $\to$ `IN_PROGRESS` (automatic upon visitor response), `RESOLVED`, `CLOSED`
- `RESOLVED` $\to$ `CLOSED`, `IN_PROGRESS` (requires mandatory resolution notes)
- `CLOSED` $\to$ `IN_PROGRESS` (reopened by staff)

### 8.2 Category & Department Routing Rules
Support categories map automatically to institutional desks:
- `ADMISSIONS` $\to$ `ADM` (Admissions Cell)
- `FEES` $\to$ `FIN` (Accounts & Finance Office)
- `EXAMINATIONS` $\to$ `EXM` (Controller of Examinations)
- `HOSTEL` $\to$ `HST` (Hostel Administration)
- `SCHOLARSHIPS` $\to$ `SCH` (Student Welfare & Scholarships Cell)
- `PLACEMENTS` $\to$ `PLC` (Career Guidance & Placement Cell)
- `GENERAL` $\to$ `GEN` (General Administration)

### 8.3 SLA Deadlines
- `URGENT`: 4 Hours
- `HIGH`: 12 Hours
- `MEDIUM`: 24 Hours
- `LOW`: 48 Hours

### 8.4 Public Endpoints

#### `POST /api/v1/public/tickets`
Creates a new support ticket and captures minimal required fields.
- **Payload**: `{ "student_name", "student_email", "student_phone" (optional), "category", "subject", "message", "priority" (optional), "session_id" (optional) }`
- **Response**: `201 Created` with unique `ticket_number` (`TCK-YYYY-XXXXX`), `department_code`, and `sla_due_at`.

#### `POST /api/v1/public/tickets/{ticket_number}/request-otp`
Generates a cryptographically secure 6-digit OTP and sends it to the visitor's registered email.
- **Security**: Rate-limited (max 3 per 10m window), expires in 15 minutes. Salted SHA-256 hashed storage. Zero plaintext OTP logging.
- **Payload**: `{ "email": "student@example.com" }`

#### `POST /api/v1/public/tickets/{ticket_number}/verify-otp`
Verifies OTP code with a 3-attempt limit.
- **Payload**: `{ "email": "student@example.com", "otp": "123456" }`
- **Response**: `200 OK` with scoped JWT visitor token (`visitor_ticket_access`).

#### `GET /api/v1/public/tickets/{ticket_number}`
Returns visitor-safe ticket details and communication feed.
- **Header**: `Authorization: Bearer <visitor_token>`
- **Security**: Internal staff notes are stripped. Access to other tickets yields `403 Forbidden`.

#### `POST /api/v1/public/tickets/{ticket_number}/messages`
Submits a follow-up reply from the visitor.
- **Header**: `Authorization: Bearer <visitor_token>`
- **Automatic State Machine**: If status is `WAITING_FOR_USER`, automatically transitions ticket back to `IN_PROGRESS`.

### 8.5 Admin & Staff Endpoints

#### `GET /api/v1/admin/tickets`
- **Access**: `SUPER_ADMIN`, `ADMIN`, `DEPARTMENT_STAFF`, `VIEWER`
- **Scoping**: `DEPARTMENT_STAFF` can only view tickets routed to their department or assigned to them.
- **Query Params**: `status`, `category`, `department_code`, `overdue_only`, `search`.

#### `GET /api/v1/admin/tickets/{ticket_id}`
- **Access**: Permitted staff
- **Returns**: Full ticket details, internal notes, status audit history, and associated pre-escalation chatbot messages (from linked `session_id`).

#### `POST /api/v1/admin/tickets/{ticket_id}/assign`
- **Access**: `SUPER_ADMIN`, `ADMIN`, `DEPARTMENT_STAFF`
- **Payload**: `{ "assigned_to_user_id": "<uuid>", "note": "optional" }`
- **Lifecycle**: Automatically transitions `OPEN` $\to$ `ASSIGNED`.

#### `PATCH /api/v1/admin/tickets/{ticket_id}/status`
- **Access**: `SUPER_ADMIN`, `ADMIN`, `DEPARTMENT_STAFF`
- **Validation**: Enforces valid status lifecycle. Rejects invalid transitions with `400 Bad Request`. Requires `resolution_notes` when setting `RESOLVED`.
- **Notifications**: Dispatches notification emails to visitor via configured `EmailProvider`.

#### `POST /api/v1/admin/tickets/{ticket_id}/messages`
- **Access**: Permitted staff
- **Payload**: `{ "message": "...", "is_internal_note": boolean }`
- **Lifecycle**: If `is_internal_note=false`, dispatches email notification to visitor and automatically moves status to `WAITING_FOR_USER`.


