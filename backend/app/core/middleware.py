"""Request id, timing, metrics and security headers for every HTTP request; request body size limits."""

import json
import logging
import re
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core import metrics
from app.core.config import get_settings
from app.core.errors import error_body
from app.core.logging import request_id_var

logger = logging.getLogger("app.request")

_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}

# Only the Next.js server calls the API, but its answers hold a family's data: never cached, never
# shown in a frame, never read as anything but what they say they are.
_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}
# The API docs page (not served in production) loads its scripts from a CDN.
_CSP = "default-src 'none'; frame-ancestors 'none'"
_DOCS_PAGES = ("/docs", "/redoc")
_HSTS = "max-age=31536000; includeSubDomains"


def _route_pattern(scope: Scope) -> str:
    """`/api/v1/books/{book_id}` for a request to one book: the path with its parameters' names in
    place of their values. "unmatched" when no route took the request."""
    if "route" not in scope:
        return "unmatched"
    names = {str(value): name for name, value in scope.get("path_params", {}).items()}
    return "/".join(f"{{{names[part]}}}" if part in names else part for part in scope["path"].split("/"))


class RequestContextMiddleware:
    """Gives each request an id (returned as `X-Request-ID`) and the security headers, logs how long
    it took and counts it for monitoring (core/metrics).

    Only the method, path, status and duration are logged - never query
    strings or bodies, which can contain personal data. The metrics name the route's pattern
    (`/api/v1/books/{book_id}`), never the ids in the path.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self._production = get_settings().is_production

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get("x-request-id", "")
        request_id = incoming if _SAFE_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500

        async def send_with_headers(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                for name, value in _SECURITY_HEADERS.items():
                    headers.setdefault(name, value)  # a stream keeps its own Cache-Control
                if not scope["path"].startswith(_DOCS_PAGES):
                    headers["Content-Security-Policy"] = _CSP
                if self._production:
                    headers["Strict-Transport-Security"] = _HSTS
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            seconds = time.perf_counter() - started
            logger.info("%s %s -> %s in %.1f ms", scope["method"], scope["path"], status_code, seconds * 1000)
            method = scope["method"] if scope["method"] in _METHODS else "OTHER"
            route = _route_pattern(scope)
            metrics.HTTP_REQUESTS.labels(method, route, str(status_code)).inc()
            metrics.HTTP_SECONDS.labels(method, route).observe(seconds)
            request_id_var.reset(token)


_JSON_BODY_LIMIT = 1024 * 1024  # JSON requests are small; only uploads need more
_MULTIPART_OVERHEAD = 64 * 1024


class _BodyTooLarge(Exception):
    pass


class BodySizeLimitMiddleware:
    """Refuses request bodies that are too large, before they fill the disk or memory.

    Uploads (`multipart/form-data`) may be as large as MAX_UPLOAD_MB; everything else 1 MB. Both
    the declared Content-Length and the bytes actually received are checked.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        is_upload = headers.get("content-type", "").startswith("multipart/form-data")
        limit = get_settings().max_upload_bytes + _MULTIPART_OVERHEAD if is_upload else _JSON_BODY_LIMIT

        declared = headers.get("content-length")
        if declared is not None and declared.isdigit() and int(declared) > limit:
            await self._reject(send, is_upload)
            return

        received = 0
        exceeded = False
        response_started = False

        async def limited_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    exceeded = True
                    raise _BodyTooLarge
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal response_started
            if exceeded:
                # The framework turned our error into its own response (e.g. "error parsing the
                # body"); answer with the real reason instead, once.
                if message["type"] == "http.response.start" and not response_started:
                    response_started = True
                    await self._reject(send, is_upload)
                return
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except _BodyTooLarge:
            if not response_started:
                await self._reject(send, is_upload)

    @staticmethod
    async def _reject(send: Send, is_upload: bool) -> None:
        if is_upload:
            message = f"This file is larger than {get_settings().max_upload_mb} MB."
        else:
            message = "The request is too large."
        body = json.dumps(
            error_body("file_too_large" if is_upload else "payload_too_large", message)
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
