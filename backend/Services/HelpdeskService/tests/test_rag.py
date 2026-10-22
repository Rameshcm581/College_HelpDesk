# backend/Services/HelpdeskService/tests/test_rag.py
import pathlib
import pytest
from httpx import AsyncClient
from unittest.mock import patch

from resources.pdfService import pdf_service
from resources.aiService import (
    get_embedding_provider,
    get_llm_provider,
    MockLLMProvider,
)
from configs.base_config import BaseConfig

SAMPLE_PDF_PATH = pathlib.Path(__file__).resolve().parents[3] / "storage" / "demo_college_regulations_2025_2026.pdf"


# ── UNIT TESTS ───────────────────────────────────────────────────────────────

def test_pdf_extraction_page_preservation():
    """Requirement 1 & 2: Extract text from PDF while strictly preserving page numbers and metadata."""
    assert SAMPLE_PDF_PATH.exists(), f"Sample PDF missing at {SAMPLE_PDF_PATH}"
    pdf_bytes = SAMPLE_PDF_PATH.read_bytes()
    pages = pdf_service.extract_pages(pdf_bytes)
    assert len(pages) == 3, f"Expected 3 pages in sample PDF, got {len(pages)}"

    for page in pages:
        assert page.page_number in [1, 2, 3]
        assert len(page.text) > 100
        assert page.char_count > 0

    # Page 1 contains Admissions & Tuition
    assert "ADMISSION" in pages[0].text.upper()
    # Page 2 contains Hostel Regulations
    assert "HOSTEL" in pages[1].text.upper()
    # Page 3 contains Examinations & Attendance
    assert "EXAMINATION" in pages[2].text.upper()


def test_structure_aware_chunking():
    """Requirement 3: Divide text into chunks while preserving page numbers and section boundaries."""
    pdf_bytes = SAMPLE_PDF_PATH.read_bytes()
    pages = pdf_service.extract_pages(pdf_bytes)
    chunks = pdf_service.chunk_document(
        pages=pages,
        document_title="[DEMONSTRATION SAMPLE] St. Jude College Regulations 2025-2026",
        academic_year="2025-2026",
        department="GENERAL",
    )
    assert len(chunks) >= 3

    for chunk in chunks:
        assert chunk.page_number in [1, 2, 3]
        assert chunk.token_count > 0
        assert len(chunk.content.strip()) > 50
        assert chunk.metadata.get("academic_year") == "2025-2026"


@pytest.mark.asyncio
async def test_configurable_embedding_provider():
    """Requirement 4: Embeddings generated through a configurable provider with 1536 unit dimensions."""
    provider = get_embedding_provider()
    embedding = await provider.get_embedding("What is the hostel caution deposit fee?")
    assert len(embedding) == BaseConfig.EMBEDDING_DIMENSION  # 1536
    # Verify L2 unit normalization
    norm = sum(x * x for x in embedding) ** 0.5
    assert abs(norm - 1.0) < 1e-4


# ── INTEGRATION TESTS: RAG TEST SUITE (CASES A - F) ─────────────────────────

