# System Architecture Specification: College AI Help Desk

## 1. High-Level Architectural Blueprint

The **College AI Help Desk** uses a decoupled, event-driven, micro-modular architecture designed for high availability, low-latency conversational inference, and strict security isolation between public visitors and authenticated college staff.

```mermaid
graph TB
    subgraph ClientLayer["Client & Integration Layer"]
        HostWebsite["College Public Website<br/>(WordPress / HTML / React)"]
        WidgetBundle["Embeddable Chatbot Widget<br/>(Vanilla JS / Shadow DOM / React Standalone)"]
        AdminDashboard["College Admin & Staff Portal<br/>(React + Vite + TypeScript)"]
        HostWebsite -->|Embeds via script tag| WidgetBundle
    end

    subgraph EdgeLayer["Edge / Ingress Layer"]
        ReverseProxy["Nginx Reverse Proxy & Load Balancer<br/>(SSL, Rate Limiting, Static Caching)"]
        WidgetBundle -->|HTTPS / WSS| ReverseProxy
        AdminDashboard -->|HTTPS / WSS| ReverseProxy
    end

    subgraph AppLayer["Application Layer (FastAPI Backend)"]
        APIGateway["FastAPI Core Engine<br/>(Uvicorn ASGI Workers)"]
        PublicRouter["/api/v1/public<br/>(Chat, Tickets, Fallbacks)"]
        AdminRouter["/api/v1/admin<br/>(Docs, Users, Analytics, RBAC)"]
        AuthModule["Security & Auth<br/>(JWT, Argon2id, RBAC Policy)"]
        RAGModule["RAG Orchestrator<br/>(Intent, Hybrid Retrieval, Prompting)"]
        TicketModule["Ticket Manager<br/>(CRUD, SLAs, Notification Dispatch)"]

        ReverseProxy -->|/api/v1/public/*| PublicRouter
        ReverseProxy -->|/api/v1/admin/*| AdminRouter
        PublicRouter --> RAGModule
        PublicRouter --> TicketModule
        AdminRouter --> AuthModule
        AdminRouter --> TicketModule
    end

    subgraph AsyncLayer["Async Processing & Messaging Layer"]
        RedisServer["Redis 7 (In-Memory Broker & Cache)<br/>- Rate Limiting Tokens<br/>- Task Queues (Celery/ARQ)<br/>- Session Cache"]
        WorkerService["Background Worker Container<br/>(Celery / PyWorker Pool)"]
        OCREngine["Tesseract OCR Engine<br/>(English + Tamil models)"]
        PDFParser["PyMuPDF / pdfplumber<br/>Document Extraction"]

        APIGateway -->|Enqueue Jobs| RedisServer
        RedisServer -->|Dequeue Jobs| WorkerService
        WorkerService --> PDFParser
        PDFParser --> OCREngine
    end

    subgraph DataLayer["Storage & Vector Database"]
        PostgresDB[("PostgreSQL 16 + pgvector<br/>- Relational: Users, Tickets, Audits<br/>- Inverted Indexes: tsvector English/Tamil<br/>- Vector Indexes: HNSW cos/inner_product")]
        BlobStore[("Document Storage<br/>(Local Encrypted Volume / S3 Compatible)")]

        RAGModule -->|Hybrid Query| PostgresDB
        WorkerService -->|Insert Chunks & Vectors| PostgresDB
        WorkerService -->|Read/Store Originals| BlobStore
        AdminRouter -->|Upload File| BlobStore
    end

    subgraph ExternalServices["External Cloud APIs"]
        OpenAIAPI["OpenAI API<br/>- Chat: gpt-4o / gpt-4o-mini<br/>- Embeddings: text-embedding-3-small"]
        SMTPServer["Institutional SMTP / Mail Relay<br/>(Ticket Receipts & Staff Alerts)"]

        RAGModule -->|Embed Query & Generate Answer| OpenAIAPI
        WorkerService -->|Embed Batch Chunks| OpenAIAPI
        WorkerService -->|Send Notification Emails| SMTPServer
    end
```

---

## 2. Component Decoupling & Isolation

