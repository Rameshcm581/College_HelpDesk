# backend/Services/HelpdeskService/resources/utils.py
from datetime import datetime, timedelta, timezone
import hashlib
import re
from typing import Any, Dict, Optional
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from configs.base_config import BaseConfig

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2id."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a password against an Argon2id hash."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Generates a short-lived JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta else timedelta(minutes=BaseConfig.ACCESS_TOKEN_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, BaseConfig.SECRET_KEY, algorithm=BaseConfig.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decodes and validates a JWT token."""
    try:
        payload = jwt.decode(token, BaseConfig.SECRET_KEY, algorithms=[BaseConfig.JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def calculate_sha256(content: bytes) -> str:
    """Calculates SHA-256 checksum of raw binary content."""
    return hashlib.sha256(content).hexdigest()


def mask_pii_for_logging(text_content: str) -> str:
    """Masks phone numbers and email addresses before logging or analytics storage."""
    # Mask Indian (+91 98765 43210 or 9876543210) & international phone formats
    masked = re.sub(r'(\+?91[\s.-]?)?[6-9]\d{4}[\s.-]?\d{5}', '[PHONE_REDACTED]', text_content)
    masked = re.sub(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', '[PHONE_REDACTED]', masked)
    # Mask emails
    masked = re.sub(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', '[EMAIL_REDACTED]', masked)
    return masked
