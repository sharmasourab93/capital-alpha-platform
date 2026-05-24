"""FastAPI middleware for the REST runtime."""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)


def register_request_logging(app: FastAPI) -> None:
    """Register request lifecycle logging."""

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        """Log request start, completion, and unexpected failure."""
        start_time = time.perf_counter()
        logger.info("HTTP start: %s %s", request.method, request.url.path)
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "HTTP failed: %s %s",
                request.method,
                request.url.path,
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "HTTP complete: %s %s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
