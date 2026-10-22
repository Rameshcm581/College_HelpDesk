#!/usr/bin/env bash
# ==============================================================================
# Disaster Recovery / Restore Drill Script
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${ROOT_DIR}/backups"

LATEST_BACKUP=$(ls -t "${BACKUP_DIR}"/*.dump 2>/dev/null | head -n1 || true)

if [ -z "${LATEST_BACKUP}" ]; then
    echo "No backup file found in ${BACKUP_DIR}. Running backup first..."
    bash "${SCRIPT_DIR}/backup.sh"
    LATEST_BACKUP=$(ls -t "${BACKUP_DIR}"/*.dump | head -n1)
fi

echo "Verifying backup file integrity for: ${LATEST_BACKUP}"
docker compose -f "${ROOT_DIR}/docker-compose.yml" exec -T helpdesk_db \
    pg_restore --list < "${LATEST_BACKUP}" >/dev/null

echo "Restore drill PASSED: Backup archive catalog is valid and readable by pg_restore."
