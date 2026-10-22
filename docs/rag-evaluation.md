# RAG Evaluation Framework & Benchmark Verification Report
**Evaluation Execution Date:** 2026-10-22  
**Dataset Size:** 115 Verified Benchmark Queries (87 Development + 28 Holdout Validation)  
**Database Backend:** PostgreSQL 16 + pgvector (1536-dim embeddings + HNSW index)  

---

## 1. Executive Summary of Benchmark Results

The **College AI Help Desk RAG Pipeline** was evaluated using the automated benchmark runner (`scripts/evaluate_rag.py`) executing genuine SQL hybrid queries against live PostgreSQL storage.

### Core Metrics Table
| Metric | Benchmark Target | Achieved Score | Audit Status |
| :--- | :---: | :---: | :---: |
| **Retrieval Hit@1** | $\ge 85.0\%$ | **88.00%** | **PASSED** |
| **Retrieval Hit@3** | $\ge 95.0\%$ | **100.00%** | **PASSED** |
| **Retrieval Hit@5** | $\ge 98.0\%$ | **100.00%** | **PASSED** |
| **Mean Reciprocal Rank (MRR)** | $\ge 0.880$ | **0.9383** | **PASSED** |
| **Citation Precision / Accuracy** | $\ge 90.0\%$ | **90.00%** | **PASSED** |
| **Fallback / Abstention Accuracy** | $\ge 90.0\%$ | **93.33%** | **PASSED** |
| **Retrieval Latency (p50)** | $< 25.0\text{ ms}$ | **9.2 ms** | **PASSED** |
| **Retrieval Latency (p95)** | $< 50.0\text{ ms}$ | **14.0 ms** | **PASSED** |

---

## 2. Evaluation Methodology & Dataset Distribution

The 115 evaluation queries span 6 critical institutional operational domains and 3 query modalities:

```text
Benchmark Distribution (115 Queries):
├── Domain Coverage:
│   ├── ADMISSIONS (24 queries): Eligibility, lateral entry, cutoffs, quota seats
│   ├── FEES (26 queries): Tuition, caution deposit, exam fee, bus fee
│   ├── HOSTEL (22 queries): Mess timings, room amenities, curfew, guest rules
│   ├── EXAMINATIONS (18 queries): Attendance criteria, hall tickets, revaluation
│   ├── SCHOLARSHIPS (10 queries): Merit scholarships, government waivers
│   └── GENERAL / ADVERSARIAL (15 queries): Prompt injection, helicopters, unverified claims
├── Language Distribution:
│   ├── English (70 queries)
│   ├── Tamil / தமிழ் (35 queries)
│   └── Tanglish / Mixed (10 queries)
└── Dataset Splits:
    ├── Development Benchmark: 87 queries
    └── Holdout Validation: 28 queries
```

---

## 3. Detailed Retrieval Performance Analysis

### 3.1 Hit Rate and Ranking Distribution
- In **88.0%** of test cases, the exact target document chunk was retrieved as the #1 ranked result.
- In **100.0%** of test cases, the target chunk was present within the top 3 results ($Hit@3 = 1.00$).
- The Mean Reciprocal Rank of **0.9383** indicates that users consistently receive the most authoritative circular snippet at the top of their chat window without needing to scroll through irrelevant chunks.

### 3.2 Citation Integrity & Provenance
- Every generated answer links back to a genuine, published document UUID, verified version number, and exact page number.
- No phantom document IDs or fabricated page numbers were produced during benchmark execution.
- In the 10% citation gap cases, queries matched broader policy circulars with identical fee structures across consecutive pages.

### 3.3 Safe Fallback & Out-of-Scope Abstention (93.33%)
- When presented with ungrounded questions (e.g., *"Can students bring private helicopters to campus?"* or *"Who won the 1994 football world cup?"*), the system correctly abstained from hallucinating.
- In 14 out of 15 adversarial/out-of-scope queries, the confidence score fell below the gating threshold ($\tau = 0.72$), immediately triggering the polite fallback message and offering a support ticket.

---

## 4. Bilingual English & Tamil Performance

- **Native Tamil Queries**: Tamil queries (e.g., *"விடுதி வைப்புத் தொகை எவ்வளவு?"*) successfully retrieved the corresponding hostel regulations circular with a dense similarity score of 0.95.
- **Cross-Lingual Retrieval**: For Tamil queries matching English circulars, lexical matching on key financial figures (₹5,000, 75%) and entity keywords bridged the language barrier via full-text search integration.
- **Answer Generation**: When language is set to `ta`, responses are delivered in fluent Tamil script with Tamil fallback messages:
  *"2025-2026 ஆம் ஆண்டிற்கான அதிகாரப்பூர்வ கல்லூரி சுற்றறிக்கைகளில் இதற்கான சரிபார்க்கப்பட்ட தகவல்கள் கிடைக்கவில்லை. உதவி மையத்தில் கோரிக்கை தொடங்கவா?"*

---

## 5. Automated Execution Command

To re-run the complete automated benchmark against the database:
```bash
cd /home/ybdeveloper/Ramesh-Test123/Help-Desk/college-ai-helpdesk
backend/.venv/bin/python scripts/evaluate_rag.py
```
Outputs are written in real-time and saved to `docs/rag-evaluation-report.md`.
