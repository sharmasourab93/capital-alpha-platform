from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any


@dataclass(frozen=True, slots=True)
class RetryConfig:
    max_attempts: int = 3
    initial_delay_seconds: float = 0.2
    backoff_multiplier: float = 2.0
    retry_status_codes: tuple[int, ...] = (408, 429, 500, 502, 503, 504)


DEFAULT_RETRY_CONFIG = RetryConfig()
SmartApiOperation = Callable[..., dict[str, Any]]


class AngelOneSmartApiRestBrokerError(Exception):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}

    @property
    def is_auth_failure(self) -> bool:
        return _is_auth_failure(self.details)


def smart_api_error_handler(
    message: str,
    *,
    retry_config: RetryConfig = DEFAULT_RETRY_CONFIG,
    validate_status: bool = True,
) -> Callable[[SmartApiOperation], SmartApiOperation]:
    def decorator(operation: SmartApiOperation) -> SmartApiOperation:
        @wraps(operation)
        def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            return call_smart_api(
                message,
                lambda: operation(*args, **kwargs),
                retry_config=retry_config,
                validate_status=validate_status,
            )

        return wrapper

    return decorator


def call_smart_api(
    message: str,
    operation: Callable[[], dict[str, Any]],
    *,
    retry_config: RetryConfig = DEFAULT_RETRY_CONFIG,
    validate_status: bool = True,
) -> dict[str, Any]:
    attempts = max(1, retry_config.max_attempts)
    delay = retry_config.initial_delay_seconds
    last_error: AngelOneSmartApiRestBrokerError | None = None

    for attempt in range(1, attempts + 1):
        try:
            response = operation()
            validate_smart_api_response(
                response,
                message,
                validate_status=validate_status,
            )
            return response
        except AngelOneSmartApiRestBrokerError as exc:
            if exc.is_auth_failure or not _should_retry_error(
                exc, retry_config
            ):
                raise
            last_error = exc
        except Exception as exc:
            last_error = AngelOneSmartApiRestBrokerError(
                message,
                {"reason": str(exc), "attempt": attempt},
            )

        if attempt < attempts:
            time.sleep(delay)
            delay *= retry_config.backoff_multiplier

    if last_error is not None:
        raise last_error

    raise AngelOneSmartApiRestBrokerError(message)


def validate_smart_api_response(
    response: Any,
    message: str,
    *,
    validate_status: bool = True,
) -> None:
    if not isinstance(response, dict):
        raise AngelOneSmartApiRestBrokerError(
            message,
            {"response": response},
        )

    if validate_status and response.get("status") is False:
        raise AngelOneSmartApiRestBrokerError(
            message,
            {"response": response},
        )


def broker_error_handler(message: str, details_builder=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except AngelOneSmartApiRestBrokerError:
                raise
            except Exception as exc:  # noqa: BLE001
                details = (
                    details_builder(*args, **kwargs) if details_builder else {}
                )
                details["reason"] = str(exc)
                raise AngelOneSmartApiRestBrokerError(
                    message, details
                ) from exc

        return wrapper

    return decorator


def _should_retry_error(
    error: AngelOneSmartApiRestBrokerError,
    retry_config: RetryConfig,
) -> bool:
    response = error.details.get("response")
    if not isinstance(response, dict):
        return True

    status_code = response.get("status_code") or response.get("statusCode")
    if isinstance(status_code, int):
        return status_code in retry_config.retry_status_codes

    error_code = str(response.get("errorcode") or "").upper()
    return error_code in {
        "AB1004",
        "AB1006",
        "429",
        "500",
        "502",
        "503",
        "504",
    }


def _is_auth_failure(details: dict[str, Any]) -> bool:
    response = details.get("response") or details.get("session")
    if not isinstance(response, dict):
        return False

    error_text = " ".join(
        str(response.get(field, ""))
        for field in ("message", "errorcode", "errorCode")
    ).lower()
    return any(
        token in error_text
        for token in ("token", "session", "auth", "jwt", "unauthorized")
    )


__all__ = [
    "DEFAULT_RETRY_CONFIG",
    "AngelOneSmartApiRestBrokerError",
    "RetryConfig",
    "broker_error_handler",
    "call_smart_api",
    "smart_api_error_handler",
    "validate_smart_api_response",
]
