# backend/Services/HelpdeskService/resources/rerankerService.py
import abc
import math
import re
from typing import Any, Dict, List, Optional
from configs.base_config import BaseConfig


class BaseReranker(abc.ABC):
    @abc.abstractmethod
    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Reranks candidate evidence chunks and returns top_k."""
        pass


class RRFReranker(BaseReranker):
    """Combines dense semantic ranking and sparse full-text keyword ranking
    using Reciprocal Rank Fusion (RRF).
    Formula: RRF_score(d) = sum(w_m / (k + rank_m(d)))
    """

    def __init__(
        self,
        k: int = None,
        dense_weight: float = None,
        sparse_weight: float = None,
    ):
        self.k = k or BaseConfig.RRF_K
        self.dense_weight = dense_weight or BaseConfig.HYBRID_DENSE_WEIGHT
        self.sparse_weight = sparse_weight or BaseConfig.HYBRID_SPARSE_WEIGHT

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        # Sort candidates by dense similarity for dense rank
        sorted_by_dense = sorted(
            candidates,
            key=lambda c: float(c.get("dense_similarity") or c.get("similarity") or 0.0),
            reverse=True,
        )
        dense_ranks = {str(c["chunk_id"]): idx + 1 for idx, c in enumerate(sorted_by_dense)}

        # Sort only candidates with real keyword matches for sparse rank
        sparse_matching = [c for c in candidates if float(c.get("sparse_score") or 0.0) > 0.0]
        sorted_by_sparse = sorted(
            sparse_matching,
            key=lambda c: float(c.get("sparse_score") or 0.0),
            reverse=True,
        )
        sparse_ranks = {str(c["chunk_id"]): idx + 1 for idx, c in enumerate(sorted_by_sparse)}

        # Detect if query has Tamil script
        is_query_tamil = bool(re.search(r'[\u0B80-\u0BFF]', query))

        # Compute RRF score for each unique chunk
        unique_candidates: Dict[str, Dict[str, Any]] = {}
        for c in candidates:
            cid = str(c["chunk_id"])
            if cid not in unique_candidates:
                d_rank = dense_ranks.get(cid, 999)
                s_rank = sparse_ranks.get(cid, 999)

                dense_term = (self.dense_weight / (self.k + d_rank)) if d_rank < 900 else 0.0
                sparse_term = (self.sparse_weight / (self.k + s_rank)) if s_rank < 900 else 0.0
                rrf_score = dense_term + sparse_term

                dense_sim = float(c.get("dense_similarity") or c.get("similarity") or 0.0)
                sparse_score = float(c.get("sparse_score") or 0.0)

                # Calibrate confidence score:
                # If dense similarity is below threshold and no keyword match, preserve low similarity to trigger fallback
                if dense_sim < BaseConfig.RAG_CONFIDENCE_THRESHOLD and sparse_score <= 0.01:
                    calibrated_score = dense_sim
                else:
                    max_possible = (self.dense_weight / (self.k + 1)) + (self.sparse_weight / (self.k + 1))
                    relative_ratio = rrf_score / max_possible
                    calibrated_score = max(dense_sim, min(0.98, (dense_sim * 0.7) + (relative_ratio * 0.3)))

                item = dict(c)
                item["rrf_score"] = round(rrf_score, 5)
                item["similarity"] = round(calibrated_score, 3)
                item["dense_rank"] = d_rank
                item["sparse_rank"] = s_rank
                unique_candidates[cid] = item

        reranked = sorted(unique_candidates.values(), key=lambda x: x["rrf_score"], reverse=True)
        return reranked[:top_k]


class LexicalSemanticCrossReranker(BaseReranker):
    """Advanced in-process cross-scorer:
    Combines semantic embedding similarity with exact entity matching,
    numbers/fee preservation, and query keyword proximity without external GPU services.
    """

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        query_lower = query.lower()
        # Extract specific numbers, percentages, and currencies from query
        query_numbers = set(re.findall(r'₹?\b\d+[\d,.]*%?', query_lower))
        query_terms = set(re.findall(r'[\w\u0B80-\u0BFF]+', query_lower)) - {
            "what", "is", "the", "for", "and", "in", "to", "how", "much"
        }

        scored = []
        for c in candidates:
            content_lower = c.get("content", "").lower()
            base_sim = float(c.get("similarity") or 0.5)

            # 1. Lexical overlap bonus
            matched_terms = sum(1 for t in query_terms if t in content_lower)
            lexical_ratio = (matched_terms / len(query_terms)) if query_terms else 0.5

            # 2. Number consistency bonus / penalty
            # If query asked for ₹5000 or 75% and passage contains it, boost confidence
            number_boost = 0.0
            if query_numbers:
                if any(num.replace('₹', '').replace(',', '') in content_lower.replace(',', '') for num in query_numbers):
                    number_boost = 0.10
                else:
                    number_boost = -0.05

            combined_score = min(
                0.99,
                max(0.10, (base_sim * 0.65) + (lexical_ratio * 0.25) + number_boost)
            )

            item = dict(c)
            item["similarity"] = round(combined_score, 3)
            item["cross_score"] = round(combined_score, 4)
            scored.append(item)

        scored.sort(key=lambda x: x["cross_score"], reverse=True)
        return scored[:top_k]


class NoOpReranker(BaseReranker):
    """Pass-through reranker that returns candidates sorted by base similarity."""

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        return sorted(
            candidates,
            key=lambda x: float(x.get("similarity") or 0.0),
            reverse=True,
        )[:top_k]


def get_reranker(strategy_name: Optional[str] = None) -> BaseReranker:
    """Factory that returns configured reranker implementation."""
    name = (strategy_name or BaseConfig.RERANKER_TYPE).lower()
    if name == "cross_scorer":
        return LexicalSemanticCrossReranker()
    elif name == "none":
        return NoOpReranker()
    # Default to Hybrid Reciprocal Rank Fusion
    return RRFReranker()
