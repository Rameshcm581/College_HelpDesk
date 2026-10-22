#!/usr/bin/env bash
# ==============================================================================
# Database Backup Script for College AI Help Desk
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKUP_DIR="${ROOT_DIR}/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/helpdesk_db_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

echo "Creating PostgreSQL snapshot to ${BACKUP_FILE}..."
docker compose -f "${ROOT_DIR}/docker-compose.yml" exec -T helpdesk_db \
    pg_dump -U helpdesk_user -d college_helpdesk_db -Fc > "${BACKUP_FILE}"

FILE_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "Backup created successfully: ${BACKUP_FILE} (${FILE_SIZE})"
