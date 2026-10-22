# backend/Services/HelpdeskService/resources/chatController.py
import asyncio
import json
import logging
import time
import uuid
from collections import defaultdict
from typing import AsyncGenerator
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from configs.base_config import BaseConfig
from models import get_db
from models.models import ChatSessions
from resources.ragService import rag_service
from resources.schemas import (
    ApiResponse,
    ChatFeedbackRequest,
    ChatQueryRequest,
    ChatQueryResponse,
    CitationItem,
    SuggestedTicket,
)
from resources.utils import mask_pii_for_logging

logger = logging.getLogger(__name__)
router = APIRouter()

# ── IN-MEMORY RATE LIMITING (Sliding Window per IP with Key Eviction) ─────────
_rate_limit_store = defaultdict(list)


def get_client_ip(request: Request) -> str:
    """Extracts client IP, respecting trusted reverse proxy headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        client_ip = forwarded.split(",")[0].strip()
        if client_ip:
            return client_ip
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"


def check_rate_limit(client_ip: str, limit: int = None, window_sec: int = 60) -> bool:
    """Returns True if within rate limit, False otherwise. Periodically prunes stale keys."""
    max_requests = limit or BaseConfig.RATE_LIMIT_CHAT_PER_MINUTE
    now = time.time()

    # Periodic cleanup to prevent unbounded memory growth under high IP churn
    if len(_rate_limit_store) > 1000:
        stale_keys = [k for k, v in _rate_limit_store.items() if not v or (now - v[-1] > window_sec)]
        for k in stale_keys:
            _rate_limit_store.pop(k, None)

    # Filter out entries older than window
    timestamps = [t for t in _rate_limit_store[client_ip] if now - t < window_sec]
    if len(timestamps) >= max_requests:
        return False
    timestamps.append(now)
    _rate_limit_store[client_ip] = timestamps
    return True


def validate_embed_origin(request: Request) -> bool:
    """Verifies that requests originate from approved embed origins."""
    origin = request.headers.get("origin") or request.headers.get("referer")
    if not origin:
        return True  # Direct API calls or same-origin
    parsed = urlparse(origin)
    clean_origin = f"{parsed.scheme}://{parsed.netloc}"
    allowed = BaseConfig.ALLOWED_EMBED_ORIGINS
    if BaseConfig.DEBUG and ("localhost" in clean_origin or "127.0.0.1" in clean_origin):
        return True
    return clean_origin in allowed or "*" in allowed


@router.post("/chat", response_model=ApiResponse, tags=["Public Chatbot"])
async def handle_public_chat(
    req: ChatQueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Public conversational AI endpoint."""
    client_ip = get_client_ip(request)
    logger.info("Public chat query from %s: query='%s'", client_ip, mask_pii_for_logging(req.query))

    # 1. Rate limiting check
    if not check_rate_limit(client_ip):
        logger.warning("Rate limit exceeded for IP %s", client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment before sending another message.",
            headers={"Retry-After": "60"},
        )

    # 2. Origin check for widget embedding
    if not validate_embed_origin(request):
        logger.warning("Unauthorized embed origin rejected: %s", request.headers.get("origin"))
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Embedding from this origin is not authorized by the college administration.",
        )

    session_id = req.session_id or uuid.uuid4()

    # Ensure session exists in database
    session = await db.get(ChatSessions, session_id)
    if not session:
        session = ChatSessions(
            id=session_id,
            ip_hash=f"ip-{hash(client_ip) % 1000000}",
            language_code=req.language,
            client_origin=request.headers.get("origin"),
        )
        db.add(session)
        await db.commit()

    # Detect Tamil characters in query or language param
    is_tamil = req.language == "ta" or any("\u0b80" <= char <= "\u0bff" for char in req.query)
    lang = "ta" if is_tamil else "en"

    # Execute full RAG pipeline (embed query -> pgvector search -> threshold -> LLM)
    rag_response = await rag_service.answer_query(
        db=db,
        query=req.query,
        session_id=session_id,
        language=lang,
        academic_year=req.academic_year or "2025-2026",
        department_code=req.department_code,
        document_type=req.document_type,
        version_number=req.version_number,
    )

    return ApiResponse(success=True, data=rag_response.model_dump())


