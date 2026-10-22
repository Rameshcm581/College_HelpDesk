# Verified Defect & Remediation Report

**Audit Date:** 2026-10-22  
**Classification System:**
- **P0 — Critical:** Security compromise, data loss, destructive bug, or unauthenticated administrative takeover.
- **P1 — High:** Core feature broken, authorization bypass, unreliable workflow, or RAG data corruption.
- **P2 — Medium:** Significant feature or workflow failure, script path breakage, or important edge case failure.
- **P3 — Low:** Cosmetic issue, noncritical usability defect, or documentation ambiguity.

---

## 1. Summary of Identified Defects

| Defect ID | Severity | Component | Summary | Status |
|:---|:---:|:---|:---|:---:|
| **DEF-001** | **P2** | Backend Operational Scripts | `ROOT_DIR` miscalculated in `backend/scripts/*.sh` causing failure | **VERIFIED & FIXED** |
| **OBS-001** | **P1 (Pre-Deploy)** | Configuration (`.env`) | Production OpenAI API Key & spending quota required | **DOCUMENTED** |
| **OBS-002** | **P1 (Pre-Deploy)** | Configuration (`.env`) | Production random `SECRET_KEY` & database passwords required | **DOCUMENTED** |
| **OBS-003** | **P1 (Pre-Deploy)** | Configuration (`.env`) | Institutional SMTP credentials required for live visitor emails | **DOCUMENTED** |

---

## 2. Detailed Defect Analysis & Verification

### DEF-001: Operational Scripts in `backend/scripts/` Fail Due to Relative Path Miscalculation

- **Defect Identifier:** `DEF-001`
- **Severity:** **P2 — Medium**
- **Affected Component:** `backend/scripts/lint_all.sh`, `backend/scripts/backup.sh`, `backend/scripts/restore_drill.sh`, `backend/scripts/start_all.sh`, `backend/scripts/stop_all.sh`
- **Steps to Reproduce:**
  1. Navigate to project root or backend folder.
  2. Execute `./backend/scripts/lint_all.sh` or `./backend/scripts/backup.sh`.
  3. Observe terminal failure:
     ```text
     ./backend/scripts/lint_all.sh: line 11: cd: .../college-ai-helpdesk/backend/frontend: No such file or directory
     compose file ".../college-ai-helpdesk/backend/docker-compose.yml" is invalid: open .../college-ai-helpdesk/backend/docker-compose.yml: no such file or directory
     ```
- **Root Cause:**
  The scripts in `backend/scripts/` were replicated from `scripts/` at the project root. While in `scripts/`, `SCRIPT_DIR/..` points to the project root, in `backend/scripts/`, `SCRIPT_DIR/..` resolved to `college-ai-helpdesk/backend`. Consequently, references to `${ROOT_DIR}/frontend`, `${ROOT_DIR}/docker-compose.yml`, and `${ROOT_DIR}/backend/Services` failed.
- **Remediation Applied:**
  Updated the `ROOT_DIR` definition in all affected scripts in `backend/scripts/`:
  ```diff
  - ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
  + ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
  ```
- **Verification Test:**
  Executed `./backend/scripts/lint_all.sh`.
  - Frontend TypeScript build: 1,533 modules built cleanly.
  - Frontend Vitest suite: 18 / 18 tests passed.
  - Backend Pytest suite: 58 / 58 tests passed in 23.85s.
  - Result: **CLEAN (Exit Code 0)**.

---

## 3. Operational Observations (Pre-Deployment Checklist)

These items are documented configuration requirements for live production deployment:

### OBS-001: OpenAI API Key & Monthly Spending Limit
- **Description:** For live production RAG generation, a valid `OPENAI_API_KEY` must be populated in the production `.env`.
- **Mitigation in Place:** The application has a verified deterministic mock provider in `resources/aiService.py` that activates automatically when the API key is empty or a placeholder, allowing full offline testing, QA, and local development without runtime crashes.

### OBS-002: Production Secret Keys & Passwords
- **Description:** Default development credentials (`dev-secret-change-me-32-chars-minimum-xx`, `helpdesk_dev_pass`, `helpdesk_redis_pass`) must be overridden before deploying to production.
- **Enforcement in Place:** `BaseConfig` in `configs/base_config.py` contains a guardrail that raises `RuntimeError` if `APP_ENV=prod` and `SECRET_KEY` is under 32 characters or contains default strings.

### OBS-003: Institutional SMTP Configuration
- **Description:** When running with mock email mode, OTP codes are logged in memory and returned with a dev hint in non-production mode. In production, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, and `SMTP_PASSWORD` must be provided to deliver real emails to students.
