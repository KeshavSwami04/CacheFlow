"""
Two middlewares:

1. RequestContextMiddleware — assigns X-Request-ID, binds it into structlog
   contextvars for per-request log correlation.

2. PrometheusMiddleware — records per-request HTTP metrics (count + duration)
   using the route *template* (`/api/v1/urls/{url_id}`) rather than the raw
   URL path, avoiding label-cardinality explosions from path parameters.
"""
import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core import metrics as m

logger = structlog.get_logger("http")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            path=request.url.path,
            method=request.method,
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled_exception")
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Records cacheflow_http_requests_total and
    cacheflow_http_request_duration_seconds for every request.

    Uses the matched route path (e.g. /api/v1/urls/{url_id}) as the
    `endpoint` label so each distinct API operation gets its own time
    series without cardinality blowing up with per-ID paths.
    """

    _SKIP_PATHS = {"/metrics", "/api/v1/health/live", "/api/v1/health/ready"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self._SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        route = request.scope.get("route")
        endpoint = route.path if route else request.url.path
        method = request.method
        status = str(response.status_code)

        m.http_requests_total.labels(method=method, endpoint=endpoint, status_code=status).inc()
        m.http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

        return response
