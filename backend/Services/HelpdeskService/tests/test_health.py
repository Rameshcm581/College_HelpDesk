# backend/Services/HelpdeskService/tests/test_health.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_health_alias(async_client: AsyncClient):
    """Verifies external load balancer alias returns 200 OK and healthy status."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "service" in data


@pytest.mark.asyncio
async def test_public_config_endpoint(async_client: AsyncClient):
    """Verifies public configuration endpoint returns academic year and bilingual greetings."""
    response = await async_client.get("/api/v1/public/config")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["current_academic_year"] == "2025-2026"
    assert "en" in json_data["data"]["supported_languages"]
    assert "ta" in json_data["data"]["supported_languages"]


@pytest.mark.asyncio
async def test_live_probe(async_client: AsyncClient):
    """Verifies Kubernetes / Docker liveness endpoint."""
    response = await async_client.get("/api/v1/public/live")
    assert response.status_code == 200
    assert response.json() == {"live": True}