### 2.1 Public Chatbot Widget vs. Protected Admin Dashboard
1. **Public Widget**:
   - **Isolation**: Compiled into a single, zero-dependency bundle (`widget.js`) with styles encapsulated inside a **Shadow DOM** (`AttachShadow({ mode: 'closed' })`). This guarantees that the host college website's CSS cannot distort the widget, nor can the widget leak styles into the parent page.
   - **Authentication**: Zero authentication requirements. Communication uses an ephemeral `session_id` (UUIDv4) stored in browser `sessionStorage`.
   - **Surface Area**: Can only reach public endpoints:
     - `POST /api/v1/public/chat`
     - `POST /api/v1/public/tickets`
     - `GET /api/v1/public/health`
2. **Protected Admin Dashboard**:
   - **Isolation**: Served from a dedicated subpath (`/admin/`) or distinct administrative subdomain (`admin.college.edu`).
   - **Authentication**: Strict cookie-based or bearer-token-based JWT with Argon2id credentials, CSRF tokens, and role-based claim checks.
   - **Surface Area**: Complete administrative control: Document uploads, version approvals, vector re-indexing, user lifecycle, ticket triage, and system telemetry.

---

## 3. RAG Pipeline Architecture

The Retrieval-Augmented Generation pipeline is engineered to balance sub-second retrieval speeds, cross-lingual precision (Tamil and English), and strict citation grounding.

```mermaid
sequenceDiagram
    autonumber
    actor User as Student / Parent
    participant Widget as Public Widget
    participant API as FastAPI (RAG Orchestrator)
    participant Redis as Redis Cache
    participant DB as Postgres + pgvector
    participant OpenAI as OpenAI API

    User->>Widget: Enter question (e.g., "கல்லூரி விடுதிக் கட்டணம் என்ன?")
    Widget->>API: POST /api/v1/public/chat { query, session_id, lang }
    API->>API: 1. Input Sanitization & Jailbreak Guardrails
    API->>API: 2. Language & Intent Detection (Tamil detected)
    API->>Redis: Check Semantic Cache for identical query
    alt Semantic Cache Hit
        Redis-->>API: Cached answer + verified citations
    else Cache Miss
        API->>OpenAI: Embed query via text-embedding-3-small (1536 dim)
        OpenAI-->>API: Dense vector embedding
        API->>DB: Execute Hybrid Search:<br/>- Vector HNSW cosine search (top 30)<br/>- tsvector Full-Text Search (top 30)<br/>- Metadata filter: status='PUBLISHED' & year='2025-2026'
        DB-->>API: 30 Candidate document chunks with metadata
        API->>API: Reciprocal Rank Fusion (RRF) & Confidence Scoring
        alt Confidence Score < Threshold (0.72)
            API-->>Widget: "Reliable official records were not found. Would you like to create a ticket?"
        else Confidence Score >= 0.72
            API->>OpenAI: Stream chat completion with Grounded Prompt + Document Chunks
            OpenAI-->>API: Streamed tokens + Markdown citations [Doc: Hostel-Rules-2025.pdf, Page 12]
            API-->>Widget: Server-Sent Events (SSE) token stream
            API->>DB: Log conversation query, retrieved chunks, token count, and latency
        end
    end
    Widget-->>User: Render verified answer with citation cards
```

---

## 4. Document Ingestion, Parsing & OCR Pipeline

The ingestion pipeline converts disparate institutional documents into clean, chunked, searchable knowledge vectors.

```mermaid
flowchart TD
    A[Admin Uploads Document<br/>PDF, Scanned Image, DOCX] --> B[Store Raw File in Blob/Local Storage<br/>Assign UUID & Academic Year]
    B --> C[Create Document Record in DB<br/>Status: PENDING_PROCESSING]
    C --> D[Enqueue Ingestion Task in Redis Queue]
    D --> E[Worker Service Picks Task]
    
    E --> F{Is Document Scanned?}
    F -->|Yes: Pure Image or Scanned PDF| G[Render Pages to 300 DPI Images<br/>pdftoppm]
    G --> H[Run Tesseract OCR<br/>Languages: eng + tam]
    H --> I[Extract Text with Bounding Boxes & Confidence]
    
    F -->|No: Native Digital PDF / DOCX| J[Extract Digital Text & Tables<br/>PyMuPDF / pdfplumber]
    
    I --> K[Text Normalization & Cleansing<br/>- Remove artifact characters<br/>- Fix Tamil Unicode ligature breaks<br/>- Strip headers/footers]
    J --> K
    
    K --> L[Hierarchical & Semantic Chunking<br/>500-800 tokens, 100 token overlap<br/>Inject metadata: Title, Dept, Academic Year, Page]
    
    L --> M[Batch Embedding Generation<br/>OpenAI text-embedding-3-small]
    M --> N[Store Chunks & Embeddings in Postgres pgvector]
    N --> O[Generate tsvector full-text search index tokens]
    O --> P[Update Document Status:<br/>PENDING_REVIEW or APPROVED]
    P --> Q[Notify Approver via Email / Admin Dashboard]
```

