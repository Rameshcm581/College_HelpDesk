# backend/Services/HelpdeskService/main.py
import logging
import os
import pathlib
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from configs.base_config import BaseConfig
from models import engine
from resources.errors import register_handlers
from routes import router

# ── Logging setup (Must run before any component that logs) ───────────────────
logging.basicConfig(
    level=BaseConfig.LOG_LEVEL,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("helpdesk_service")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Lifecycle manager for database connectivity and resource teardown."""
    logger.info("Initializing %s (v%s) [%s]", BaseConfig.APP_NAME, BaseConfig.APP_VERSION, BaseConfig.APP_ENV)
    
    # Ping database to verify connectivity on boot
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1;"))
        logger.info("Database connection pool established successfully.")
    except Exception as exc:
        logger.warning("Database not immediately available on startup: %s", exc)

    yield

    logger.info("Shutting down %s — releasing database connection pool.", BaseConfig.APP_NAME)
    await engine.dispose()


app = FastAPI(
    title=BaseConfig.APP_NAME,
    version=BaseConfig.APP_VERSION,
    description="Multilingual (English & Tamil) AI Help Desk & Ticketing API for Higher Education.",
    docs_url="/docs" if BaseConfig.DEBUG else None,
    redoc_url="/redoc" if BaseConfig.DEBUG else None,
    lifespan=lifespan,
)

# ── CORS Middleware ───────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=BaseConfig.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    """Enforces Content-Security-Policy frame-ancestors and defense headers."""
    response = await call_next(request)
    # Allow embedding from configured allowed origins only
    allowed_frame_ancestors = " ".join(BaseConfig.ALLOWED_EMBED_ORIGINS)
    response.headers["Content-Security-Policy"] = (
        f"frame-ancestors 'self' {allowed_frame_ancestors}"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


# ── Global Error Handling ─────────────────────────────────────────────────────
register_handlers(app)

# ── Mount Canonical API Routes ─────────────────────────────────────────────────
app.include_router(router)


@app.get("/health", tags=["Health & Readiness"], include_in_schema=False)
async def root_health_alias():
    """Root alias for external load balancers and container healthchecks."""
    return {"status": "healthy", "service": BaseConfig.APP_NAME, "version": BaseConfig.APP_VERSION}