@router.post("/chat/stream", tags=["Public Chatbot"])
async def stream_public_chat(
    req: ChatQueryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Streams RAG responses token-by-token using Server-Sent Events (SSE)."""
    client_ip = get_client_ip(request)
    logger.info("Public stream chat query from %s: query='%s'", client_ip, mask_pii_for_logging(req.query))

    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait a moment before sending another message.",
        )

    if not validate_embed_origin(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Embedding from this origin is not authorized.",
        )

    session_id = req.session_id or uuid.uuid4()
    session = await db.get(ChatSessions, session_id)
    if not session:
        session = ChatSessions(
            id=session_id,
            ip_hash=f"ip-{hash(client_ip) % 1000000}",
            language_code=req.language,
            client_origin=request.headers.get("origin"),
        )
        db.add(session)
        await db.commit()

    is_tamil = req.language == "ta" or any("\u0b80" <= char <= "\u0bff" for char in req.query)
    lang = "ta" if is_tamil else "en"

    # Execute RAG query
    rag_response = await rag_service.answer_query(
        db=db,
        query=req.query,
        session_id=session_id,
        language=lang,
        academic_year=req.academic_year or "2025-2026",
        department_code=req.department_code,
        document_type=req.document_type,
        version_number=req.version_number,
    )

    async def sse_generator() -> AsyncGenerator[str, None]:
        # 1. Send start event
        yield f"data: {json.dumps({'type': 'start', 'message_id': str(rag_response.message_id), 'session_id': str(session_id), 'language': lang})}\n\n"

        # 2. Stream tokens (words) smoothly
        words = rag_response.response.split(" ")
        for i, word in enumerate(words):
            token = word + (" " if i < len(words) - 1 else "")
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
            await asyncio.sleep(0.02)  # 20ms pacing for natural streaming cadence

        # 3. Send citations & metadata event
        meta_payload = {
            "type": "meta",
            "confidence_score": rag_response.confidence_score,
            "fallback_triggered": rag_response.fallback_triggered,
            "citations": [c.model_dump(mode="json") for c in rag_response.citations],
            "suggested_ticket": rag_response.suggested_ticket.model_dump(mode="json") if rag_response.suggested_ticket else None,
        }
        yield f"data: {json.dumps(meta_payload, default=str)}\n\n"

        # 4. Done event
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chat/feedback", response_model=ApiResponse, tags=["Public Chatbot"])
async def submit_chat_feedback(req: ChatFeedbackRequest):
    """Submits end-user rating on answer helpfulness."""
    logger.info("Chat feedback received: message_id=%s, rating=%s", req.message_id, req.feedback)
    return ApiResponse(
        success=True,
        message=f"Feedback '{req.feedback}' recorded. Thank you for helping improve the help desk.",
    )


@router.get("/config", response_model=ApiResponse, tags=["Public Chatbot"])
async def get_public_config():
    """Returns college configuration and active academic year for widget hydration."""
    config_data = {
        "college_name": "St. Jude College of Engineering & Technology",
        "college_logo_url": "/assets/college-logo.svg",
        "current_academic_year": "2025-2026",
        "supported_languages": ["en", "ta"],
        "primary_color": "#1e3a8a",
        "accent_color": "#059669",
        "widget_position": "bottom-right",
        "greeting_en": "Hello! I am the College AI Help Desk Assistant. Ask me about admissions, fees, hostel regulations, scholarships, or academic policies for 2025–2026.",
        "greeting_ta": "வணக்கம்! நான் கல்லூரி AI உதவி மைய உதவியாளர். சேர்க்கை, கட்டணம், விடுதி, தேர்வுகள் அல்லது உதவித்தொகை பற்றி கேளுங்கள்.",
        "suggested_questions": [
            {"text": "What is the hostel caution deposit fee?", "lang": "en"},
            {"text": "விடுதி வைப்புத் தொகை எவ்வளவு?", "lang": "ta"},
            {"text": "What is the minimum attendance required for semester exams?", "lang": "en"},
            {"text": "How much is the B.E. Computer Science tuition fee?", "lang": "en"},
            {"text": "Who won the 1994 FIFA world cup?", "lang": "en"},
        ],
        "anti_hallucination_guarantee": True,
        "is_demonstration_sample": True,
        "allowed_embed_origins": BaseConfig.ALLOWED_EMBED_ORIGINS,
    }
    return ApiResponse(success=True, data=config_data)
