"""Typed application errors. Services raise these; one handler turns them into JSON.

Response shape (stable contract for the mobile app):
    {"error": {"code": "booking_conflict", "message": "...", "details": {...}}}
"""

from typing import Any


class AppError(Exception):
    status_code: int = 400
    code: str = "bad_request"

    def __init__(self, message: str, *, code: str | None = None, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.details = details


class InvalidCharacters(AppError):
    """Input contains characters the system cannot store (U+0000). Malformed request -> 400."""

    status_code = 400
    code = "invalid_characters"


class ValidationFailed(AppError):
    status_code = 422
    code = "validation_failed"


class Unauthorized(AppError):
    status_code = 401
    code = "unauthorized"


class Forbidden(AppError):
    status_code = 403
    code = "forbidden"


class ChallengeRequired(AppError):
    """Login needs a solved challenge (CAPTCHA) first. Codes: challenge_required / challenge_failed.
    details carry only what the client needs to show the widget (provider, public site key)."""

    status_code = 403
    code = "challenge_required"


class NotFound(AppError):
    status_code = 404
    code = "not_found"


class Conflict(AppError):
    status_code = 409
    code = "conflict"


class RateLimited(AppError):
    status_code = 429
    code = "rate_limited"


class ServiceUnavailable(AppError):
    status_code = 503
    code = "service_unavailable"


class ExternalServiceError(AppError):
    status_code = 502
    code = "external_service_error"
