# backend/Services/HelpdeskService/tests/test_ticket_workflow.py
from datetime import datetime, timedelta, timezone
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from models import get_db
from models.models import (
    Departments,
    TicketCategory,
    TicketMessages,
    TicketOtps,
    TicketPriority,
    TicketStatus,
    TicketStatusHistory,
    Tickets,
    UserRole,
    Users,
)
from resources.emailService import MockTestEmailProvider, email_service


@pytest.fixture(autouse=True)
def setup_mock_email():
    """Configures MockTestEmailProvider for clean notification assertions."""
    mock_provider = MockTestEmailProvider()
    email_service.provider = mock_provider
    yield mock_provider
    email_service.provider = MockTestEmailProvider()


@pytest.mark.asyncio
async def test_ticket_creation_and_routing(async_client: AsyncClient, setup_mock_email: MockTestEmailProvider):
    """Verifies ticket creation with department routing, SLA calculation, and notification."""
    payload = {
        "student_name": "Priya Sharma",
        "student_email": "priya.sharma@example.com",
        "student_phone": "+91 9876543210",
        "category": "hostel",
        "subject": "Room Allocation Query for Academic Year 2026-27",
        "message": "When will the room allocation list for 2nd year girls hostel be released?",
        "priority": "high",
    }

    resp = await async_client.post("/api/v1/public/tickets", json=payload)
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    data = body["data"]

    ticket_number = data["ticket_number"]
    assert ticket_number.startswith("TCK-")
    assert data["status"] == "OPEN"
    assert data["category"] == "HOSTEL"
    assert data["department_code"] == "HST"
    assert data["sla_due_at"] is not None

    # Verify notification dispatched to visitor
    assert len(setup_mock_email.sent_emails) == 1
    sent = setup_mock_email.sent_emails[0]
    assert sent["to_email"] == "priya.sharma@example.com"
    assert ticket_number in sent["subject"]
    assert "Ticket Created" in sent["subject"]


@pytest.mark.asyncio
async def test_ticket_creation_fees_routing(async_client: AsyncClient):
    """Verifies fees category routes directly to Accounts & Finance (FIN)."""
    payload = {
        "student_name": "Rohan Kumar",
        "student_email": "rohan.kumar@example.com",
        "category": "fees",
        "subject": "Semester 3 Fee Receipt Discrepancy",
        "message": "Amount was deducted via UPI but portal still shows pending status.",
        "priority": "urgent",
    }
    resp = await async_client.post("/api/v1/public/tickets", json=payload)
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["department_code"] == "FIN"
    assert data["category"] == "FEES"


@pytest.mark.asyncio
async def test_visitor_otp_generation_verification_and_tracking(
    async_client: AsyncClient, setup_mock_email: MockTestEmailProvider
):
    """Tests OTP generation, verification, and secured ticket tracking for visitors."""
    # 1. Create a ticket
    create_resp = await async_client.post(
        "/api/v1/public/tickets",
        json={
            "student_name": "Ananya Krishnan",
            "student_email": "ananya.k@example.com",
            "category": "admissions",
            "subject": "Lateral Entry Eligibility",
            "message": "What is the cutoff percentage for Diploma mechanical lateral entry?",
            "priority": "medium",
        },
    )
    assert create_resp.status_code == 201
    ticket_num = create_resp.json()["data"]["ticket_number"]
    setup_mock_email.clear()

    # 2. Request OTP
    otp_req_resp = await async_client.post(
        f"/api/v1/public/tickets/{ticket_num}/request-otp",
        json={"email": "ananya.k@example.com"},
    )
    assert otp_req_resp.status_code == 200
    assert len(setup_mock_email.sent_emails) == 1
    otp_email = setup_mock_email.sent_emails[0]
    assert otp_email["to_email"] == "ananya.k@example.com"

    # Extract the 6-digit OTP from the email body
    import re
    match = re.search(r"\b\d{6}\b", otp_email["text_content"])
    assert match is not None, "6-digit OTP must be present in the dispatched notification"
    otp_code = match.group(0)

    # 3. Verify OTP with incorrect code first
    bad_verify = await async_client.post(
        f"/api/v1/public/tickets/{ticket_num}/verify-otp",
        json={"email": "ananya.k@example.com", "otp": "999999"},
    )
    assert bad_verify.status_code == 401
    assert "Invalid verification code" in bad_verify.json()["error"]["message"]

    # 4. Verify OTP with correct code
    good_verify = await async_client.post(
        f"/api/v1/public/tickets/{ticket_num}/verify-otp",
        json={"email": "ananya.k@example.com", "otp": otp_code},
    )
    assert good_verify.status_code == 200
    token = good_verify.json()["data"]["access_token"]
    assert token is not None

    # 5. Access ticket without token -> 401
    unauth_resp = await async_client.get(f"/api/v1/public/tickets/{ticket_num}")
    assert unauth_resp.status_code == 401

    # 6. Access ticket with valid visitor token
    auth_headers = {"Authorization": f"Bearer {token}"}
    track_resp = await async_client.get(f"/api/v1/public/tickets/{ticket_num}", headers=auth_headers)
    assert track_resp.status_code == 200
    ticket_data = track_resp.json()["data"]
    assert ticket_data["ticket_number"] == ticket_num
    assert ticket_data["student_email"] == "ananya.k@example.com"
    assert len(ticket_data["messages"]) >= 1

    # 7. Visitor sends a reply
    reply_resp = await async_client.post(
        f"/api/v1/public/tickets/{ticket_num}/messages",
        headers=auth_headers,
        json={"message": "Thank you, also what is the last date to apply?"},
    )
    assert reply_resp.status_code == 200