### 4.1 Chunking Strategy
- **Token Target**: 500 to 800 tokens per chunk.
- **Overlap**: 100 to 120 tokens (15–20%) to preserve cross-boundary semantic context.
- **Context Injection**: Each chunk is prepended with standard structural metadata before vectorization:
  ```text
  [DOCUMENT: B.E. Regulations 2025-2026]
  [DEPARTMENT: Academic Affairs]
  [SECTION: 4.2 Attendance and Condonation Rules]
  [PAGE: 14]
  ---
  <Extracted chunk text content>
  ```
- **Table Preservation**: Tables in fee circulars and exam schedules are extracted and serialized into clean GitHub-flavored Markdown tables to preserve column-row relationships in both vector and keyword representations.

---

## 5. Background Processing: Worker Architecture

### 5.1 Decision: Celery vs. ARQ
- **Decision**: **Celery with Redis Broker and SQLAlchemy Result Backend**.
- **Rationale**:
  1. Celery provides battle-tested worker pooling (`prefork` or `gevent`), task rate-limiting, and task routing.
  2. Heavy CPU/memory tasks (PyMuPDF rendering, Tesseract OCR for 50-page PDFs) benefit from pre-forked worker processes separate from async I/O web servers.
  3. Built-in support for retries with exponential backoff, dead-letter queues, and task monitoring via Flower or Prometheus metrics.
- **Task Queues**:
  - `queue_ingestion`: High-memory, CPU-bound PDF parsing, OCR, and embedding generation.
  - `queue_notifications`: Low-latency I/O tasks for SMTP email delivery.
  - `queue_maintenance`: Periodic background tasks (e.g., pruning old guest chat logs, refreshing search statistics).

---

## 6. Hybrid Vector & Full-Text Search Architecture

1. **Dense Vector Search**:
   - `pgvector` extension configured with **HNSW (Hierarchical Navigable Small World)** indexing.
   - Distance metric: Cosine distance (`vector_cosine_ops`) or Inner Product on normalized vectors.
   - HNSW parameters: `m = 16`, `ef_construction = 64` for high recall ($> 98\%$) and low query latency ($< 15\text{ ms}$).
2. **Sparse Lexical Search**:
   - PostgreSQL native `tsvector` with `tsquery`.
   - Dual dictionaries: PostgreSQL English dictionary + custom simple/Tamil lexeme tokenization.
   - GIN index on `search_vector` for millisecond keyword lookups (e.g., exact course codes "CS8501", fee amounts "₹45,000", or faculty names).
3. **Reciprocal Rank Fusion (RRF)**:
   For every candidate chunk $d$:
   $$\text{RRF Score}(d) = \frac{1}{k + \text{Rank}_{\text{dense}}(d)} + \frac{1}{k + \text{Rank}_{\text{sparse}}(d)}$$
   where $k = 60$. Chunks are sorted by descending RRF score, and the top $N=5$ chunks are passed to the reranking/prompt context window.

---

## 7. Multilingual Strategy (English & Tamil)

1. **Input Detection**: Fast lightweight language identification (`langdetect` or fast regex/unicode script detection for Tamil unicode block `\u0B80-\u0BFF`).
2. **Query Normalization**:
   - Pure Tamil queries: Cleaned and normalized to standard Tamil Unicode NFC form.
   - Tanglish (Tamil written in Latin script, e.g., "Hostel fees evvalavu?"): Detected via prompt instructions; the LLM normalizes intent into both Tamil and English retrieval search terms before running hybrid search.
3. **Grounding & Answering**:
   - The LLM is instructed: *"Respond in the exact language or dialect specified by the user (Tamil script for Tamil queries, English for English queries). Use only the verified context. Do not invent any facts."*
4. **OCR**: Tesseract OCR loaded with dual language flags `-l eng+tam` so circulars featuring bilingual headings and Tamil government directives are transcribed without corrupted glyphs.

---

## 8. Network, Reverse Proxy & Caching Strategy

