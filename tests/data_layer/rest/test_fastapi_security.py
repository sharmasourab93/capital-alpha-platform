from __future__ import annotations

import asyncio
import importlib

import pytest
from starlette.requests import Request


def _load_security_module(monkeypatch, **env):
    for key in (
        "REST_API_KEYS",
        "REST_API_KEY_SCOPES",
        "REST_ALLOWED_ORIGINS",
        "REST_TRUSTED_HOSTS",
        "REST_RATE_LIMIT_PER_MINUTE",
        "REST_MAX_SYMBOLS_PER_REQUEST",
        "REST_MAX_RESOLVE_REQUESTS",
        "REST_MAX_HISTORY_DAYS",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    module = importlib.import_module("data_layer.data_modes.rest.security")
    module = importlib.reload(module)
    module.RATE_LIMITER = module.InMemoryRateLimiter()
    return module


def _request(
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    client_host: str = "127.0.0.1",
) -> Request:
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [
            (key.lower().encode("latin-1"), value.encode("latin-1"))
            for key, value in (headers or {}).items()
        ],
        "client": (client_host, 12345),
        "scheme": "http",
        "query_string": b"",
        "server": ("testserver", 80),
    }
    return Request(scope)


def test_health_is_exempt_from_api_key_auth(monkeypatch):
    security = _load_security_module(monkeypatch, REST_API_KEYS="secret-key")

    response = asyncio.run(
        security.enforce_request_security(_request("/health"))
    )

    assert response is None


def test_protected_route_requires_api_key(monkeypatch):
    security = _load_security_module(monkeypatch, REST_API_KEYS="secret-key")

    response = asyncio.run(
        security.enforce_request_security(
            _request("/market/reference/exchanges")
        )
    )

    assert response is not None
    assert response.status_code == 401


def test_valid_api_key_allows_route(monkeypatch):
    security = _load_security_module(monkeypatch, REST_API_KEYS="secret-key")

    response = asyncio.run(
        security.enforce_request_security(
            _request(
                "/market/reference/exchanges",
                headers={"x-api-key": "secret-key"},
            )
        )
    )

    assert response is None


def test_scope_restriction_blocks_unauthorized_route(monkeypatch):
    security = _load_security_module(
        monkeypatch,
        REST_API_KEYS="reference-key",
        REST_API_KEY_SCOPES='{"reference-key":["reference"]}',
    )

    response = asyncio.run(
        security.enforce_request_security(
            _request(
                "/market/cash/quotes",
                method="POST",
                headers={"x-api-key": "reference-key"},
            )
        )
    )

    assert response is not None
    assert response.status_code == 403


def test_trusted_host_policy_rejects_unlisted_host(monkeypatch):
    security = _load_security_module(
        monkeypatch,
        REST_TRUSTED_HOSTS="trusted.local",
    )

    response = asyncio.run(
        security.enforce_request_security(
            _request(
                "/market/reference/exchanges",
                headers={"host": "evil.local"},
            )
        )
    )

    assert response is not None
    assert response.status_code == 400


def test_cors_origin_policy_rejects_unlisted_origin(monkeypatch):
    security = _load_security_module(
        monkeypatch,
        REST_ALLOWED_ORIGINS="https://allowed.example.com",
    )

    response = asyncio.run(
        security.enforce_request_security(
            _request(
                "/market/reference/exchanges",
                headers={"origin": "https://blocked.example.com"},
            )
        )
    )

    assert response is not None
    assert response.status_code == 403


def test_cors_preflight_returns_allow_headers_for_allowed_origin(monkeypatch):
    security = _load_security_module(
        monkeypatch,
        REST_ALLOWED_ORIGINS="https://allowed.example.com",
    )

    response = asyncio.run(
        security.enforce_request_security(
            _request(
                "/market/reference/exchanges",
                method="OPTIONS",
                headers={
                    "origin": "https://allowed.example.com",
                    "access-control-request-method": "GET",
                },
            )
        )
    )

    assert response is not None
    assert response.status_code == 204
    assert (
        response.headers["Access-Control-Allow-Origin"]
        == "https://allowed.example.com"
    )


def test_rate_limit_returns_429_after_limit(monkeypatch):
    security = _load_security_module(
        monkeypatch,
        REST_API_KEYS="limited-key",
        REST_RATE_LIMIT_PER_MINUTE="1",
    )
    request = _request(
        "/market/reference/exchanges",
        headers={"x-api-key": "limited-key"},
    )

    first = asyncio.run(security.enforce_request_security(request))
    second = asyncio.run(security.enforce_request_security(request))

    assert first is None
    assert second is not None
    assert second.status_code == 429


def test_request_guard_rejects_oversized_symbols_payload(monkeypatch):
    security = _load_security_module(
        monkeypatch,
        REST_MAX_SYMBOLS_PER_REQUEST="1",
    )

    with pytest.raises(ValueError, match="symbols exceeds maximum"):
        security.validate_rest_request(
            path="/market/cash/quotes",
            method="POST",
            query={},
            body={
                "symbols": ["SBIN", "RELIANCE"],
            },
        )


def test_request_guard_rejects_large_history_window(monkeypatch):
    security = _load_security_module(
        monkeypatch,
        REST_MAX_HISTORY_DAYS="30",
    )

    with pytest.raises(ValueError, match="history window exceeds maximum"):
        security.validate_rest_request(
            path="/market/derivatives/history",
            method="POST",
            query={},
            body={
                "from": "2026-01-01 09:15",
                "to": "2026-03-15 15:30",
            },
        )
