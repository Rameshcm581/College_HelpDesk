# backend/Services/HelpdeskService/tests/test_auth.py
import pytest
from resources.utils import (
    calculate_sha256,
    create_access_token,
    decode_access_token,
    hash_password,
    mask_pii_for_logging,
    verify_password,
)


def test_argon2_password_hashing():
    """Verifies Argon2id password hashing and verification."""
    password = "SuperSecretPassword123#!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_generation_and_decoding():
    """Verifies creation and signature decoding of JWT tokens."""
    payload = {"sub": "u-12345", "email": "test@college.edu", "role": "SUPER_ADMIN"}
    token = create_access_token(payload)

    assert isinstance(token, str)
    decoded = decode_access_token(token)
    assert decoded is not None
    assert decoded["sub"] == "u-12345"
    assert decoded["email"] == "test@college.edu"
    assert decoded["role"] == "SUPER_ADMIN"


def test_pii_masking_utility():
    """Verifies automatic redaction of phone numbers and email addresses."""
    raw_query = "Contact me at student@example.com or phone +91 9876543210 about admission."
    masked = mask_pii_for_logging(raw_query)

    assert "student@example.com" not in masked
    assert "[EMAIL_REDACTED]" in masked
    assert "9876543210" not in masked
    assert "[PHONE_REDACTED]" in masked


def test_checksum_utility():
    """Verifies SHA-256 calculation."""
    content = b"Official Circular Content"
    checksum = calculate_sha256(content)
    assert len(checksum) == 64