```text
Internet / Client Requests
        │
        ▼
[ Nginx Reverse Proxy / Port 80 & 443 ]
   ├── Rate Limiter Zone: 15 req/min per IP on /api/v1/public/chat
   ├── SSL Termination (TLS 1.3, HSTS)
   ├── Static Asset Cache: widget.js (Cache-Control: public, max-age=3600, stale-while-revalidate)
   ├── Routing /widget/* -> Static bundle
   ├── Routing /admin/*  -> React Admin SPA (index.html fallback)
   └── Routing /api/*    -> FastAPI ASGI Cluster (Uvicorn: 4 workers)
```

- **Semantic Cache in Redis**: Query hashes and high-similarity questions ($> 0.98$ embedding cosine similarity) have their generated responses cached with a 12-hour TTL. Any document update triggers an immediate cache invalidation for the affected department/academic year.

---

## 9. Backend Directory & Codebase Layout (Referenced from ARC100 Pattern)

To maintain clean modular boundaries and align with the proven engineering standards from `/home/ybdeveloper/Ramesh-Test123/ARC100/code/backend`, the backend is organized into a modular service topology:

```text
backend/
├── docker-compose.yml              # Local and production multi-container orchestration
├── Dockerfile                      # Web API container build
├── Dockerfile.worker               # Celery worker container with Tesseract & Poppler
├── requirements.txt                # Root-level pinned dependencies
├── scripts/                        # Operational and maintenance automation
│   ├── start_all.sh                # Boot backend, worker, DB, and redis
│   ├── stop_all.sh                 # Graceful shutdown script
│   ├── backup.sh                   # Automated pg_dump snapshot script
│   ├── restore_drill.sh            # Backup restoration verification test
│   ├── smoke_test.sh               # Health check and ping test suite
│   └── lint_all.sh                 # flake8 / black / ruff / mypy check
├── backups/                        # Local snapshot storage (.dump files)
├── docs/                           # Architecture, database schema, and API specs
├── logs/                           # Runtime log sinks (api_gateway.log, worker.log)
└── Services/
    └── HelpdeskService/            # Core backend application package
        ├── main.py                 # FastAPI initialization, lifespan DB init, CORS, error handlers
        ├── Dockerfile              # Service-specific build definition
        ├── requirements.txt        # Service Python dependencies
        ├── pytest.ini              # Pytest configuration
        ├── configs/                # Environment-driven configuration hierarchy
        │   ├── __init__.py
        │   ├── base_config.py      # Base settings (JWT expiry, model names, defaults)
        │   ├── dev_config.py       # Development environment overrides
        │   └── local_config.py     # Local developer overrides
        ├── models/                 # SQLAlchemy 2.0 ORM Declarative Models
        │   ├── __init__.py         # Base, async engine, and sessionmaker exports
        │   └── models.py           # Users, Documents, Chunks, Tickets, Messages, Audits
        ├── resources/              # Controller & Service domain logic
        │   ├── __init__.py
        │   ├── authController.py   # Login, refresh, logout, password verification
        │   ├── chatController.py   # Public chat query & SSE streaming handler
        │   ├── documentController.py # Ingestion, approval, and archive workflows
        │   ├── ticketController.py # Ticket CRUD, triage, and message threads
        │   ├── analyticsController.py # Token usage, query clustering, cost metrics
        │   ├── aiService.py        # OpenAI API client, embeddings, prompt construction
        │   ├── ragService.py       # RRF hybrid search, confidence evaluation (τ ≥ 0.72)
        │   ├── ocrService.py       # Tesseract bilingual (eng + tam) & PDF extraction
        │   ├── notificationService.py # SMTP email dispatch helper
        │   ├── schemas.py          # Pydantic v2 validation models
        │   ├── errors.py           # Standardized error classes and exception handlers
        │   └── utils.py            # Argon2id password hashing, JWT generation, PII masking
        ├── routes/                 # Route registrations & path prefixes
        │   └── __init__.py         # Maps /api/v1/public/*, /api/v1/admin/*, /api/auth/*
        └── tests/                  # Automated pytest test suites
            ├── __init__.py
            ├── conftest.py         # Test fixtures, mock DB session, test client
            ├── test_auth.py        # Authentication & RBAC test cases
            ├── test_chat.py        # Chat queries & fallback trigger tests
            ├── test_documents.py   # Document upload, chunking & approval tests
            ├── test_tickets.py     # Ticket workflows and email notification tests
            ├── test_hybrid_search.py # pgvector HNSW + tsvector RRF search tests
            └── test_rag_eval.py    # Faithfulness and citation precision benchmarks
```

