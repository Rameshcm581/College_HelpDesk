#!/usr/bin/env bash
# ==============================================================================
# Start College AI Help Desk Local Stack
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== [1/4] Starting PostgreSQL with pgvector & Redis ==="
cd "${ROOT_DIR}"
docker compose up -d helpdesk_db helpdesk_redis

echo "=== [2/4] Waiting for PostgreSQL readiness ==="
until docker compose exec -T helpdesk_db pg_isready -U helpdesk_user -d college_helpdesk_db >/dev/null 2>&1; do
    echo "Waiting for database on port 5435..."
    sleep 2
done

echo "=== [3/4] Running Alembic Database Migrations ==="
cd "${ROOT_DIR}/backend/Services/HelpdeskService"
"${ROOT_DIR}/backend/.venv/bin/alembic" upgrade head

echo "=== [4/4] Starting FastAPI Backend on port 8005 ==="
echo "You can start the backend with:"
echo "cd ${ROOT_DIR}/backend/Services/HelpdeskService && ${ROOT_DIR}/backend/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8005 --reload"
echo "And frontend with:"
echo "cd ${ROOT_DIR}/frontend && npm run dev"
echo "Stack started successfully."
