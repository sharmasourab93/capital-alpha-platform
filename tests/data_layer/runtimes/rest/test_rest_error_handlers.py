"""Tests for REST runtime error handlers."""

import asyncio

from starlette.requests import Request

from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
)
from data_layer.brokers.canonical.errors import (
    BrokerValidationError,
    CanonicalBrokerError,
)
from data_layer.runtimes.rest.app import create_app


def test_canonical_exception_handler_returns_json_response() -> None:
    """Verify canonical errors are returned as JSON."""
    app = create_app()
    handler = app.exception_handlers[CanonicalBrokerError]

    response = asyncio.run(
        handler(
            _request("/market/angelone/NSE/ltp"),
            BrokerValidationError("Bad request", {"field": "symbol"}),
        )
    )

    assert response.status_code == 422
    assert b"BROKER_VALIDATION_ERROR" in response.body


def test_angelone_exception_handler_returns_json_response() -> None:
    """Verify AngelOne setup errors are returned as JSON."""
    app = create_app()
    handler = app.exception_handlers[AngelOneSmartApiRestBrokerError]

    response = asyncio.run(
        handler(
            _request("/market/brokers"),
            AngelOneSmartApiRestBrokerError(
                "Missing AngelOne environment variable",
                {"env_var": "ANGELONE_API_KEY"},
            ),
        )
    )

    assert response.status_code == 503
    assert b"ANGELONE_BROKER_ERROR" in response.body


def test_unexpected_exception_handler_returns_json_response() -> None:
    """Verify unexpected errors are returned as stable JSON."""
    app = create_app()
    handler = app.exception_handlers[Exception]

    response = asyncio.run(
        handler(_request("/market/brokers"), RuntimeError("failure"))
    )

    assert response.status_code == 500
    assert b"INTERNAL_SERVER_ERROR" in response.body


def _request(path: str) -> Request:
    """Return a minimal Starlette request."""
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("testclient", 123),
        }
    )
