# Document Ingestion and Versioning System

## 1. Overview
The College AI Help Desk Chatbot features an enterprise-grade document ingestion and versioning pipeline that ingests, extracts, stages, reviews, indexes, and maintains institutional records (academic calendars, tuition fees, hostel rules, exam guidelines).

The system ensures that **no unapproved, draft, processing, failed, or expired documents can ever be retrieved by students or parents**, while providing zero-downtime safe version replacements.

---

## 2. Ingestion Architecture & Data Flow

```
[Administrator / Approver]
            │
            ├────────────────────────────────────────┐
            ▼ (Multipart PDF Upload)                  ▼ (URL Ingestion)
[PDFExtractionService]                      [WebScraperService]
 ├─ Magic bytes: %PDF                        ├─ Scheme validation: http/https
 ├─ Size cap: BaseConfig.MAX_UPLOAD_SIZE     ├─ DNS IP resolution
 ├─ SHA-256 deduplication                    ├─ Strict SSRF defense
 └─ Safe UUID-based storage                  ├─ Manual redirect IP re-validation
            │                                └─ HTML strip & structure
            │                                         │
            └────────────────────┬────────────────────┘
                                 │
                                 ▼
                     [PostgreSQL: IngestionJobs]
                                 │ (Queued)
                                 ▼
                    [Celery / Redis Background Worker]
                                 │
                                 ▼
                      [Text Extraction & OCR]
                      - High-density text: pypdf
                      - Low-density / images: OCR detection & processing
                      - Structure-aware paragraph preservation
                                 │
                                 ▼
                  [Status: REVIEW_REQUIRED]
                  (Extracted text preview stored)
                                 │
                 ┌───────────────┴───────────────┐
                 ▼ (Staff Review)                ▼ (Staff Review)
           [REJECTED]                       [APPROVED]
                 │                               │
                 ▼                               ▼
          Status: FAILED              [Celery / Redis Indexing Worker]
                                       ├─ Generate chunks & token counts
                                       ├─ Vector embeddings (1536-dim)
                                       ├─ Store in document_chunks
                                       └─ SAFE ACTIVATION:
                                          - New version -> ACTIVE
                                          - Previous active version -> ARCHIVED
                                          - Document active_version_id -> New Version
```

---

## 3. Document Lifecycle States & Transitions

| Lifecycle State | Description | Search Retrieval Ineligible? |
| :--- | :--- | :--- |
| `UPLOADED` | File received and safely stored on disk. Background job queued. | **YES (Excluded)** |
| `PROCESSING` | Worker actively extracting text or executing OCR. | **YES (Excluded)** |
| `REVIEW_REQUIRED` | Text extracted; administrator preview generated and awaiting staff approval. | **YES (Excluded)** |
| `APPROVED` | Authorized staff approved content; indexing job queued. | **YES (Excluded)** |
| `INDEXING` | Background worker generating pgvector embeddings. | **YES (Excluded)** |
| `ACTIVE` | Indexed and verified. Currently active version for the document. | **NO (Retrieved)** |
| `FAILED` | Extraction error, OCR failure, or rejected by staff. | **YES (Excluded)** |
| `ARCHIVED` | Superseded by newer version or retired by administrator. | **YES (Excluded)** |

### State Transition Rules:
1. `UPLOADED -> PROCESSING`: When background worker picks up the job.
2. `PROCESSING -> REVIEW_REQUIRED`: On successful text extraction and preview generation.
3. `PROCESSING -> FAILED`: When extraction fails, corrupt PDF detected, or retry limit exhausted.
4. `REVIEW_REQUIRED -> APPROVED`: When authorized staff (`SUPER_ADMIN` or `CONTENT_APPROVER`) approves.
5. `REVIEW_REQUIRED -> FAILED`: When staff rejects the extracted content.
6. `APPROVED -> INDEXING`: When background indexing job starts.
7. `INDEXING -> ACTIVE`: When chunking and vector storage finish successfully.
8. `ACTIVE -> ARCHIVED`: Automatically when a replacement version reaches `ACTIVE`, or manually archived.

---

## 4. Administrator Review & Approval API

All administrative endpoints are protected by JWT Bearer authentication and role-based access control (`SUPER_ADMIN`, `CONTENT_APPROVER`).

