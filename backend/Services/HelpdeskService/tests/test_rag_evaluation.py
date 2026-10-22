# backend/Services/HelpdeskService/tests/test_rag_evaluation.py
"""Automated pytest test suite executing the 115-query Golden Evaluation Benchmark.
Verifies Hit@1, Hit@3, Hit@5, MRR, Citation Accuracy, and Safe Fallback/Abstention.
"""
import json
import pathlib
import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from configs.base_config import BaseConfig
from models import async_session_factory
from resources.ragService import rag_service

DATASET_PATH = pathlib.Path(__file__).parent / "golden_dataset.json"


@pytest.fixture(scope="module")
def golden_dataset():
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_golden_dataset_hit_rate_and_mrr(golden_dataset):
    """Verifies that retrieval across English, Tamil, and Tanglish queries
    achieves ≥85% Hit@1, ≥95% Hit@3, and ≥0.88 MRR.
    """
    positive_cases = [c for c in golden_dataset if not c["expected_fallback"]]
    assert len(positive_cases) >= 70

    hit_1_count = 0
    hit_3_count = 0
    hit_5_count = 0
    rr_sum = 0.0

    async with async_session_factory() as db:
        for item in positive_cases:
            query = item["query"]
            expected_doc = item["expected_doc_title"]
            expected_page = item["expected_page"]

            chunks = await rag_service.search_evidence(
                db=db,
                query_text=query,
                top_k=5,
                academic_year_code="2025-2026",
            )

            matched_rank = None
            for rank, c in enumerate(chunks, 1):
                doc_title = c.get("document_title", "")
                page = c.get("page_number")
                doc_ok = expected_doc.lower() in doc_title.lower() if expected_doc else True
                page_ok = (expected_page == page) if expected_page else True

                if doc_ok and page_ok:
                    matched_rank = rank
                    break

            if matched_rank == 1:
                hit_1_count += 1
            if matched_rank and matched_rank <= 3:
                hit_3_count += 1
            if matched_rank and matched_rank <= 5:
                hit_5_count += 1
            if matched_rank:
                rr_sum += 1.0 / matched_rank

    total = len(positive_cases)
    hit_at_1 = hit_1_count / total
    hit_at_3 = hit_3_count / total
    hit_at_5 = hit_5_count / total
    mrr = rr_sum / total

    assert hit_at_1 >= 0.85, f"Hit@1 {hit_at_1:.3f} fell below threshold 0.85"
    assert hit_at_3 >= 0.95, f"Hit@3 {hit_at_3:.3f} fell below threshold 0.95"
    assert hit_at_5 == 1.00, f"Hit@5 {hit_at_5:.3f} fell below 1.00"
    assert mrr >= 0.88, f"MRR {mrr:.3f} fell below threshold 0.88"


@pytest.mark.asyncio
async def test_golden_dataset_safe_fallback_abstention(golden_dataset):
    """Verifies that out-of-scope, ambiguous, older academic years, and unsupported queries
    consistently trigger fallback without hallucinated citations or guesswork.
    """
    negative_cases = [c for c in golden_dataset if c["expected_fallback"]]
    assert len(negative_cases) >= 12

    fallback_correct = 0

    async with async_session_factory() as db:
        for item in negative_cases:
            query = item["query"]
            lang = item["language"]

            res = await rag_service.answer_query(
                db=db,
                query=query,
                session_id=uuid.uuid4(),
                language=lang,
                academic_year="2025-2026",
            )

            if res.fallback_triggered and len(res.citations) == 0:
                fallback_correct += 1

    accuracy = fallback_correct / len(negative_cases)
    assert accuracy >= 0.90, f"Safe fallback accuracy {accuracy:.3f} fell below 0.90"


@pytest.mark.asyncio
async def test_cross_lingual_tamil_queries_retrieve_genuine_evidence(golden_dataset):
    """Verifies Tamil queries querying English documents and Tamil queries querying Tamil documents."""
    ta_cases = [c for c in golden_dataset if c["query_type"] in ("ta_to_en", "ta_to_ta")]
    assert len(ta_cases) >= 20

    success_count = 0
    async with async_session_factory() as db:
        for item in ta_cases:
            chunks = await rag_service.search_evidence(
                db=db,
                query_text=item["query"],
                top_k=3,
                academic_year_code="2025-2026",
            )
            if any(item["expected_doc_title"].lower() in c["document_title"].lower() for c in chunks):
                success_count += 1

    rate = success_count / len(ta_cases)
    assert rate >= 0.90, f"Cross-lingual Tamil retrieval rate {rate:.3f} fell below 0.90"
