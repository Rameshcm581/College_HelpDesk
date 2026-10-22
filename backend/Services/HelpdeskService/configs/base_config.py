# backend/Services/HelpdeskService/configs/base_config.py
import os
import pathlib
from dotenv import load_dotenv

# Search for .env at Service level, then backend level, then root level
for env_path in [
    pathlib.Path(__file__).parent.parent / ".env",
    pathlib.Path(__file__).parent.parent.parent.parent / ".env",
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
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
    RAG_CONFIDENCE_THRESHOLD: float = float(os.getenv("RAG_CONFIDENCE_THRESHOLD", "0.72"))

    # Hybrid Search & Reranking
    HYBRID_SEARCH_ENABLED: bool = os.getenv("HYBRID_SEARCH_ENABLED", "true").lower() == "true"
    HYBRID_DENSE_WEIGHT: float = float(os.getenv("HYBRID_DENSE_WEIGHT", "0.65"))
    HYBRID_SPARSE_WEIGHT: float = float(os.getenv("HYBRID_SPARSE_WEIGHT", "0.35"))
    RRF_K: int = int(os.getenv("RRF_K", "60"))
    RERANKER_TYPE: str = os.getenv("RERANKER_TYPE", "hybrid_rrf")  # "hybrid_rrf", "cross_scorer", "none"
    RERANKER_TOP_K: int = int(os.getenv("RERANKER_TOP_K", "5"))
    MULTILINGUAL_EXPANSION_ENABLED: bool = os.getenv("MULTILINGUAL_EXPANSION_ENABLED", "true").lower() == "true"

    # Storage
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./storage")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "50"))

    # CORS & Allowed Origins
    CORS_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5175,http://localhost:3000,http://127.0.0.1:5175,http://localhost:8005").split(",")
        if origin.strip()
    ]
    ALLOWED_EMBED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_EMBED_ORIGINS",
            "http://localhost:5175,http://127.0.0.1:5175,http://localhost:3000,http://localhost:8005"
        ).split(",")
        if origin.strip()
    ]

    # Rate Limiting
    RATE_LIMIT_CHAT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_CHAT_PER_MINUTE", "60"))
