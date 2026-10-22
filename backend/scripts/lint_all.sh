#!/usr/bin/env bash
# ==============================================================================
# Quality Assurance & Linter Suite
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=== [1/2] Checking Frontend (TypeScript & Tests) ==="
cd "${ROOT_DIR}/frontend"
npm run build
npm test

echo "=== [2/2] Checking Backend (Pytest Suite) ==="
cd "${ROOT_DIR}/backend/Services/HelpdeskService"
"${ROOT_DIR}/backend/.venv/bin/pytest" -v

echo "=== All QA and lint checks passed successfully! ==="
