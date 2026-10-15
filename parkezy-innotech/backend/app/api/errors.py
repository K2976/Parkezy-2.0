import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.errors import AppError, RateLimited
from app.db import errors as db_errors

log = logging.getLogger(__name__)


def _body(code: str, message: str, details=None) -> dict:
    return {"error": {"code": code, "message": message, "details": jsonable_encoder(details)}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(_: Request, exc: AppError) -> JSONResponse:
        headers = {}
        if isinstance(exc, RateLimited) and isinstance(exc.details, dict):
            headers["Retry-After"] = str(exc.details.get("retry_after_seconds", 60))
        if exc.status_code >= 500:
            log.warning("upstream failure: %s %s", exc.code, exc.details)
        return JSONResponse(_body(exc.code, exc.message, exc.details), status_code=exc.status_code, headers=headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(p) for p in err["loc"] if p != "body"), "message": err["msg"]}
            for err in exc.errors()
        ]
        return JSONResponse(_body("validation_failed", "Some fields are invalid", details), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed", 413: "payload_too_large"}.get(
            exc.status_code, "http_error"
        )
        return JSONResponse(_body(code, str(exc.detail)), status_code=exc.status_code)

    async def database_failure(request: Request, exc: Exception) -> JSONResponse:
        failure = db_errors.classify(exc)
        if failure is None:
            raise exc  # not a transient database problem: falls through to the 500 handler below
        # The database is busy or unreachable. The request failed and its transaction was rolled back;
        # tell the client to retry instead of reporting a bug.
        log.warning(
            "database unavailable: %s (%s) on %s %s",
            failure.reason,
            type(exc).__name__,
            request.method,
            request.url.path,
        )
        retry_after = request.app.state.container.settings.db_unavailable_retry_after_seconds
        return JSONResponse(
            _body(failure.code, failure.message, {"reason": failure.reason, "retry_after_seconds": retry_after}),
            status_code=503,
            headers={"Retry-After": str(retry_after)},
        )

    # Specific types are handled in the inner exception layer, so an expected outage is answered
    # like any other API error instead of being logged as an application crash.
    for exc_type in db_errors.HANDLED_TYPES:
        app.add_exception_handler(exc_type, database_failure)

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error")
        return JSONResponse(_body("internal_error", "Something went wrong on our side"), status_code=500)
