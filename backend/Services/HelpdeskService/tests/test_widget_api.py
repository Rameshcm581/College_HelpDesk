# backend/Services/HelpdeskService/tests/test_widget_api.py
import pytest
from httpx import AsyncClient
from unittest.mock import patch

from configs.base_config import BaseConfig
from resources.chatController import check_rate_limit, _rate_limit_store


# ── WIDGET PUBLIC CONFIG & HYDRATION TESTS ────────────────────────────────────

@pytest.mark.asyncio
async def test_widget_public_config_schema(async_client: AsyncClient):
    """Verifies that GET /api/v1/public/config returns all parameters required to brand and hydrate the widget."""
    resp = await async_client.get("/api/v1/public/config")
    assert resp.status_code == 200
    data = resp.json()["data"]

    # Configurable branding checks
    assert data["college_name"] == "St. Jude College of Engineering & Technology"
    assert data["current_academic_year"] == "2025-2026"
    assert "en" in data["supported_languages"]
    assert "ta" in data["supported_languages"]
    assert "primary_color" in data
    assert "widget_position" in data
    assert data["greeting_en"] is not None
    assert data["greeting_ta"] is not None
    assert len(data["suggested_questions"]) >= 4
    assert data["anti_hallucination_guarantee"] is True
    assert data["is_demonstration_sample"] is True
    assert isinstance(data["allowed_embed_origins"], list)


@pytest.mark.asyncio
async def test_widget_chat_feedback_recording(async_client: AsyncClient):
    """Verifies that POST /api/v1/public/chat/feedback records helpful/unhelpful feedback ratings."""
    payload = {
        "message_id": "00000000-0000-0000-0000-000000000001",
        "feedback": "helpful",
    }
    resp = await async_client.post("/api/v1/public/chat/feedback", json=payload)
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert "helpful" in resp.json()["message"]


@pytest.mark.asyncio
async def test_widget_sse_streaming_chat(async_client: AsyncClient):
    """Verifies that POST /api/v1/public/chat/stream delivers valid Server-Sent Events (SSE)."""
    payload = {
        "query": "What is the hostel caution deposit fee?",
        "language": "en",
        "academic_year": "2025-2026",
    }
    resp = await async_client.post("/api/v1/public/chat/stream", json=payload)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    body = resp.text
    assert "data: " in body
    assert '"type": "start"' in body
    assert '"type": "token"' in body
    assert '"type": "meta"' in body
    assert "[DONE]" in body


# ── SECURITY & RATE LIMITING TESTS ───────────────────────────────────────────

def test_rate_limiter_in_memory():
    """Verifies the sliding window rate limiter blocks traffic after exceeding per-minute threshold."""
    ip = "192.168.1.99"
    _rate_limit_store[ip] = []

    # Should allow up to 3 requests under limit 3
    assert check_rate_limit(ip, limit=3, window_sec=60) is True
    assert check_rate_limit(ip, limit=3, window_sec=60) is True
    assert check_rate_limit(ip, limit=3, window_sec=60) is True
    # 4th request must be rejected
    assert check_rate_limit(ip, limit=3, window_sec=60) is False


@pytest.mark.asyncio
async def test_rate_limiter_endpoint_response(async_client: AsyncClient):
    """Verifies that client receiving rate limit error gets HTTP 429 Too Many Requests."""
    with patch("resources.chatController.check_rate_limit", return_value=False):
        payload = {
            "query": "What is the tuition fee?",
            "language": "en",
        }
        resp = await async_client.post("/api/v1/public/chat", json=payload)
        assert resp.status_code == 429
        error_msg = resp.json()["error"]["message"]
        assert "Rate limit exceeded" in error_msg


@pytest.mark.asyncio
async def test_security_headers_and_frame_ancestors(async_client: AsyncClient):
    """Verifies that the backend sends Content-Security-Policy frame-ancestors and anti-sniffing headers."""
    resp = await async_client.get("/api/v1/public/config")
    assert resp.status_code == 200
    headers = resp.headers

    assert "content-security-policy" in headers
    csp = headers["content-security-policy"]
    assert "frame-ancestors" in csp
    assert "x-content-type-options" in headers
    assert headers["x-content-type-options"] == "nosniff"


@pytest.mark.asyncio
async def test_unapproved_origin_rejection(async_client: AsyncClient):
    """Verifies that embedding requests from unapproved third-party origins are refused."""
    with patch("resources.chatController.validate_embed_origin", return_value=False):
        payload = {
            "query": "What is the hostel fee?",
            "language": "en",
        }
        resp = await async_client.post(
            "/api/v1/public/chat",
            json=payload,
            headers={"Origin": "https://malicious-unapproved-site.com"},
        )
        assert resp.status_code == 403
        error_msg = resp.json()["error"]["message"]
        assert "not authorized" in error_msg