| Endpoint | Method | Role | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/admin/documents/upload` | `POST` | Approver, Admin | Multipart PDF upload with SHA-256 deduplication and async queue. |
| `/api/v1/admin/documents/ingest-url` | `POST` | Approver, Admin | SSRF-defended website URL ingestion. |
| `/api/v1/admin/documents/jobs/{job_id}` | `GET` | Staff | Ingestion job progress, status, and error monitoring. |
| `/api/v1/admin/documents/{doc_id}/versions/{version_id}/preview` | `GET` | Approver, Admin | Preview extracted text and page counts prior to approval. |
| `/api/v1/admin/documents/{doc_id}/versions/{version_id}/approve` | `POST` | Approver, Admin | Approves version and triggers background pgvector embedding. |
| `/api/v1/admin/documents/{doc_id}/versions/{version_id}/reject` | `POST` | Approver, Admin | Rejects version and marks it `FAILED`. |
| `/api/v1/admin/documents/{doc_id}/replace` | `POST` | Approver, Admin | Stages new version without deactivating current active version. |
| `/api/v1/admin/documents/{doc_id}/archive` | `POST` | Approver, Admin | Archives document and excludes all versions from search. |
| `/api/v1/admin/documents/{doc_id}/download` | `GET` | Staff | Secure PDF download with nosniff attachment headers. |

---

## 5. Security Architecture

### 5.1 Authentication & Role-Based Authorization
- `require_roles([UserRole.SUPER_ADMIN, UserRole.CONTENT_APPROVER])` guards all upload, approval, replacement, and archival endpoints.
- Unauthenticated requests receive `401 Unauthorized`.
- Non-administrative roles (e.g., `SUPPORT_AGENT`) receive `403 Forbidden`.

### 5.2 Server-Side Request Forgery (SSRF) Defense
The URL ingestion service (`WebScraperService`) implements strict multi-layer SSRF defenses:
1. **Scheme Restrictions**: Only `http` and `https` permitted. Schemes like `file://`, `ftp://`, `gopher://`, `dict://`, and `data:` are blocked.
2. **DNS IP Resolution**: The hostname is resolved via `socket.getaddrinfo`.
3. **Network Filtering**: Every resolved IP address is verified using Python `ipaddress`. The system blocks:
   - Loopback addresses (`127.0.0.0/8`, `::1`)
   - Private networks (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `fc00::/7`)
   - Link-local addresses (`169.254.0.0/16`, `fe80::/10`)
   - Cloud metadata endpoints (`169.254.169.254`, `metadata.google.internal`)
   - Multicast, broadcast, reserved, and unspecified IPs.
4. **Manual Redirect Re-validation**: Redirects are not followed blindly. On every HTTP 301/302/307/308 redirect, the `Location` header is parsed and re-validated against all SSRF rules before making the next connection.
5. **Download Caps & Timeouts**: Maximum 5 MB download limit and strict 5s connect / 10s read timeouts.

### 5.3 Secure File Handling
- **Magic Bytes Validation**: All uploaded PDFs must begin with `%PDF` (first 4 bytes). Non-PDF files are rejected with `400 Bad Request`.
- **Untrusted Filenames Discarded**: User-provided filenames are never used for disk storage paths. Safe UUID filenames are generated:
  `storage/documents/<document_id>/v<version_number>_<uuid_suffix>.pdf`
- **Execution Prevention**: The download endpoint forces `Content-Type: application/pdf`, `Content-Disposition: attachment`, and `X-Content-Type-Options: nosniff`.

---

## 6. Replacement Safety Guarantees

When replacing an existing institutional document:
1. Version 1 is currently `ACTIVE`.
2. Administrator uploads replacement -> Version 2 is staged in `UPLOADED` state.
3. Version 1 remains **online and active** for student queries.
4. Version 2 transitions through `PROCESSING` -> `REVIEW_REQUIRED`. Version 1 remains **online and active**.
5. Staff reviews and approves Version 2 -> Version 2 transitions to `INDEXING`.
6. Only when pgvector chunking and embedding generation complete with 100% success does Version 2 transition to `ACTIVE`, while Version 1 transitions to `ARCHIVED`.
7. **Failure Isolation**: If Version 2 fails extraction, fails OCR, fails indexing, or is rejected by staff:
   - Version 2 transitions to `FAILED`.
   - Version 1 is **completely untouched** and remains `ACTIVE` with zero loss of availability.

---

## 7. RAG Gating & Retrieval Guarantees

The RAG orchestration engine (`rag_service.search_evidence`) enforces strict SQL gating:
```sql
SELECT c.id, c.content, d.title, v.version_number, ay.code, similarity
FROM document_chunks c
JOIN documents d ON c.document_id = d.id
JOIN document_versions v ON (c.version_id = v.id OR (c.version_id IS NULL AND d.active_version_id = v.id))
JOIN academic_years ay ON d.academic_year_id = ay.id
WHERE d.status IN ('ACTIVE', 'PUBLISHED')
  AND v.status IN ('ACTIVE', 'PUBLISHED')
  AND d.active_version_id = v.id
  AND (v.valid_from IS NULL OR v.valid_from <= CURRENT_DATE)
  AND (v.valid_until IS NULL OR v.valid_until >= CURRENT_DATE)
ORDER BY similarity DESC
LIMIT 5;
```
This guarantees that unapproved, indexing, failed, archived, or expired documents cannot leak into student answers.