@pytest.mark.asyncio
async def test_otp_rate_limiting(async_client: AsyncClient):
    """Ensures OTP requests are rate-limited to prevent abuse (max 3 per 10m)."""
    create_resp = await async_client.post(
        "/api/v1/public/tickets",
        json={
            "student_name": "Test RateLimit",
            "student_email": "ratelimit@example.com",
            "category": "general",
            "subject": "Campus Tour",
            "message": "Are weekend campus tours available for prospective students?",
            "priority": "low",
        },
    )
    ticket_num = create_resp.json()["data"]["ticket_number"]

    # Fire 3 OTP requests successfully
    for _ in range(3):
        res = await async_client.post(
            f"/api/v1/public/tickets/{ticket_num}/request-otp",
            json={"email": "ratelimit@example.com"},
        )
        assert res.status_code == 200

    # 4th OTP request must be rejected with 429
    res_exceeded = await async_client.post(
        f"/api/v1/public/tickets/{ticket_num}/request-otp",
        json={"email": "ratelimit@example.com"},
    )
    assert res_exceeded.status_code == 429
    assert res_exceeded.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_staff_ticket_lifecycle_and_state_machine(
    async_client: AsyncClient, setup_mock_email: MockTestEmailProvider
):
    """Tests the complete staff ticket lifecycle:
    OPEN -> ASSIGNED -> IN_PROGRESS -> WAITING_FOR_USER -> RESOLVED -> CLOSED.
    Validates invalid transition rejection and resolution note requirements.
    """
    # 1. Login as Super Admin
    admin_login = await async_client.post(
        "/api/auth/login",
        json={"email": "admin@college.edu", "password": "DevAdminSecret123#!"},
    )
    admin_token = admin_login.json()["data"]["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Create ticket
    create_resp = await async_client.post(
        "/api/v1/public/tickets",
        json={
            "student_name": "Vikram Seth",
            "student_email": "vikram.seth@example.com",
            "category": "scholarships",
            "subject": "Merit Cum Means Scholarship Renewal",
            "message": "I submitted my renewal documents last week. Could you confirm receipt?",
            "priority": "medium",
        },
    )
    ticket_data = create_resp.json()["data"]
    ticket_id = ticket_data["id"]
    ticket_num = ticket_data["ticket_number"]
    assert ticket_data["status"] == "OPEN"

    # 3. Invalid transition test: Attempt to jump directly from OPEN to RESOLVED
    bad_transition = await async_client.patch(
        f"/api/v1/admin/tickets/{ticket_id}/status",
        headers=admin_headers,
        json={"status": "RESOLVED", "reason": "Quick fix"},
    )
    assert bad_transition.status_code == 400
    assert "Invalid transition" in bad_transition.json()["error"]["message"]

    # 4. Assign staff (Auto-transitions OPEN -> ASSIGNED)
    user_me = await async_client.get("/api/auth/me", headers=admin_headers)
    user_id = user_me.json()["data"]["id"]

    assign_resp = await async_client.post(
        f"/api/v1/admin/tickets/{ticket_id}/assign",
        headers=admin_headers,
        json={"assigned_to_user_id": user_id, "note": "Assigned to head of scholarships for verification"},
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["data"]["status"] == "ASSIGNED"

    # 5. Move ASSIGNED -> IN_PROGRESS
    in_prog_resp = await async_client.patch(
        f"/api/v1/admin/tickets/{ticket_id}/status",
        headers=admin_headers,
        json={"status": "IN_PROGRESS", "reason": "Staff actively reviewing physical income certificate"},
    )
    assert in_prog_resp.status_code == 200
    assert in_prog_resp.json()["data"]["status"] == "IN_PROGRESS"

    # 6. Add Internal Staff Note (Not visible to visitor, no status change)
    internal_note_resp = await async_client.post(
        f"/api/v1/admin/tickets/{ticket_id}/messages",
        headers=admin_headers,
        json={
            "message": "Income certificate verified from Tehsildar portal. Awaiting bank passbook.",
            "is_internal_note": True,
        },
    )
    assert internal_note_resp.status_code == 200
    assert internal_note_resp.json()["data"]["is_internal_note"] is True

    # 7. Reply to visitor (Moves IN_PROGRESS -> WAITING_FOR_USER automatically)
    setup_mock_email.clear()
    reply_to_visitor = await async_client.post(
        f"/api/v1/admin/tickets/{ticket_id}/messages",
        headers=admin_headers,
        json={
            "message": "Your income certificate is approved. Please upload your bank passbook first page.",
            "is_internal_note": False,
        },
    )
    assert reply_to_visitor.status_code == 200
    assert reply_to_visitor.json()["data"]["status"] == "WAITING_FOR_USER"
    assert len(setup_mock_email.sent_emails) == 1
    assert "Response" in setup_mock_email.sent_emails[0]["subject"]

    # 8. Attempt RESOLVED without resolution notes -> 400
    bad_resolve = await async_client.patch(
        f"/api/v1/admin/tickets/{ticket_id}/status",
        headers=admin_headers,
        json={"status": "RESOLVED"},
    )
    assert bad_resolve.status_code == 400
    assert "Resolution information is required" in bad_resolve.json()["error"]["message"]

    # 9. Correctly Resolve with resolution notes
    resolve_resp = await async_client.patch(
        f"/api/v1/admin/tickets/{ticket_id}/status",
        headers=admin_headers,
        json={
            "status": "RESOLVED",
            "resolution_notes": "All documents received and approved. Scholarship sanctioned.",
            "reason": "Complete verification",
        },
    )
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["data"]["status"] == "RESOLVED"

    # 10. Close ticket (RESOLVED -> CLOSED)
    close_resp = await async_client.patch(
        f"/api/v1/admin/tickets/{ticket_id}/status",
        headers=admin_headers,
        json={"status": "CLOSED", "reason": "Archived after resolution"},
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["data"]["status"] == "CLOSED"

    # 11. Verify ticket history audit trail
    detail_resp = await async_client.get(f"/api/v1/admin/tickets/{ticket_id}", headers=admin_headers)
    assert detail_resp.status_code == 200
    history = detail_resp.json()["data"]["status_history"]
    assert len(history) >= 5  # OPEN -> ASSIGNED -> IN_PROGRESS -> WAITING_FOR_USER -> RESOLVED -> CLOSED


@pytest.mark.asyncio
async def test_department_staff_rbac_boundaries(async_client: AsyncClient):
    """Ensures department staff can only view/manage tickets for their department."""
    # 1. Login as Hostel Staff (department_code = 'HST')
    staff_login = await async_client.post(
        "/api/auth/login",
        json={"email": "staff_hostel@college.edu", "password": "StaffSecret123#!"},
    )
    staff_token = staff_login.json()["data"]["access_token"]
    staff_headers = {"Authorization": f"Bearer {staff_token}"}

    # 2. Create an Admissions ticket (routed to ADM)
    adm_ticket = await async_client.post(
        "/api/v1/public/tickets",
        json={
            "student_name": "Applicant Ram",
            "student_email": "ram@example.com",
            "category": "admissions",
            "subject": "Direct Admission Fees",
            "message": "What is the fee structure for management quota?",
            "priority": "low",
        },
    )
    adm_ticket_id = adm_ticket.json()["data"]["id"]

    # 3. Create a Hostel ticket (routed to HST)
    hst_ticket = await async_client.post(
        "/api/v1/public/tickets",
        json={
            "student_name": "Hostel Resident Sita",
            "student_email": "sita@example.com",
            "category": "hostel",
            "subject": "Wi-Fi in Block B",
            "message": "Block B 2nd floor router is not working.",
            "priority": "medium",
        },
    )
    hst_ticket_id = hst_ticket.json()["data"]["id"]

    # 4. Hostel staff lists tickets -> should include HST ticket, but NOT ADM ticket
    list_resp = await async_client.get("/api/v1/admin/tickets", headers=staff_headers)
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]
    ticket_ids = [t["id"] for t in items]
    assert hst_ticket_id in ticket_ids
    assert adm_ticket_id not in ticket_ids

    # 5. Hostel staff tries to view ADM ticket detail directly -> 403 Forbidden
    detail_resp = await async_client.get(f"/api/v1/admin/tickets/{adm_ticket_id}", headers=staff_headers)
    assert detail_resp.status_code == 403
    assert detail_resp.json()["error"]["code"] == "FORBIDDEN"

    # 6. Hostel staff views HST ticket -> 200 OK
    hst_detail = await async_client.get(f"/api/v1/admin/tickets/{hst_ticket_id}", headers=staff_headers)
    assert hst_detail.status_code == 200


@pytest.mark.asyncio
async def test_unconfigured_email_provider_behavior(async_client: AsyncClient):
    """Ensures that when no email provider is configured, the system does not
    simulate successful email delivery, but still processes the ticket safely.
    """
    from resources.emailService import UnconfiguredEmailProvider

    # Explicitly set unconfigured provider
    email_service.provider = UnconfiguredEmailProvider()
    assert email_service.provider.is_configured() is False

    resp = await async_client.post(
        "/api/v1/public/tickets",
        json={
            "student_name": "Unconfigured Test",
            "student_email": "unconfigured@example.com",
            "category": "placements",
            "subject": "On-Campus Drive Schedule",
            "message": "When will the next IT product company drive commence?",
            "priority": "low",
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    # Strictly must NOT simulate successful notification
    assert data["notification_sent"] is False


@pytest.mark.asyncio
async def test_otp_max_attempts_and_invalidation(async_client: AsyncClient):
    """Tests that exceeding max OTP attempts (3) locks and invalidates the code."""
    # 1. Create ticket
    create_resp = await async_client.post(
        "/api/v1/public/tickets",
        json={
            "student_name": "Lockout Test",
            "student_email": "lockout@example.com",
            "category": "examinations",
            "subject": "Revaluation Results",
            "message": "When will Nov/Dec 2025 revaluation results be published?",
            "priority": "medium",
        },
    )
    ticket_num = create_resp.json()["data"]["ticket_number"]

    # 2. Request OTP
    otp_req = await async_client.post(
        f"/api/v1/public/tickets/{ticket_num}/request-otp",
        json={"email": "lockout@example.com"},
    )
    assert otp_req.status_code == 200

    # 3. Fail 3 times
    for attempt in range(1, 4):
        verify_fail = await async_client.post(
            f"/api/v1/public/tickets/{ticket_num}/verify-otp",
            json={"email": "lockout@example.com", "otp": "000000"},
        )
        assert verify_fail.status_code == 401

    # 4. 4th attempt must be rejected with 429 Maximum verification attempts exceeded
    fourth_attempt = await async_client.post(
        f"/api/v1/public/tickets/{ticket_num}/verify-otp",
        json={"email": "lockout@example.com", "otp": "000000"},
    )
    assert fourth_attempt.status_code == 429
    assert "Maximum verification attempts exceeded" in fourth_attempt.json()["error"]["message"]

