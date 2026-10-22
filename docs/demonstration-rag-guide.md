# Demonstration RAG Vertical Slice Guide: College AI Help Desk

> **IMPORTANT DISCLAIMER — DEMONSTRATION PROTOTYPE**  
> All college regulations, department names, fee amounts, deadlines, and circulars referenced in this demonstration pipeline and test suite are **fictional demonstration samples** (`[DEMONSTRATION SAMPLE] St. Jude College Academic & Campus Regulations 2025-2026`). They were created exclusively for RAG benchmarks and offline verification. **Never represent this sample data as official college information.**

---

## 1. Overview of the RAG Vertical Slice

The first end-to-end vertical slice proves that a user can ask questions about an approved institutional document and receive an answer supported strictly by retrieved evidence, accompanied by verified source citations (document title, version, and page number).

### Functional Architecture Workflow

```
[Approved PDF Document]
       │
       ▼ (scripts/generate_demo_pdf.py & resources/pdfService.py)
[PDF Text Extraction & Page Preservation] (pypdf: Pages 1, 2, 3)
       │
       ▼ (resources/pdfService.py)
[Structure-Aware Semantic Chunking] (1 chunk per page with metadata)
       │
       ▼ (resources/aiService.py: EmbeddingProvider)
[1536-Dimensional Vector Embeddings] (text-embedding-3-small or DeterministicMock)
       │
       ▼ (PostgreSQL 16 + pgvector)
[Storage in 'documents' & 'document_chunks'] (Vector Cosine Distance <=>)
       │
       ▼ (User asks Question in React UI or API)
[FastAPI /api/v1/public/chat Endpoint]
       │
       ▼ (resources/ragService.py)
[pgvector Cosine Similarity Retrieval & Threshold Gating (τ = 0.72)]
       ├── (Similarity < 0.72 or Insufficient Evidence) ──► [Safe Fallback & Support Ticket Prompt]
       └── (Similarity >= 0.72 with Evidence Chunks)   ──► [Grounded Answer & Citation Synthesis]
                                                                     │
                                                                     ▼
                                                      [React Frontend Displays Answer & Verified Citations]
```

---

## 2. Security & Anti-Hallucination Guarantees

1. **No Frontend API Key Exposure:**  
   The OpenAI API key is strictly maintained backend-side (`OPENAI_API_KEY` in `backend/.env`). The React client communicates solely via the backend proxy (`/api/v1/public/chat`), preventing any client-side credential leakage.
2. **Controlled Document Ingestion:**  
   Public users cannot upload arbitrary PDFs. Ingestion is restricted to controlled CLI administrative commands (`scripts/ingest_demonstration_pdf.py`) or authenticated admin routes with role-based access control.
3. **No Fabricated Citations:**  
   Citations are extracted directly from the actual retrieved `document_chunks` rows returned by PostgreSQL. If an answer cannot be grounded, no citation is generated.
4. **Independent Confidence Gating:**  
   The system does not rely on the LLM's self-reported confidence. It algorithmically computes the pgvector cosine distance:
   $$\text{Similarity} = 1.0 - (c.\text{embedding} \Leftrightarrow \text{query\_vector})$$
   If $\text{Similarity} < \tau$ (default $\tau = 0.72$), the query is immediately refused and routed to a support ticket recommendation.
5. **Safe Fallback Response:**  
   When evidence is missing or below threshold, the system returns a safe, polite refusal in English or Tamil explaining that the answer could not be verified from official records.

---

## 3. How to Ingest & Test a Demonstration PDF

### Step 1: Generate or Place the Approved PDF
To regenerate the 3-page fictional demonstration PDF:
```bash
# Run from repository root
backend/.venv/bin/python scripts/generate_demo_pdf.py
```
This generates:
`backend/storage/demo_college_regulations_2025_2026.pdf`
- **Page 1:** Admissions & Tuition Fees (B.E. Computer Science annual fee ₹85,000, deadline July 15, 2025).
- **Page 2:** Hostel Regulations & Mess Charges (Refundable Caution Deposit ₹5,000, deadline July 31, 2025, late fee ₹100/day).
- **Page 3:** Examinations & Attendance Regulations (Minimum 75% attendance, Condonation fee ₹1,500, Revaluation fee ₹750 within 10 days).