@pytest.mark.asyncio
async def test_case_a_question_answered_by_pdf(async_client: AsyncClient):
    """TEST CASE A: A question answered by the PDF.
    Verifies that the chatbot answers using retrieved evidence from the approved document.
    """
    payload = {
        "query": "What is the hostel caution deposit fee?",
        "language": "en",
        "academic_year": "2025-2026",
    }
    resp = await async_client.post("/api/v1/public/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["fallback_triggered"] is False
    assert data["confidence_score"] >= BaseConfig.RAG_CONFIDENCE_THRESHOLD
    assert "5,000" in data["response"] or "5000" in data["response"]
    assert len(data["citations"]) >= 1
    assert data["citations"][0]["document_title"] is not None


@pytest.mark.asyncio
async def test_case_b_question_with_no_answer_fallback(async_client: AsyncClient):
    """TEST CASE B: A question for which the PDF contains no answer.
    Verifies that when evidence is insufficient, it triggers a safe refusal and suggests a ticket.
    """
    payload = {
        "query": "Who won the 1994 FIFA world cup tournament in soccer?",
        "language": "en",
        "academic_year": "2025-2026",
    }
    resp = await async_client.post("/api/v1/public/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["fallback_triggered"] is True
    assert data["confidence_score"] < BaseConfig.RAG_CONFIDENCE_THRESHOLD
    assert len(data["citations"]) == 0
    assert "could not find verified official documentation" in data["response"]
    assert data["suggested_ticket"] is not None
    assert data["suggested_ticket"]["default_category"] == "GENERAL"


@pytest.mark.asyncio
async def test_case_c_question_matching_multiple_passages(async_client: AsyncClient):
    """TEST CASE C: A question that could match multiple passages.
    Verifies queries covering campus fees match both tuition and hostel records appropriately.
    """
    payload = {
        "query": "What are the rules regarding late fee penalties and payment schedules?",
        "language": "en",
        "academic_year": "2025-2026",
    }
    resp = await async_client.post("/api/v1/public/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["fallback_triggered"] is False
    assert len(data["citations"]) >= 1
    cited_pages = [c["page_number"] for c in data["citations"]]
    assert any(p in [1, 2] for p in cited_pages)


@pytest.mark.asyncio
async def test_case_d_query_referring_to_specific_fee_or_date(async_client: AsyncClient):
    """TEST CASE D: A query referring to a specific fee or date.
    Verifies precise factual extraction of fees and deadlines without guessing.
    """
    payload = {
        "query": "What is the fee and deadline for semester examination revaluation?",
        "language": "en",
        "academic_year": "2025-2026",
    }
    resp = await async_client.post("/api/v1/public/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert data["fallback_triggered"] is False
    assert "750" in data["response"]
    assert "10 days" in data["response"]
    assert data["citations"][0]["page_number"] == 3


@pytest.mark.asyncio
async def test_case_e_unavailable_ai_service_safe_fallback(async_client: AsyncClient):
    """TEST CASE E: An unavailable or incorrectly configured AI service.
    Verifies that if the LLM provider throws an exception (e.g. gateway timeout or auth error),
    the system safely catches it and returns a polite fallback message with a support ticket.
    """
    with patch("resources.ragService.get_llm_provider") as mock_get_llm:
        mock_llm = MockLLMProvider()
        async def failing_llm(*args, **kwargs):
            raise RuntimeError("503 Service Unavailable: AI Provider upstream timeout")
        mock_llm.generate_grounded_answer = failing_llm
        mock_get_llm.return_value = mock_llm

        payload = {
            "query": "What is the hostel caution deposit fee?",
            "language": "en",
            "academic_year": "2025-2026",
        }
        resp = await async_client.post("/api/v1/public/chat", json=payload)
        assert resp.status_code == 200
        data = resp.json()["data"]

        # Safe fallback must be triggered, no 500 crash
        assert data["fallback_triggered"] is True
        assert data["confidence_score"] == 0.0
        assert "error" in data["response"].lower() or "support ticket" in data["response"].lower()
        assert data["suggested_ticket"] is not None


@pytest.mark.asyncio
async def test_case_f_citation_points_to_actual_source_page(async_client: AsyncClient):
    """TEST CASE F: A citation that must point to the actual source page.
    Verifies that citations point to:
    - Page 1 for Tuition / Admission fees
    - Page 2 for Hostel Caution Deposit & Mess
    - Page 3 for Attendance & Examination rules
    """
    test_specs = [
        ("How much is the B.E. Computer Science annual tuition fee and when is the admission deadline?", 1),
        ("What is the hostel caution deposit fee?", 2),
        ("What is the fee and deadline for semester examination revaluation?", 3),
    ]

    for query, expected_page in test_specs:
        resp = await async_client.post(
            "/api/v1/public/chat",
            json={"query": query, "language": "en", "academic_year": "2025-2026"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert data["fallback_triggered"] is False, f"Query '{query}' unexpectedly triggered fallback."
        assert len(data["citations"]) >= 1, f"Query '{query}' produced no citations."
        top_citation = data["citations"][0]
        assert top_citation["page_number"] == expected_page, (
            f"Query '{query}' cited Page {top_citation['page_number']}, expected Page {expected_page}."
        )
        assert top_citation["document_title"] is not None
        assert top_citation["version_number"] >= 1
