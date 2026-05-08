from __future__ import annotations

import hmac
import json
import os
from collections import defaultdict, deque
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from time import time
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, Response

from data_layer.data_modes.rest.contracts import paths

_EXEMPT_PATHS = frozenset(
    {
        paths.HEALTH,
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    }
)
_ALL_SCOPES = frozenset(
    {
        "reference",
        "cash",
        "derivatives",
    }
)
_PATH_SCOPES = {
    **{path: "reference" for path in paths.REFERENCE_PATHS},
    **{path: "cash" for path in paths.CASH_PATHS},
    **{path: "derivatives" for path in paths.DERIVATIVES_PATHS},
}
_BODY_DATE_PATHS = paths.BODY_DATE_PATHS
_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M"


@dataclass(frozen=True)
class RestSecuritySettings:
    api_keys: tuple[str, ...]
    api_key_scopes: dict[str, frozenset[str]]
    allowed_origins: tuple[str, ...]
    trusted_hosts: tuple[str, ...]
    rate_limit_per_minute: int
    max_symbols_per_request: int
    max_resolve_requests: int
    max_history_days: int

    @property
    def auth_enabled(self) -> bool:
        return bool(self.api_keys)


class InMemoryRateLimiter:
    """Simple in-memory sliding-window limiter for one FastAPI process."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._entries: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def allow(self, *, subject: str, path: str, limit: int) -> bool:
        now = time()
        window_start = now - 60.0
        key = (subject, path)

        with self._lock:
            bucket = self._entries[key]
            while bucket and bucket[0] < window_start:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True


RATE_LIMITER = InMemoryRateLimiter()


def load_settings() -> RestSecuritySettings:
    """Load REST security settings from environment variables."""

    api_keys = tuple(_split_csv_env("REST_API_KEYS"))
    allowed_origins = tuple(_split_csv_env("REST_ALLOWED_ORIGINS"))
    trusted_hosts = tuple(_split_csv_env("REST_TRUSTED_HOSTS"))
    api_key_scopes = _load_api_key_scopes(api_keys)
    return RestSecuritySettings(
        api_keys=api_keys,
        api_key_scopes=api_key_scopes,
        allowed_origins=allowed_origins,
        trusted_hosts=trusted_hosts,
        rate_limit_per_minute=_int_env("REST_RATE_LIMIT_PER_MINUTE", 120),
        max_symbols_per_request=_int_env("REST_MAX_SYMBOLS_PER_REQUEST", 100),
        max_resolve_requests=_int_env("REST_MAX_RESOLVE_REQUESTS", 20),
        max_history_days=_int_env("REST_MAX_HISTORY_DAYS", 366),
    )


async def enforce_request_security(request: Request) -> Response | None:
    """Apply FastAPI-layer authentication, authorization, host, origin, and rate-limit checks."""

    settings = load_settings()
    if request.url.path in _EXEMPT_PATHS:
        return None

    origin_response = _handle_origin_policy(request, settings)
    if origin_response is not None:
        return origin_response

    host_response = _handle_trusted_host_policy(request, settings)
    if host_response is not None:
        return host_response

    api_key = request.headers.get("x-api-key")
    auth_response = _handle_api_key_policy(
        request=request,
        settings=settings,
        api_key=api_key,
    )
    if auth_response is not None:
        return auth_response

    subject = api_key or _client_identity(request)
    if not RATE_LIMITER.allow(
        subject=subject,
        path=request.url.path,
        limit=settings.rate_limit_per_minute,
    ):
        return _error_response(
            429,
            "RATE_LIMIT_EXCEEDED",
            "Rate limit exceeded for this API key or client.",
        )

    return None


def validate_rest_request(
    *,
    path: str,
    method: str,
    query: dict[str, str] | None,
    body: dict | None,
) -> None:
    """Validate request sizes and time-window bounds before routing to broker code."""

    settings = load_settings()
    payload = body or {}
    params = query or {}

    if path == paths.CASH_QUOTES and method == "POST":
        _validate_symbols(
            payload.get("symbols"), settings.max_symbols_per_request
        )

    if path == paths.DERIVATIVES_RESOLVE and method == "POST":
        requests = payload.get("requests") or []
        if len(requests) > settings.max_resolve_requests:
            raise ValueError(
                "requests exceeds maximum allowed size of {0}".format(
                    settings.max_resolve_requests
                )
            )

    if path in _BODY_DATE_PATHS and method == "POST":
        _validate_history_window(
            from_value=payload.get("from"),
            to_value=payload.get("to"),
            max_history_days=settings.max_history_days,
        )

    if path == paths.REFERENCE_EXCHANGE_SYMBOL_NAME_MAP and method == "GET":
        limit = params.get("limit")
        if limit is not None and int(limit) > 500:
            raise ValueError("limit exceeds maximum allowed size of 500")

    if (
        path
        in {
            paths.CASH_NSE_LISTED_STOCKS,
            paths.CASH_BSE_LISTED_STOCKS,
        }
        and method == "GET"
    ):
        limit = params.get("limit")
        if limit is not None and int(limit) > 500:
            raise ValueError("limit exceeds maximum allowed size of 500")


def _handle_origin_policy(
    request: Request,
    settings: RestSecuritySettings,
) -> Response | None:
    origin = request.headers.get("origin")
    if not settings.allowed_origins or not origin:
        return None

    if origin not in settings.allowed_origins:
        return _error_response(
            403,
            "ORIGIN_NOT_ALLOWED",
            "Origin is not allowed.",
        )

    if request.method == "OPTIONS" and request.headers.get(
        "access-control-request-method"
    ):
        return Response(
            status_code=204,
            headers=_cors_headers(origin),
        )

    return None


def _handle_trusted_host_policy(
    request: Request,
    settings: RestSecuritySettings,
) -> Response | None:
    if not settings.trusted_hosts:
        return None

    host = request.headers.get("host", "").split(":", 1)[0].lower()
    if host not in {value.lower() for value in settings.trusted_hosts}:
        return _error_response(
            400,
            "UNTRUSTED_HOST",
            "Host is not allowed.",
        )
    return None


def _handle_api_key_policy(
    *,
    request: Request,
    settings: RestSecuritySettings,
    api_key: str | None,
) -> Response | None:
    if not settings.auth_enabled:
        return None

    if not api_key:
        return _error_response(
            401,
            "AUTHENTICATION_REQUIRED",
            "Missing X-API-Key header.",
        )

    matched_key = _match_api_key(api_key, settings.api_keys)
    if matched_key is None:
        return _error_response(
            401,
            "INVALID_API_KEY",
            "Invalid API key.",
        )

    required_scope = _PATH_SCOPES.get(request.url.path)
    allowed_scopes = settings.api_key_scopes.get(matched_key, _ALL_SCOPES)
    if required_scope and required_scope not in allowed_scopes:
        return _error_response(
            403,
            "FORBIDDEN",
            "API key is not authorized for this endpoint.",
        )

    return None


def _match_api_key(candidate: str, valid_keys: Iterable[str]) -> str | None:
    for key in valid_keys:
        if hmac.compare_digest(candidate, key):
            return key
    return None


def _load_api_key_scopes(
    api_keys: tuple[str, ...],
) -> dict[str, frozenset[str]]:
    raw_value = os.getenv("REST_API_KEY_SCOPES", "").strip()
    default_mapping = {api_key: _ALL_SCOPES for api_key in api_keys}
    if not raw_value:
        return default_mapping

    payload = json.loads(raw_value)
    if not isinstance(payload, dict):
        raise ValueError("REST_API_KEY_SCOPES must be a JSON object")

    scopes: dict[str, frozenset[str]] = {}
    for api_key in api_keys:
        configured_scopes = payload.get(api_key, list(_ALL_SCOPES))
        if not isinstance(configured_scopes, list):
            raise ValueError(
                "REST_API_KEY_SCOPES[{0}] must be a list".format(api_key)
            )
        scopes[api_key] = frozenset(str(item) for item in configured_scopes)
    return scopes


def _validate_symbols(symbols: Any, limit: int) -> None:
    if not isinstance(symbols, list):
        raise ValueError("symbols must be a list")
    if len(symbols) > limit:
        raise ValueError(
            "symbols exceeds maximum allowed size of {0}".format(limit)
        )


def _validate_history_window(
    *,
    from_value: Any,
    to_value: Any,
    max_history_days: int,
) -> None:
    if not isinstance(from_value, str) or not isinstance(to_value, str):
        raise ValueError("from and to must be datetime strings")

    start = datetime.strptime(from_value, _TIMESTAMP_FORMAT)
    end = datetime.strptime(to_value, _TIMESTAMP_FORMAT)
    if end < start:
        raise ValueError("to must be greater than or equal to from")
    if (end - start).days > max_history_days:
        raise ValueError(
            "history window exceeds maximum allowed span of {0} days".format(
                max_history_days
            )
        )


def _split_csv_env(name: str) -> list[str]:
    raw_value = os.getenv(name, "")
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    return int(raw_value)


def _client_identity(request: Request) -> str:
    client = request.client.host if request.client else "unknown"
    return str(client)


def _cors_headers(origin: str) -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Headers": "Content-Type, X-API-Key, X-Request-Id",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Vary": "Origin",
    }


def _error_response(
    status_code: int,
    error_type: str,
    message: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": error_type,
                "message": message,
                "details": [],
            },
            "meta": {},
        },
    )
