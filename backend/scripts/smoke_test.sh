#!/usr/bin/env bash
# ==============================================================================
# Smoke test for College AI Help Desk
# ==============================================================================
set -euo pipefail

BASE_URL="${1:-http://localhost:8005}"

echo "=== Running Smoke Tests on ${BASE_URL} ==="

echo -n "1. Testing /health root alias: "
curl -fsS "${BASE_URL}/health" >/dev/null && echo "PASSED (200 OK)" || (echo "FAILED" && exit 1)

echo -n "2. Testing /api/v1/public/health deep check: "
curl -fsS "${BASE_URL}/api/v1/public/health" >/dev/null && echo "PASSED (200 OK)" || (echo "FAILED" && exit 1)

echo -n "3. Testing /api/v1/public/config: "
curl -fsS "${BASE_URL}/api/v1/public/config" >/dev/null && echo "PASSED (200 OK)" || (echo "FAILED" && exit 1)

echo -n "4. Testing /api/v1/public/live: "
curl -fsS "${BASE_URL}/api/v1/public/live" >/dev/null && echo "PASSED (200 OK)" || (echo "FAILED" && exit 1)

echo "=== All smoke tests passed successfully! ==="
