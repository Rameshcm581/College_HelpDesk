# backend/Services/HelpdeskService/configs/base_config.py
import os
import pathlib
from dotenv import load_dotenv

# Search for .env at Service level, backend level, and project root level
for env_path in [
    pathlib.Path(__file__).parent.parent / ".env",
    pathlib.Path(__file__).parent.parent.parent.parent / ".env",
    pathlib.Path(__file__).parent.parent.parent.parent.parent / ".env",
]:
    if env_path.exists():
        load_dotenv(env_path)
        break

APP_ENV = os.getenv("APP_ENV", "dev")
IS_PROD = APP_ENV == "prod"
_DEFAULT_SECRET = "dev-secret-change-me-32-chars-minimum-xx"

_SECRET = os.getenv("SECRET_KEY", _DEFAULT_SECRET)
if IS_PROD and (len(_SECRET) < 32 or "change-me" in _SECRET or _SECRET.startswith("dev-")):
    raise RuntimeError("APP_ENV=prod requires SECRET_KEY to be set to a random value of at least 32 characters")


class BaseConfig:
    APP_NAME: str = "College AI Help Desk API"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = APP_ENV
    DEBUG: bool = os.getenv("DEBUG", "true" if not IS_PROD else "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

    # Security
    SECRET_KEY: str = _SECRET
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_MINUTES: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "15"))
    REFRESH_TOKEN_DAYS: int = int(os.getenv("REFRESH_TOKEN_DAYS", "7"))
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "true" if IS_PROD else "false").lower() == "true"
    REFRESH_COOKIE_NAME: str = "helpdesk_refresh"

    # Database URLs (Default connects to pgvector on port 5435 to avoid host port 5432 conflicts)
    DB_URI: str = os.getenv(
        "DB_URI",
        "postgresql+asyncpg://helpdesk_user:helpdesk_dev_pass@localhost:5435/college_helpdesk_db"
    )
    SYNC_DB_URI: str = os.getenv(
        "SYNC_DB_URI",
        "postgresql://helpdesk_user:helpdesk_dev_pass@localhost:5435/college_helpdesk_db"
    )

    # Redis URL
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://:helpdesk_redis_pass@localhost:6380/0")

    # AI & RAG Settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_CHAT_MODEL: str = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
    OPENAI_COMPLETION_MODEL: str = os.getenv("OPENAI_COMPLETION_MODEL", "gpt-4o")
    OPENAI_EMBEDDING_MODEL: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    EMBEDDING_PROVIDER: str = os.getenv("EMBEDDING_PROVIDER", "mock")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
    RAG_CONFIDENCE_THRESHOLD: float = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.68"))

    # Hybrid Search & Reranking
    HYBRID_SEARCH_ENABLED: bool = os.getenv("HYBRID_SEARCH_ENABLED", "true").lower() == "true"
    HYBRID_DENSE_WEIGHT: float = float(os.getenv("HYBRID_DENSE_WEIGHT", "0.65"))
    HYBRID_SPARSE_WEIGHT: float = float(os.getenv("HYBRID_SPARSE_WEIGHT", "0.35"))
    RRF_K: int = int(os.getenv("RRF_K", "60"))
    RERANKER_TYPE: str = os.getenv("RERANKER_TYPE", "hybrid_rrf")  # "hybrid_rrf", "cross_scorer", "none"
    RERANKER_TOP_K: int = int(os.getenv("RERANKER_TOP_K", "5"))
    MULTILINGUAL_EXPANSION_ENABLED: bool = os.getenv("MULTILINGUAL_EXPANSION_ENABLED", "true").lower() == "true"

    # Storage & Neon S3 Object Storage
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./storage")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))
    AWS_ENDPOINT_URL_S3: str = os.getenv("AWS_ENDPOINT_URL_S3", "").strip()
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
    AWS_REGION: str = os.getenv("AWS_REGION", "ap-southeast-1").strip()
    NEON_STORAGE_BUCKET: str = os.getenv("NEON_STORAGE_BUCKET", "storage").strip()
    USE_NEON_STORAGE: bool = os.getenv("USE_NEON_STORAGE", "false").lower() in ("true", "1", "yes")

    # CORS & Allowed Origins
    CORS_ORIGINS: list[str] = [
        origin.strip().rstrip('/')
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5175,http://localhost:3000,http://127.0.0.1:5175,http://localhost:8005,https://college-help-desk-omega.vercel.app"
        ).split(",")
        if origin.strip()
    ]
    ALLOWED_EMBED_ORIGINS: list[str] = [
        origin.strip().rstrip('/')
        for origin in os.getenv(
            "ALLOWED_EMBED_ORIGINS",
            "http://localhost:5175,http://127.0.0.1:5175,http://localhost:3000,http://localhost:8005,https://college-help-desk-omega.vercel.app"
        ).split(",")
        if origin.strip()
    ]

    # Rate Limiting
    RATE_LIMIT_CHAT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_CHAT_PER_MINUTE", "60"))
    # When USE_REDIS_RATE_LIMIT=true the chat rate limiter uses the Upstash/Redis
    # sliding-window counter instead of the in-process defaultdict, which makes
    # the limit work correctly across multiple replicas.
    USE_REDIS_RATE_LIMIT: bool = os.getenv("USE_REDIS_RATE_LIMIT", "true").lower() == "true"

    # SMTP – Institutional Email Notifications
    SMTP_HOST: str = os.getenv("SMTP_HOST", "").strip()
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "").strip()
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "").strip()
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "helpdesk@college.edu").strip()
    SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "College AI Help Desk").strip()
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

    # Celery / Background Jobs
    CELERY_BEAT_ENABLED: bool = os.getenv("CELERY_BEAT_ENABLED", "true").lower() == "true"
    # Scheduled web-scraper runs (cron format strings, IST)
    SCRAPER_SCHEDULE_CRON: str = os.getenv("SCRAPER_SCHEDULE_CRON", "0 2 * * *")   # 02:00 IST daily
    DB_BACKUP_SCHEDULE_CRON: str = os.getenv("DB_BACKUP_SCHEDULE_CRON", "0 3 * * *")  # 03:00 IST daily

