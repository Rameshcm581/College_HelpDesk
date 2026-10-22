# backend/Services/HelpdeskService/resources/authController.py
import uuid
from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import get_db
from models.models import Users
from resources.errors import UnauthorizedError
from resources.schemas import ApiResponse, LoginRequest, TokenResponse, UserSummary
from resources.utils import create_access_token, decode_access_token, verify_password

router = APIRouter()


@router.post("/login", response_model=ApiResponse, tags=["Authentication"])
async def login(
    req: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticates staff user and sets refresh cookie."""
    result = await db.execute(select(Users).where(Users.email == req.email))
    user = result.scalars().first()

    if not user or not verify_password(req.password, user.password_hash):
        raise UnauthorizedError("Invalid email or password.")

    if not user.is_active:
        raise UnauthorizedError("User account is deactivated.")

    # Create access token
    token_data = {"sub": str(user.id), "email": user.email, "role": user.role.value}
    access_token = create_access_token(token_data)

    user_summary = UserSummary(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        department_id=user.department_id,
    )

    token_resp = TokenResponse(
        access_token=access_token,
        expires_in=900,
        user=user_summary,
    )

    return ApiResponse(success=True, data=token_resp.model_dump())


@router.get("/me", response_model=ApiResponse, tags=["Authentication"])
async def get_current_user(
    authorization: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """Returns currently authenticated staff user."""
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header.")

    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise UnauthorizedError("Token is invalid or has expired.")

    user_id = uuid.UUID(payload["sub"])
    user = await db.get(Users, user_id)
    if not user or not user.is_active:
        raise UnauthorizedError("User does not exist or is inactive.")

    return ApiResponse(
        success=True,
        data={
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,
            "department_id": str(user.department_id) if user.department_id else None,
        },
    )


@router.post("/logout", response_model=ApiResponse, tags=["Authentication"])
async def logout(response: Response):
    """Clears refresh token cookie and logs out staff user."""
    response.delete_cookie(key="helpdesk_refresh")
    return ApiResponse(success=True, message="Successfully logged out.")
