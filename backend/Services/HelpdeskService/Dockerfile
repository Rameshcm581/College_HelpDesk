# ==============================================================================
# Production Dockerfile for College AI Help Desk Backend Service
# Multi-stage build with non-root security execution and OCR language support
# ==============================================================================

# ── STAGE 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ── STAGE 2: Runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH" \
    APP_ENV=production

WORKDIR /app

# Install runtime dependencies: PostgreSQL client libraries, Tesseract OCR with Tamil language support, and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    tesseract-ocr \
    tesseract-ocr-tam \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create secure unprivileged user
RUN groupadd -g 1001 appgroup && \
    useradd -u 1001 -g appgroup -m -s /bin/bash appuser

# Copy installed Python packages from builder
COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appgroup . /app

# Create persistent storage directories with appropriate permissions
RUN mkdir -p /app/storage/documents && \
    chown -R appuser:appgroup /app/storage

USER appuser

EXPOSE 8005

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005"]
