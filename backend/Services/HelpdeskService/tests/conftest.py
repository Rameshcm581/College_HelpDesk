# backend/Services/HelpdeskService/tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient
from main import app
from models import engine


@pytest.fixture(autouse=True)
async def cleanup_db_pool():
    """Disposes engine pool between test runs to prevent asyncpg cross-loop collisions."""
    yield
    await engine.dispose()


@pytest.fixture
async def async_client():
    """Provides async HTTP client bound to the FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
