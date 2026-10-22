# backend/Services/HelpdeskService/resources/authDeps.py
import uuid
from typing import List, Optional
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from models import get_db
from models.models import Users, UserRole
from resources.errors import ForbiddenError, UnauthorizedError
from resources.utils import decode_access_token


# Role equivalence and compatibility mapping
ROLE_EQUIVALENCE = {
    UserRole.CONTENT_APPROVER: UserRole.ADMIN,
    UserRole.SUPPORT_AGENT: UserRole.DEPARTMENT_STAFF,
    UserRole.AUDITOR: UserRole.VIEWER,
}


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Users:
    """Dependency that extracts and validates the JWT Bearer token and returns the current user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header.")

    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise UnauthorizedError("Token is invalid or has expired.")

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise UnauthorizedError("Invalid user token format.")

    user = await db.get(Users, user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("User does not exist or is inactive.")

    return user


def require_roles(allowed_roles: List[UserRole]):
    """Returns a dependency callable enforcing role-based access control.
    Super Admins inherently possess all permissions. Legacy role aliases are mapped.
    """
    async def role_checker(user: Users = Depends(get_current_user)) -> Users:
        # 1. Super Admin possesses universal administrative access
        if user.role == UserRole.SUPER_ADMIN:
            return user

        # 2. Direct match
        if user.role in allowed_roles:
            return user

        # 3. Equivalence mapping (e.g. CONTENT_APPROVER -> ADMIN)
        normalized_role = ROLE_EQUIVALENCE.get(user.role)
        if normalized_role and normalized_role in allowed_roles:
            return user

        raise ForbiddenError(
            f"Access forbidden: role '{user.role.value}' does not have sufficient administrative privileges. Required one of: {[r.value for r in allowed_roles]}"
        )

    return role_checker


def check_department_scope(user: Users, target_department_id: Optional[uuid.UUID]) -> bool:
    """Enforces department data boundaries for department staff.
    Super Admin, Admin, and Viewers have institution-wide visibility.
    """
    if user.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.VIEWER, UserRole.AUDITOR):
        return True

    # Department staff are strictly bounded to their assigned department
    normalized_role = ROLE_EQUIVALENCE.get(user.role, user.role)
    if normalized_role == UserRole.DEPARTMENT_STAFF and user.department_id:
        if target_department_id and user.department_id != target_department_id:
            raise ForbiddenError("Access restricted: Staff can only access records for their assigned department.")

    return True
