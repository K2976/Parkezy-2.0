import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.infra import metrics

log = logging.getLogger("parkezy.access")

# JSON API: nothing here should ever be sniffed as HTML, framed, or leak the URL to other sites.
SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"strict-transport-security", b"max-age=31536000; includeSubDomains"),
    (b"cache-control", b"no-store"),
]


def route_template(scope: Scope) -> str:
    """Full route template for metrics, e.g. /v1/bookings/{booking_id}.

    FastAPI includes routers lazily, so the matched route only knows its own path ("/bookings/...")
    without the "/v1" prefix it was mounted under. Prefixes are static, so put back the leading
    segments of the real path that the template doesn't cover."""
    template = getattr(scope.get("route"), "path", None)
    if not template:
        return "unmatched"
    real = scope["path"].strip("/").split("/")
    tail = template.strip("/").split("/")
    prefix = real[: max(0, len(real) - len(tail))]
    return "/" + "/".join(prefix + tail) if prefix else template


class RequestContextMiddleware:
    """Adds X-Request-ID and Server-Timing headers and logs one line per request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        request_id = headers.get(b"x-request-id", b"").decode()[:64] or uuid.uuid4().hex
        started = time.perf_counter()
        status = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                elapsed = (time.perf_counter() - started) * 1000
                message.setdefault("headers", [])
                message["headers"] += [
                    (b"x-request-id", request_id.encode()),
                    (b"server-timing", f"app;dur={elapsed:.1f}".encode()),
                    *SECURITY_HEADERS,
                ]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed_s = time.perf_counter() - started
            # Label by route template (/v1/bookings/{booking_id}), never the raw path, to bound cardinality.
            route = route_template(scope)
            metrics.observe(scope["method"], route, status, elapsed_s)
            log.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
