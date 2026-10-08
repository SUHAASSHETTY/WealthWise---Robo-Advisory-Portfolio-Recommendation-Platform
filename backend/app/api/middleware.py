"""Correlation-ID middleware and request logging (NFR-06). Logs the route template, never raw paths or bodies."""

import logging
import re
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.core.logging import reset_correlation_id, set_correlation_id

REQUEST_ID_HEADER = "X-Request-ID"
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
logger = logging.getLogger("wealthwise.request")


def _incoming_or_new_request_id(request: Request) -> str:
    incoming = request.headers.get(REQUEST_ID_HEADER, "")
    return incoming if _SAFE_REQUEST_ID.fullmatch(incoming) else str(uuid.uuid4())


def _path_template(request: Request) -> str:
    route = request.scope.get("route")
    return str(getattr(route, "path", "<unmatched>"))


async def correlation_id_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    request_id = _incoming_or_new_request_id(request)
    token = set_correlation_id(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request completed",
            extra={
                "method": request.method,
                "path_template": _path_template(request),
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return response
    finally:
        reset_correlation_id(token)
