# backend/Services/HelpdeskService/resources/healthController.py
from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from configs.base_config import BaseConfig
from models import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", tags=["Health & Readiness"])
async def check_health(db: AsyncSession = Depends(get_db)):
    """Performs deep health check across database (pgvector) and Redis cache."""
    db_status = "connected"
    pgvector_installed = False
    redis_status = "connected"

    # 1. Verify Database & pgvector extension
    try:
        # Check pgvector extension
        res = await db.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector';"))
        vector_ext = res.scalar()
        pgvector_installed = bool(vector_ext)
    except Exception as exc:
        logger.error("Health check database failure: %s", exc)
        db_status = "disconnected"

    # 2. Verify Redis connectivity
    try:
        r = aioredis.from_url(BaseConfig.REDIS_URL, decode_responses=True, socket_connect_timeout=2)
        pong = await r.ping()
        await r.aclose()
        if not pong:
            redis_status = "disconnected"
    except Exception as exc:
        logger.warning("Health check Redis failure: %s", exc)
        redis_status = "disconnected"

    overall_healthy = (db_status == "connected")

    payload = {
        "status": "healthy" if overall_healthy else "degraded",
        "service": BaseConfig.APP_NAME,
        "version": BaseConfig.APP_VERSION,
        "environment": BaseConfig.APP_ENV,
        "database": {
            "status": db_status,
            "pgvector_installed": pgvector_installed,
        },
        "redis": {
            "status": redis_status,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    status_code = status.HTTP_200_OK if overall_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=status_code, content={"success": overall_healthy, "data": payload})


@router.get("/ready", tags=["Health & Readiness"])
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """Kubernetes / Docker Compose readiness check."""
    try:
        await db.execute(text("SELECT 1;"))
        return {"ready": True}
    except Exception as exc:
        logger.error("Readiness probe failed: %s", exc)
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"ready": False})


@router.get("/live", tags=["Health & Readiness"])
async def liveness_probe():
    """Kubernetes / Docker Compose liveness check."""
    return {"live": True}
