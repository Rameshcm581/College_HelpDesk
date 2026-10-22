# backend/Services/HelpdeskService/resources/errors.py
from datetime import datetime, timezone
import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class AppException(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500, details: dict = None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found", details: dict = None):
        super().__init__(message=message, code="NOT_FOUND", status_code=status.HTTP_404_NOT_FOUND, details=details)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Invalid credentials or token expired", details: dict = None):
        super().__init__(message=message, code="UNAUTHORIZED", status_code=status.HTTP_401_UNAUTHORIZED, details=details)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Access forbidden for this role", details: dict = None):
        super().__init__(message=message, code="FORBIDDEN", status_code=status.HTTP_403_FORBIDDEN, details=details)


class ConflictError(AppException):
    def __init__(self, message: str = "Resource conflict", details: dict = None):
        super().__init__(message=message, code="CONFLICT", status_code=status.HTTP_409_CONFLICT, details=details)


class FileValidationError(AppException):
    def __init__(self, message: str = "Invalid file or payload too large", status_code: int = status.HTTP_400_BAD_REQUEST, details: dict = None):
        super().__init__(message=message, code="FILE_VALIDATION_ERROR", status_code=status_code, details=details)


class ValidationError(AppException):
    def __init__(self, message: str = "Validation failed", details: dict = None):
        super().__init__(message=message, code="VALIDATION_ERROR", status_code=status.HTTP_400_BAD_REQUEST, details=details)


class OCRExtractionError(AppException):
    def __init__(self, message: str = "OCR extraction failure", details: dict = None):
        super().__init__(message=message, code="OCR_EXTRACTION_ERROR", status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, details=details)


class SSRFValidationError(AppException):
    def __init__(self, message: str = "Forbidden destination URL or SSRF attempt detected", details: dict = None):
        super().__init__(message=message, code="SSRF_FORBIDDEN_URL", status_code=status.HTTP_400_BAD_REQUEST, details=details)


class RateLimitError(AppException):
    def __init__(self, message: str = "Rate limit exceeded. Please wait before trying again.", details: dict = None):
        super().__init__(message=message, code="RATE_LIMIT_EXCEEDED", status_code=status.HTTP_429_TOO_MANY_REQUESTS, details=details)


def register_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(_request: Request, exc: AppException):
        logger.warning("AppException: %s [%s] details=%s", exc.message, exc.code, exc.details)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
        logger.warning("HTTPException: %s (status %s)", exc.detail, exc.status_code)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": str(exc.detail),
                    "details": {},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError):
        logger.warning("Validation error on request: %s", exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Input validation failed. Check request payload.",
                    "details": {"errors": exc.errors()},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(_request: Request, exc: Exception):
        logger.exception("Unhandled server exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected server error occurred. Please try again later.",
                    "details": {},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            },
        )
