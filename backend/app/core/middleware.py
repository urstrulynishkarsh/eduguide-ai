"""Request id + timing for every HTTP request, and request body size limits."""

import json
import logging
import re
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings
from app.core.errors import error_body
from app.core.logging import request_id_var

logger = logging.getLogger("app.request")

_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


class RequestContextMiddleware:
    """Gives each request an id (returned as `X-Request-ID`) and logs how long it took.

    Only the method, path, status and duration are logged - never query
    strings or bodies, which can contain personal data.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = Headers(scope=scope).get("x-request-id", "")
        request_id = incoming if _SAFE_REQUEST_ID.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.info("%s %s -> %s in %.1f ms", scope["method"], scope["path"], status_code, duration_ms)
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
