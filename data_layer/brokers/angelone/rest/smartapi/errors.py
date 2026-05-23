from __future__ import annotations

from functools import wraps


class AngelOneSmartApiRestBrokerError(Exception):
    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


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


__all__ = [
    "AngelOneSmartApiRestBrokerError",
    "broker_error_handler",
]
