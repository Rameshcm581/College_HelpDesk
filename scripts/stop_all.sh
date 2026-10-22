#!/usr/bin/env bash
# ==============================================================================
# Gracefully stop College AI Help Desk Local Stack
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Stopping containers..."
cd "${ROOT_DIR}"
docker compose stop helpdesk_db helpdesk_redis
echo "All containers stopped gracefully."
