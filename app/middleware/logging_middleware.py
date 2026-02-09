"""Request/response logging middleware."""
import time
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.requests")


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log incoming requests and responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        method = request.method
        path = request.url.path
        client = request.client.host if request.client else "unknown"

        logger.info("→ %s %s [%s]", method, path, client)

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "← %s %s %d (%.0fms)",
                method,
                path,
                response.status_code,
                duration_ms,
            )
            return response
        except Exception as e:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "✗ %s %s FAILED after %.0fms: %s",
                method,
                path,
                duration_ms,
                str(e),
            )
            raise
