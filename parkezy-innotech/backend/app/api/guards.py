"""Request guards that run before any routing or parsing.

* Body size: requests larger than `request_max_body_bytes` get 413. A declared Content-Length is
  refused up front without reading anything; chunked/undeclared bodies are counted as they stream
  in and cut off as soon as they cross the limit.
* NUL in the URL: a percent-encoded %00 in the path or query string reaches query parameters as a
  real U+0000, which PostgreSQL cannot store. Refused with 400 before it gets that far.
* NUL in JSON bodies: `reject_nul_in_json_body`, a dependency on every /v1 route. It inspects the
  request only (never responses), with a byte-level fast path so normal bodies cost ~nothing.
"""

import json

from fastapi import HTTPException, Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import InvalidCharacters
from app.schemas.common import find_nul

BODY_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _error(code: str, message: str, details=None) -> bytes:
    return json.dumps({"error": {"code": code, "message": message, "details": details}}).encode()


async def _respond(send: Send, status: int, body: bytes) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
        }
    )
    await send({"type": "http.response.body", "body": body})


class RequestGuardMiddleware:
    def __init__(self, app: ASGIApp, *, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        query = scope.get("query_string", b"")
        if "\x00" in scope.get("path", "") or b"%00" in query.lower() or b"\x00" in query:
            await _respond(send, 400, _error("invalid_characters", "The URL may not contain NUL (%00) characters"))
            return

        limit = self.max_body_bytes
        if scope["method"] in BODY_METHODS:
            declared = next((v for k, v in scope.get("headers", []) if k == b"content-length"), None)
            if declared is not None and declared.isdigit() and int(declared) > limit:
                await _respond(send, 413, _too_large(limit))
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    # Raised inside the app's body read. FastAPI re-raises HTTPException from body parsing
                    # (anything else becomes a generic 400), and the error handler answers 413.
                    raise HTTPException(status_code=413, detail=f"Request body is larger than {limit} bytes")
            return message

        await self.app(scope, limited_receive, send)


def _too_large(limit: int) -> bytes:
    return _error("payload_too_large", f"Request body is larger than {limit} bytes", {"max_bytes": limit})


async def reject_nul_in_json_body(request: Request) -> None:
    """400 if any string or key in a JSON body contains U+0000 (PostgreSQL cannot store it).

    JSON can only carry NUL as the escape sequence \\u0000 (a raw 0x00 byte is invalid JSON and is
    already rejected as malformed), so bodies without that sequence skip parsing entirely. The body
    is the one FastAPI has already read and cached for this request."""
    if request.method not in BODY_METHODS or "json" not in request.headers.get("content-type", ""):
        return
    body = await request.body()
    if b"\\u0000" not in body:
        return
    try:
        data = json.loads(body)
    except ValueError:
        return  # malformed JSON is reported by FastAPI as 422
    where = find_nul(data)
    if where:
        raise InvalidCharacters(
            "Text may not contain NUL (\\u0000) characters",
            details=[{"field": where, "message": "contains a NUL character"}],
        )