### Step 2: Ingest the PDF into PostgreSQL pgvector
Run the controlled development ingestion script:
```bash
backend/.venv/bin/python scripts/ingest_demonstration_pdf.py
```
**Output summary:**
```
=== [1/5] Checking Demonstration PDF ===
File size: 7293 bytes | SHA-256: 05c06f9e3950...
=== [2/5] Resolving Master Records (Academic Year, Dept, Admin) ===
=== [3/5] Extracting Pages and Creating Structure-Aware Chunks ===
Extracted 3 pages. Generated 3 semantic chunks.
=== [4/5] Generating Vector Embeddings ===
Generated 3 embedding vectors (1536 dim).
=== [5/5] Persisting Document and Vector Chunks to Database ===
Successfully ingested and indexed 3 chunks for document: [DEMONSTRATION SAMPLE] St. Jude College Academic & Campus Regulations 2025-2026
```

---

## 4. Test Case Verification Matrix (Cases A – F)

All 6 required test cases are automated in `backend/Services/HelpdeskService/tests/test_rag.py`.

| Test Case | Scenario Description | Query Tested | Expected Result | Verified Status |
|:---|:---|:---|:---|:---:|
| **Case A** | Question answered by the PDF | *"What is the hostel caution deposit fee?"* | `fallback=False`, confidence $\ge 0.72$, contains `₹5,000`, 1 citation | **PASSED** |
| **Case B** | Question with no answer in PDF | *"Who won the 1994 FIFA world cup?"* | `fallback=True`, confidence $< 0.10$, safe refusal, suggested ticket | **PASSED** |
| **Case C** | Question matching multiple passages | *"What are the rules regarding late fee penalties and payment schedules?"* | `fallback=False`, matches tuition (Page 1) or hostel (Page 2) | **PASSED** |
| **Case D** | Query referring to specific fee or date | *"What is the fee and deadline for semester examination revaluation?"* | `fallback=False`, contains `₹750` and `10 days`, cites Page 3 | **PASSED** |
| **Case E** | Unavailable or misconfigured AI service | Simulated upstream LLM 503 error | `fallback=True`, `confidence=0.0`, graceful refusal, ticket suggested | **PASSED** |
| **Case F** | Citation points to actual source page | Page 1 (Tuition), Page 2 (Hostel), Page 3 (Exams) | `citation[0].page_number` strictly equals `1`, `2`, and `3` | **PASSED** |

### Running the Automated Tests
```bash
# Backend pytest suite (18/18 tests)
cd backend/Services/HelpdeskService
PYTHONPATH=. ../../backend/.venv/bin/pytest -v

# Frontend vitest suite (2/2 tests)
cd frontend
npm test
```

---

## 5. Live Interactive Testing via React Chat Interface

1. **Start Services:**
   - Database & Redis: `docker compose up -d`
   - FastAPI Backend (Port 8005):
     ```bash
     cd backend/Services/HelpdeskService
     PYTHONPATH=. ../../backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8005
     ```
   - React Frontend (Port 5175):
     ```bash
     cd frontend
     npm run preview -- --port 5175 --host 127.0.0.1
     ```

2. **Open Browser:**  
   Navigate to `http://localhost:5175/`.

3. **Verify Interactive Scenarios:**
   - Click chip: *"What is the hostel caution deposit fee?"*  
     $\rightarrow$ Returns ₹5,000 caution deposit with verified citation card: `[DEMONSTRATION SAMPLE] St. Jude College Academic & Campus Regulations 2025-2026 • Page 2`.
   - Toggle language to **தமிழ்** and click: *"விடுதி வைப்புத் தொகை எவ்வளவு?"*  
     $\rightarrow$ Returns fluent Tamil grounded response citing Page 2.
   - Click chip: *"Who won the 1994 FIFA world cup?"*  
     $\rightarrow$ Refusal message displayed with amber fallback card and **"Create Ticket"** button.
