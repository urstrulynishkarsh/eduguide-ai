"""Request id + timing for every HTTP request."""

import logging
import re
import time
import uuid

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

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
