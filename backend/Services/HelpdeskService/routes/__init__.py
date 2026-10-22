# backend/Services/HelpdeskService/routes/__init__.py
from fastapi import APIRouter

from resources.adminDashboardController import router as admin_dashboard_router
from resources.authController import router as auth_router
from resources.chatController import router as chat_router
from resources.documentController import router as document_router
from resources.healthController import router as health_router
from resources.ticketController import admin_router as admin_ticket_router
from resources.ticketController import public_router as public_ticket_router

router = APIRouter()

# ── 1. Root /api router ────────────────────────────────────────────────────────
api_router = APIRouter(prefix="/api")

# /api/auth/*
api_router.include_router(auth_router, prefix="/auth", tags=["Auth (API)"])

# ── 2. /api/v1 router ──────────────────────────────────────────────────────────
v1_router = APIRouter(prefix="/v1")

# Public Routes (/api/v1/public/*)
public_router = APIRouter(prefix="/public")
public_router.include_router(health_router, prefix="", tags=["Public Health"])
public_router.include_router(chat_router, prefix="", tags=["Public Chat"])
public_router.include_router(public_ticket_router, prefix="", tags=["Public Tickets"])

# Admin Routes (/api/v1/admin/*)
admin_router = APIRouter(prefix="/admin")
admin_router.include_router(document_router, prefix="", tags=["Admin Documents"])
admin_router.include_router(admin_ticket_router, prefix="", tags=["Admin Tickets"])
admin_router.include_router(admin_dashboard_router, prefix="", tags=["Admin Dashboard"])

# Auth Routes (/api/v1/auth/*)
v1_router.include_router(auth_router, prefix="/auth", tags=["Auth (V1)"])

v1_router.include_router(public_router)
v1_router.include_router(admin_router)

# Mount /v1 under /api
api_router.include_router(v1_router)

# Expose primary router
router.include_router(api_router)
