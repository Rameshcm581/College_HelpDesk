# Comprehensive Security Review & Threat Assessment

**Audit Date:** 2026-10-22  
**Scope:** Full-stack security evaluation across API, Authentication, RBAC, Data Layer, Embeddable Widget, AI/RAG Pipeline, and Container Infrastructure.  
**Auditor:** Senior Security Engineer & DevOps Auditor  

---

## 1. Executive Security Posture

The application demonstrates defense-in-depth architecture across all critical surfaces:
- **Authentication & Cryptography:** Zero plaintext passwords; Argon2id hashing; scoped JWT tokens with short lifetimes.
- **Authorization & RBAC:** Hierarchical role enforcement with strict department isolation boundaries.
- **AI & RAG Guardrails:** Constitutional prompt injection mitigation with XML delimiter isolation (`<user_inquiry>`) and temperature 0.0 grounding.
- **Network & Perimeter:** CSP `frame-ancestors` restriction, CORS whitelisting, SSRF validation for web ingestion, and reverse-proxy IP extraction.
- **Data Privacy & Compliance:** Automatic regex-based PII redaction in application logs; internal staff notes excluded from public visitor API endpoints.

---

## 2. Threat Analysis by Category

### 2.1 Authentication & Credential Management
- **Password Storage:** Uses **Argon2id** (`argon2-cffi`) with state-of-the-art memory and time cost parameters.
- **JWT Implementation:** Cryptographically signed tokens (HS256) with 15-minute access token lifespan. Refresh token rotation supported via HttpOnly cookies.
- **Production Guardrail:** `BaseConfig` enforces that if `APP_ENV=prod`, `SECRET_KEY` must be at least 32 characters and cannot use default/development strings.
- **OTP Generation & Verification:** 6-digit cryptographically secure random integers (`secrets.randbelow`). Stored in database as salted SHA-256 hashes (`_hash_otp`). Maximum 3 verification attempts enforced before permanent invalidation. Rate limited to 3 OTP requests per 10-minute sliding window.

### 2.2 Authorization & Role-Based Access Control (RBAC)
- **Roles:**
  - `SUPER_ADMIN`: Full system access, staff user provisioning, system monitoring.
  - `ADMIN`: College-wide document and ticket management.
  - `CONTENT_APPROVER`: Document upload, preview, and approval workflows.
  - `DEPARTMENT_STAFF`: Scoped strictly to tickets and documents belonging to their assigned department.
  - `VIEWER`: Read-only access to published circulars and dashboards.
- **Department Boundary Enforcement:**
  Verified via unit test `test_department_boundary_scope_isolation` and verified in `ticketController.py` and `documentController.py`. Department staff attempting to view, download, or edit records belonging to another department receive `403 Forbidden`.

### 2.3 Input Validation, File Safety & SSRF Defenses
- **SQL Injection Defenses:** 100% of database interactions utilize SQLAlchemy 2.0 async parameterized queries or ORM models. Zero dynamic raw SQL string interpolation.
- **Cross-Site Scripting (XSS):** React 18 JSX automatic HTML entity encoding prevents client-side reflection. Response headers include `X-Content-Type-Options: nosniff` and `X-XSS-Protection: 1; mode=block`.
- **File Upload Security:**
  - Size capped at 50 MB (`MAX_UPLOAD_SIZE_MB`).
  - Strict magic-byte validation (`%PDF-` header inspection in `pdfService.py`). Corrupted, spoofed, or non-PDF files rejected with `400 Bad Request`.
  - Storage path sanitization: random UUID-based file paths prevent path traversal attacks (`../`).
  - SHA-256 deduplication rejects duplicate file uploads.
- **Server-Side Request Forgery (SSRF) Defenses:**
  - `webScraperService.py` inspects target URLs prior to resolution.
  - Blocks loopback addresses (`127.0.0.1`, `localhost`, `::1`), link-local addresses (`169.254.0.0/16`), and private RFC 1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
  - Verified via `test_ssrf_defense_blocks_internal_and_loopback_destinations` and `test_api_ssrf_rejection`.

### 2.4 AI Security & Prompt Injection Mitigation
- **Delimiter Isolation:** Evidence chunks are wrapped in `<verified_context>` XML tags and user queries in `<user_inquiry language='...'>`.
- **Constitutional Directives:** System prompt instructs the model to ignore any instructions within `<user_inquiry>` that attempt to override constraints, request system prompts, or adopt personas.
- **Zero-Guessing Guardrail:** Retrieval score threshold $\tau = 0.72$ prevents the model from answering ungrounded queries; falls back cleanly to institutional support ticket creation.

### 2.5 Privacy & Log Sanitization (PII)
- **Masking Engine:** `mask_pii_for_logging` in `resources/utils.py` applies regex filters to server log streams.
- **Redactions:**
  - Indian 10-digit and 5+5 mobile numbers $\to$ `[PHONE_REDACTED]`
  - Email addresses $\to$ `[EMAIL_REDACTED]`
- **Visitor Privacy:** Ticket responses to visitors strictly filter out `TicketMessages` where `is_internal_note == True`.

### 2.6 Rate Limiting & Denial of Service Protection
- **Sliding-Window Memory Store:** Tracks request counts per client IP over rolling 60-second windows.
- **Proxy-Aware IP Extraction:** `get_client_ip` parses the leftmost client IP from `X-Forwarded-For` and `X-Real-IP`, preventing spoofing when behind Nginx or AWS ALB.
- **Memory Eviction:** Evicts expired sliding window entries automatically to prevent memory unbounded growth.

---

## 3. Summary of Security Test Results

| Security Control | Verification Method | Result | Notes |
|:---|:---|:---:|:---|
| **Argon2id Hashing** | Unit test `test_argon2_password_hashing` | **PASS** | High-entropy verification verified. |
| **JWT Expiration & Scope** | Unit test `test_jwt_token_generation_and_decoding` | **PASS** | Expired tokens rejected. |
| **Department RBAC Isolation** | Unit test `test_department_boundary_scope_isolation` | **PASS** | Cross-department access returns 403. |
| **SSRF Prevention** | Unit test `test_api_ssrf_rejection` | **PASS** | Internal IPs and localhost blocked. |
| **PDF Magic Header Check** | Unit test `test_file_type_and_signature_validation` | **PASS** | Non-PDF files rejected. |
| **Rate Limiting** | Unit tests `test_rate_limiter_in_memory` & `test_otp_rate_limiting` | **PASS** | Excess calls return 429. |
| **PII Masking in Logs** | Unit test `test_pii_masking_in_logs` | **PASS** | Emails & phone numbers masked. |
| **CSP Frame Ancestors** | Unit test `test_security_headers_and_frame_ancestors` | **PASS** | Embed restricted to whitelisted origins. |
