"""HTTP error handling for REST routes."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
)
from data_layer.brokers.canonical.errors import (
    BrokerNotRegisteredError,
    BrokerOperationError,
    BrokerValidationError,
    CanonicalBrokerError,
)

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register application exception handlers."""

    @app.exception_handler(CanonicalBrokerError)
    async def canonical_error_handler(
        request: Request,
        exc: CanonicalBrokerError,
    ) -> JSONResponse:
        """Return structured canonical broker errors."""
        logger.warning(
            "Canonical broker error: method=%s path=%s code=%s details=%s",
            request.method,
            request.url.path,
            exc.code,
            exc.details,
        )
        return canonical_error_response(exc)

    @app.exception_handler(AngelOneSmartApiRestBrokerError)
    async def angelone_error_handler(
        request: Request,
        exc: AngelOneSmartApiRestBrokerError,
    ) -> JSONResponse:
        """Return structured AngelOne setup/runtime errors."""
        logger.exception(
            "AngelOne broker error: method=%s path=%s details=%s",
            request.method,
            request.url.path,
            exc.details,
        )
        return JSONResponse(
            status_code=503,
            content={
                "detail": {
                    "code": "ANGELONE_BROKER_ERROR",
                    "message": str(exc),
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Return stable JSON for unexpected errors."""
        logger.exception(
            "Unhandled REST error: method=%s path=%s",
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "Internal server error",
                }
            },
        )


def call_or_raise(operation) -> dict:
    """Run a route operation and map canonical errors."""
    try:
        return operation()
    except CanonicalBrokerError as exc:
        raise canonical_http_error(exc) from exc


def canonical_error_response(exc: CanonicalBrokerError) -> JSONResponse:
    """Convert canonical errors to JSON responses."""
    return JSONResponse(
        status_code=canonical_status_code(exc),
        content={
            "detail": {
                "code": exc.code,
                "message": str(exc),
                "details": exc.details,
            }
        },
    )


def canonical_http_error(exc: CanonicalBrokerError) -> HTTPException:
    """Convert canonical errors to FastAPI HTTP exceptions."""
    return HTTPException(
        status_code=canonical_status_code(exc),
        detail={
            "code": exc.code,
            "message": str(exc),
            "details": exc.details,
        },
    )


def canonical_status_code(exc: CanonicalBrokerError) -> int:
    """Return the HTTP status code for a canonical error."""
    if isinstance(exc, BrokerValidationError):
        return 422
    if isinstance(exc, BrokerNotRegisteredError):
        return 404
    if isinstance(exc, BrokerOperationError):
        return 502
    return 500
