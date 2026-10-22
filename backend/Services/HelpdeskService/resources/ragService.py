# backend/Services/HelpdeskService/resources/ragService.py
import datetime
import logging
import re
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from configs.base_config import BaseConfig
from models.models import (
    AcademicYears,
    ChatMessages,
    ChatSessions,
    Departments,
    DocumentChunks,
    DocumentStatus,
    DocumentVersions,
    Documents,
)
from resources.aiService import get_embedding_provider, get_llm_provider
from resources.multilingualService import multilingual_service
from resources.rerankerService import get_reranker
from resources.schemas import ChatQueryResponse, CitationItem, SuggestedTicket

logger = logging.getLogger(__name__)


class RAGOrchestrationService:
    """Enterprise RAG Orchestration Service with:
    - PostgreSQL Full-Text Keyword Search + pgvector Semantic Search (Hybrid Search)
    - Reciprocal Rank Fusion (RRF) and Lexical-Semantic Reranking
    - Strict Multi-Attribute Metadata Pre-Filtering (academic year, department, type, language, validity)
    - Multilingual & Transliterated Tamil (Tanglish) query expansion
    - Contradiction / Conflict detection between documents
    - Robust safety, abstention, and authentic citation grounding.
    """

    def __init__(self):
        self.confidence_threshold = BaseConfig.RAG_CONFIDENCE_THRESHOLD

    def _detect_conflicting_evidence(self, chunks: List[Dict[str, Any]]) -> Optional[str]:
        """Detects whether retrieved evidence contains conflicting policy statements
        or mismatched fee amounts across different documents.
        """
        if len(chunks) < 2:
            return None

        # Check for multiple distinct documents with contradictory fee figures for the same query
        fee_by_doc: Dict[str, set] = {}
        for c in chunks[:3]:
            doc_title = c.get("document_title", "")
            content = c.get("content", "")
            # Find currency figures like ₹85,000 or ₹95,000 or ₹5,000
            fees = set(re.findall(r'₹\s*[\d,]+', content))
            if fees:
                if doc_title not in fee_by_doc:
                    fee_by_doc[doc_title] = set()
                fee_by_doc[doc_title].update(fees)

        # If 2 distinct documents have completely disjoint fee figures for the same entity
        if len(fee_by_doc) >= 2:
            docs = list(fee_by_doc.keys())
            fees1 = fee_by_doc[docs[0]]
            fees2 = fee_by_doc[docs[1]]
            if fees1 and fees2 and fees1 != fees2:
                # Contradiction detected
                return f"Conflict detected between '{docs[0]}' ({', '.join(fees1)}) and '{docs[1]}' ({', '.join(fees2)})."

        return None

    def _is_ambiguous_query(self, query: str) -> bool:
        """Identifies overly vague queries that lack sufficient entity context."""
        cleaned = re.sub(r'[^\w\s]', '', query.strip().lower())
        tokens = cleaned.split()
        generic_queries = {
            "fee", "fees", "what is fee", "what is the fee", "fee details",
            "cost", "rules", "regulations", "admission", "college details",
            "கட்டணம்", "கட்டணம் எவ்வளவு", "விதிமுறைகள்"
        }
        return cleaned in generic_queries or (len(tokens) <= 2 and any(t in ["fee", "fees", "cost", "கட்டணம்"] for t in tokens))

    def _check_older_academic_year_request(self, query: str, active_academic_year: str = "2025-2026") -> Optional[str]:
        """Checks if query specifically asks for an older, unindexed/archived academic year."""
        years_found = re.findall(r'\b(201\d|202[0-4])-(20\d\d)\b', query)
        if years_found:
            year_match = f"{years_found[0][0]}-{years_found[0][1]}"
            if year_match != active_academic_year:
                return year_match
        return None

    async def search_evidence(
        self,
        db: AsyncSession,
        query_text: str,
        top_k: int = 5,
        academic_year_code: Optional[str] = "2025-2026",
        department_code: Optional[str] = None,
        document_type: Optional[str] = None,
        language_code: Optional[str] = None,
        version_number: Optional[int] = None,
        approval_status: Optional[str] = None,
        reference_date: Optional[datetime.date] = None,
        reranker_strategy: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Executes hybrid retrieval:
        1. Pre-filters metadata (academic year, department, doc type, language, version, approval, validity period).
        2. Semantic dense search on pgvector (with HNSW index).
        3. Full-text sparse keyword search on PostgreSQL tsvector (with GIN index).
        4. Cross-lingual multilingual query expansion.
        5. RRF / Cross-scorer reranking.
        """
        ref_date = reference_date or datetime.date.today()

        # 1. Expand query for multilingual & Tanglish support
        if BaseConfig.MULTILINGUAL_EXPANSION_ENABLED:
            expanded_query, keyword_tokens = multilingual_service.expand_query_cross_lingual(query_text)
            tsquery_str = multilingual_service.build_tsquery_string(keyword_tokens)
        else:
            expanded_query = query_text
            tsquery_str = ""

        # Generate embedding vector
        embedder = get_embedding_provider()
        query_vector = await embedder.get_embedding(expanded_query)
        vector_str = "[" + ",".join(f"{x:.6f}" for x in query_vector) + "]"

        # 2. Build strictly enforced metadata filter conditions
        where_clauses = [
            "(v.valid_from IS NULL OR v.valid_from <= :ref_date)",
            "(v.valid_until IS NULL OR v.valid_until >= :ref_date)",
        ]
        params: Dict[str, Any] = {
            "query_vector": vector_str,
            "ref_date": ref_date,
            "top_candidates": max(15, top_k * 3),
        }

        # Status filter
        if approval_status:
            where_clauses.append("d.status = :app_status AND v.status = :app_status")
            params["app_status"] = approval_status
        else:
            where_clauses.append("d.status IN ('ACTIVE', 'PUBLISHED')")
            where_clauses.append("v.status IN ('ACTIVE', 'PUBLISHED')")
            where_clauses.append("d.active_version_id = v.id")

        # Academic year filter
        if academic_year_code:
            where_clauses.append("ay.code = :ay_code")
            params["ay_code"] = academic_year_code

        # Department filter
        if department_code:
            where_clauses.append("dept.code = :dept_code")
            params["dept_code"] = department_code

        # Document type filter
        if document_type:
            where_clauses.append("d.document_type = :doc_type")
            params["doc_type"] = document_type

        # Language code filter
        if language_code and language_code != "all":
            where_clauses.append("d.language_code = :lang_code")
            params["lang_code"] = language_code

        # Version number filter
        if version_number:
            where_clauses.append("v.version_number = :v_num")
            params["v_num"] = version_number

        where_sql = " AND ".join(where_clauses)

        # 3. Dense Semantic Search (pgvector)
        dense_sql = text(f"""
            SELECT 
                c.id AS chunk_id,
                c.document_id,
                c.version_id,
                c.page_number,
                c.content,
                c.token_count,
                d.title AS document_title,
                d.document_type,
                d.language_code,
                v.version_number,
                ay.code AS academic_year,
                dept.name AS department_name,
                1.0 - (c.embedding <=> CAST(:query_vector AS vector)) AS similarity,
                1.0 - (c.embedding <=> CAST(:query_vector AS vector)) AS dense_similarity,
                0.0 AS sparse_score
            FROM document_chunks c
            JOIN documents d ON c.document_id = d.id
            JOIN document_versions v ON (c.version_id = v.id OR (c.version_id IS NULL AND d.active_version_id = v.id))
            JOIN academic_years ay ON d.academic_year_id = ay.id
            JOIN departments dept ON d.department_id = dept.id
            WHERE {where_sql}
            ORDER BY c.embedding <=> CAST(:query_vector AS vector) ASC
            LIMIT :top_candidates;
        """)

        res_dense = await db.execute(dense_sql, params)
        dense_candidates = [dict(row) for row in res_dense.mappings().all()]

        # 4. Sparse Keyword Search (PostgreSQL full-text tsvector)
        sparse_candidates = []
        if BaseConfig.HYBRID_SEARCH_ENABLED and tsquery_str:
            sparse_params = dict(params)
            sparse_params["tsquery"] = tsquery_str

            sparse_sql = text(f"""
                SELECT 
                    c.id AS chunk_id,
                    c.document_id,
                    c.version_id,
                    c.page_number,
                    c.content,
                    c.token_count,
                    d.title AS document_title,
                    d.document_type,
                    d.language_code,
                    v.version_number,
                    ay.code AS academic_year,
                    dept.name AS department_name,
                    0.5 AS similarity,
                    0.5 AS dense_similarity,
                    ts_rank_cd(c.search_vector, websearch_to_tsquery('simple', :tsquery)) AS sparse_score
                FROM document_chunks c
                JOIN documents d ON c.document_id = d.id
                JOIN document_versions v ON (c.version_id = v.id OR (c.version_id IS NULL AND d.active_version_id = v.id))
                JOIN academic_years ay ON d.academic_year_id = ay.id
                JOIN departments dept ON d.department_id = dept.id
                WHERE {where_sql}
                  AND c.search_vector @@ websearch_to_tsquery('simple', :tsquery)
                ORDER BY sparse_score DESC
                LIMIT :top_candidates;
            """)

            try:
                res_sparse = await db.execute(sparse_sql, sparse_params)
                sparse_candidates = [dict(row) for row in res_sparse.mappings().all()]
            except Exception as exc:
                logger.warning("Sparse full-text query failed (%s). Continuing with dense candidates.", exc)

        # 5. Merge Candidate Sets
        merged_by_id: Dict[str, Dict[str, Any]] = {}
        for c in dense_candidates:
            cid = str(c["chunk_id"])
            merged_by_id[cid] = c

        for c in sparse_candidates:
            cid = str(c["chunk_id"])
            if cid in merged_by_id:
                merged_by_id[cid]["sparse_score"] = c["sparse_score"]
            else:
                merged_by_id[cid] = c

        combined_candidates = list(merged_by_id.values())

        # 6. Apply Reranking Strategy
        reranker = get_reranker(reranker_strategy)
        reranked_chunks = reranker.rerank(
            query=query_text,
            candidates=combined_candidates,
            top_k=top_k,
        )

        return reranked_chunks

    async def answer_query(
        self,
        db: AsyncSession,
        query: str,
        session_id: uuid.UUID,
        language: str = "en",
        academic_year: Optional[str] = "2025-2026",
        department_code: Optional[str] = None,
        document_type: Optional[str] = None,
        version_number: Optional[int] = None,
    ) -> ChatQueryResponse:
        """Processes user query with safety checks, conflict detection,
        ambiguity handling, cross-lingual retrieval, and authentic citations.
        """
        # Determine language (if not explicitly provided, detect from script)
        detected_lang = multilingual_service.detect_language(query)
        effective_lang = "ta" if detected_lang in ("ta", "ta-Latn") and language == "en" else language

        # 1. Scope Check: Older Academic Year Guard
        older_year = self._check_older_academic_year_request(query, academic_year or "2025-2026")
        if older_year:
            msg = (
                f"{older_year} ஆம் கல்வி ஆண்டிற்கான கல்லூரி சுற்றறிக்கைகள் காப்பகப்படுத்தப்பட்டுள்ளன. தற்போதைய அதிகாரப்பூர்வ பதிவுகள் 2025-2026 க்கானது மட்டுமே. உதவி மையத்தில் கோரிக்கை தொடங்கவா?"
                if effective_lang == "ta"
                else f"The available verified college documentation is for academic year {academic_year or '2025-2026'}. Official records for older academic year {older_year} are archived. Would you like to create a support ticket for the Administrative Office?"
            )
            return ChatQueryResponse(
                message_id=uuid.uuid4(),
                session_id=session_id,
                response=msg,
                language=effective_lang,
                confidence_score=0.10,
                fallback_triggered=True,
                citations=[],
                suggested_ticket=SuggestedTicket(default_category="GENERAL", prefilled_query=query),
            )

        # 2. Scope Check: Ambiguous / Vague Queries
        if self._is_ambiguous_query(query):
            clarification = (
                "கல்லூரியில் பல்வேறு கட்டண விவரங்கள் உள்ளன (எ.கா: B.E. கணினி அறிவியல் கல்விக் கட்டணம், விடுதி வைப்புத் தொகை, தேர்வு விலக்குக் கட்டணம், மறுமதிப்பீட்டுக் கட்டணம்). நீங்கள் எந்தக் கட்டணத்தைப் பற்றிக் கேட்கிறீர்கள் என்பதைத் தெளிவாகக் குறிப்பிடவும்."
                if effective_lang == "ta"
                else "The college has several distinct fee structures (e.g., B.E. Computer Science Tuition Fee, Hostel Caution Deposit, Exam Condonation Fee, Revaluation Fee). Please specify which department or facility fee you are inquiring about."
            )
            return ChatQueryResponse(
                message_id=uuid.uuid4(),
                session_id=session_id,
                response=clarification,
                language=effective_lang,
                confidence_score=0.40,
                fallback_triggered=True,
                citations=[],
                suggested_ticket=None,
            )

        # 3. Retrieve Evidence
        try:
            evidence_chunks = await self.search_evidence(
                db=db,
                query_text=query,
                top_k=5,
                academic_year_code=academic_year,
                department_code=department_code,
                document_type=document_type,
                version_number=version_number,
            )
        except Exception as exc:
            logger.error("Evidence retrieval failure: %s", exc, exc_info=True)
            return ChatQueryResponse(
                message_id=uuid.uuid4(),
                session_id=session_id,
                response=(
                    "மன்னிக்கவும், AI தேடல் சேவை தற்போது கிடைக்கவில்லை. உதவி மையத்தில் கோரிக்கை தொடங்கவா?"
                    if effective_lang == "ta"
                    else "I am currently unable to search verified college documents due to a service error. Would you like to create a support ticket for the Administration Office?"
                ),
                language=effective_lang,
                confidence_score=0.0,
                fallback_triggered=True,
                citations=[],
                suggested_ticket=SuggestedTicket(default_category="GENERAL", prefilled_query=query),
            )

        top_similarity = evidence_chunks[0]["similarity"] if evidence_chunks else 0.0

        # 4. Conflict Detection Between Retrieved Documents
        conflict_msg = self._detect_conflicting_evidence(evidence_chunks)
        if conflict_msg:
            logger.warning("Evidence conflict: %s", conflict_msg)
            safe_conflict_response = (
                "அதிகாரப்பூர்வ சுற்றறிக்கைகளில் முரண்பாடான கொள்கை விவரங்கள் கண்டறியப்பட்டுள்ளன. தவறான தகவலைத் தவிர்க்க, தயவுசெய்து நிர்வாக அலுவலகத்தில் கோரிக்கை தொடங்கவும்."
                if effective_lang == "ta"
                else "I detected conflicting policy records regarding this matter across approved college documents. To ensure you receive accurate details, please create a support ticket or contact the College Administration Office directly."
            )
            return ChatQueryResponse(
                message_id=uuid.uuid4(),
                session_id=session_id,
                response=safe_conflict_response,
                language=effective_lang,
                confidence_score=0.30,
                fallback_triggered=True,
                citations=[],
                suggested_ticket=SuggestedTicket(default_category="GENERAL", prefilled_query=query),
            )

        # 5. Anti-Hallucination & Confidence Threshold Check
        if not evidence_chunks or top_similarity < self.confidence_threshold:
            logger.info("Query below threshold (top=%.3f, threshold=%.3f). Triggering fallback.", top_similarity, self.confidence_threshold)
            fallback_msg = (
                f"{academic_year or '2025-2026'} ஆம் ஆண்டிற்கான அதிகாரப்பூர்வ கல்லூரி சுற்றறிக்கைகளில் இதற்கான சரிபார்க்கப்பட்ட தகவல்கள் கிடைக்கவில்லை. உதவி மையத்தில் கோரிக்கை தொடங்கவா?"
                if effective_lang == "ta"
                else f"I could not find verified official documentation regarding this matter in the approved college records for {academic_year or '2025-2026'}. Would you like to create a support ticket for the Administration Office?"
            )
            return ChatQueryResponse(
                message_id=uuid.uuid4(),
                session_id=session_id,
                response=fallback_msg,
                language=effective_lang,
                confidence_score=round(float(top_similarity), 3),
                fallback_triggered=True,
                citations=[],
                suggested_ticket=SuggestedTicket(default_category="GENERAL", prefilled_query=query),
            )

        # 6. LLM Evidence Synthesis
        try:
            llm = get_llm_provider()
            grounded_answer = await llm.generate_grounded_answer(
                query=query,
                evidence_chunks=evidence_chunks,
                language=effective_lang,
            )
        except Exception as exc:
            logger.error("LLM synthesis failure: %s", exc, exc_info=True)
            return ChatQueryResponse(
                message_id=uuid.uuid4(),
                session_id=session_id,
                response=(
                    "மன்னிக்கவும், AI சேவைப் பிழை ஏற்பட்டுள்ளது. உதவி மையத்தில் கோரிக்கை தொடங்கவா?"
                    if effective_lang == "ta"
                    else "I encountered an error connecting to the AI synthesis service. Would you like to create a support ticket for the Administration Office?"
                ),
                language=effective_lang,
                confidence_score=0.0,
                fallback_triggered=True,
                citations=[],
                suggested_ticket=SuggestedTicket(default_category="GENERAL", prefilled_query=query),
            )

        # 7. Construct Genuine Citations with Snippets
        citations = [
            CitationItem(
                document_id=uuid.UUID(str(c["document_id"])),
                document_title=c["document_title"],
                version_number=c["version_number"],
                academic_year=c["academic_year"],
                page_number=c["page_number"],
                section=c.get("section") or "Official College Regulation",
                snippet=c.get("snippet") or (c.get("content", "")[:180] + "..."),
            )
            for c in grounded_answer.citations
        ]

        chat_resp = ChatQueryResponse(
            message_id=uuid.uuid4(),
            session_id=session_id,
            response=grounded_answer.response_text,
            language=effective_lang,
            confidence_score=round(grounded_answer.confidence_score, 3),
            fallback_triggered=grounded_answer.fallback_triggered,
            citations=citations,
            suggested_ticket=None,
        )

        # 8. Record Message in Database Audit
        try:
            session_exists = await db.get(ChatSessions, session_id)
            if session_exists:
                log_msg = ChatMessages(
                    id=chat_resp.message_id,
                    session_id=session_id,
                    role="assistant",
                    content=chat_resp.response,
                    language_code=chat_resp.language,
                    confidence_score=chat_resp.confidence_score,
                    retrieved_chunk_ids=[uuid.UUID(str(c["chunk_id"])) for c in evidence_chunks[:3]] if evidence_chunks else [],
                )
                db.add(log_msg)
                await db.commit()
        except Exception as exc:
            logger.debug("Chat interaction not saved to audit: %s", exc)
            await db.rollback()

        return chat_resp


rag_service = RAGOrchestrationService()
