# backend/Services/HelpdeskService/tests/test_admin_dashboard.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_dashboard_auth_and_overview(async_client: AsyncClient):
    """Verifies authentication and overview dashboard metrics."""
    # 1. Login as Super Admin
    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@college.edu", "password": "DevAdminSecret123#!"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Overview
    overview_resp = await async_client.get("/api/v1/admin/overview", headers=headers)
    assert overview_resp.status_code == 200
    data = overview_resp.json()["data"]

    assert "documents" in data
    assert "ingestion_jobs" in data
    assert "tickets" in data
    assert "knowledge_gaps" in data
    assert "usage" in data
    assert data["documents"]["total"] >= 1


@pytest.mark.asyncio
async def test_admin_knowledge_gaps(async_client: AsyncClient):
    """Verifies knowledge gaps endpoint returns unanswered questions and clusters."""
    login_resp = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@college.edu", "password": "DevAdminSecret123#!"},
    )
    token = login_resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/admin/knowledge-gaps", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]

    assert "total_unanswered" in data
    assert "unanswered_questions" in data
    assert "topic_clusters" in data


@pytest.mark.asyncio
async def test_rbac_user_management_super_admin_only(async_client: AsyncClient):
    """Verifies that user management is strictly restricted to Super Admin,
    and Department Staff / Viewer are rejected with 403 Forbidden.
    """
    # 1. Super Admin can list users
    login_sa = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@college.edu", "password": "DevAdminSecret123#!"},
    )
    token_sa = login_sa.json()["data"]["access_token"]
    headers_sa = {"Authorization": f"Bearer {token_sa}"}

    users_resp = await async_client.get("/api/v1/admin/users", headers=headers_sa)
    assert users_resp.status_code == 200
    assert len(users_resp.json()["data"]) >= 4

    # 2. Department Staff is forbidden from listing users
    login_staff = await async_client.post(
        "/api/auth/login",
        json={"email": "staff_hostel@college.edu", "password": "StaffSecret123#!"},
    )
    token_staff = login_staff.json()["data"]["access_token"]
    headers_staff = {"Authorization": f"Bearer {token_staff}"}

    resp_staff = await async_client.get("/api/v1/admin/users", headers=headers_staff)
    assert resp_staff.status_code == 403

    # 3. Viewer is forbidden from listing users
    login_viewer = await async_client.post(
        "/api/auth/login",
        json={"email": "auditor_viewer@college.edu", "password": "ViewerSecret123#!"},
    )
    token_viewer = login_viewer.json()["data"]["access_token"]
    headers_viewer = {"Authorization": f"Bearer {token_viewer}"}

    resp_viewer = await async_client.get("/api/v1/admin/users", headers=headers_viewer)
    assert resp_viewer.status_code == 403


@pytest.mark.asyncio
async def test_system_config_and_monitoring(async_client: AsyncClient):
    """Verifies configuration retrieval/update and monitoring telemetry."""
    login_sa = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@college.edu", "password": "DevAdminSecret123#!"},
    )
    token_sa = login_sa.json()["data"]["access_token"]
    headers_sa = {"Authorization": f"Bearer {token_sa}"}

    # 1. Get Config
    config_resp = await async_client.get("/api/v1/admin/config", headers=headers_sa)
    assert config_resp.status_code == 200
    cfg = config_resp.json()["data"]
    assert cfg["short_name"] == "SJCET"
    assert "approved_origins" in cfg

    # 2. Update Config
    update_resp = await async_client.put(
        "/api/v1/admin/config",
        headers=headers_sa,
        json={"tagline": "Updated Academic Excellence & Innovation"},
    )
    assert update_resp.status_code == 200

    # 3. Viewer can read config, but cannot update config (403)
    login_viewer = await async_client.post(
        "/api/auth/login",
        json={"email": "auditor_viewer@college.edu", "password": "ViewerSecret123#!"},
    )
    headers_viewer = {"Authorization": f"Bearer {login_viewer.json()['data']['access_token']}"}

    view_cfg = await async_client.get("/api/v1/admin/config", headers=headers_viewer)
    assert view_cfg.status_code == 200

    deny_update = await async_client.put(
        "/api/v1/admin/config",
        headers=headers_viewer,
        json={"tagline": "Illegal Modification Attempt"},
    )
    assert deny_update.status_code == 403

    # 4. Monitoring Telemetry
    mon_resp = await async_client.get("/api/v1/admin/monitoring", headers=headers_sa)
    assert mon_resp.status_code == 200
    mon_data = mon_resp.json()["data"]
    assert "ingestion_failures" in mon_data
    assert "latency_metrics" in mon_data
    assert "ai_usage" in mon_data
