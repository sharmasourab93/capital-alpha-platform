from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, Protocol

from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
)


class SmartApiAccountClient(Protocol):
    def get_profile(self) -> dict[str, Any]: ...

    def rms_limit(self) -> dict[str, Any]: ...

    def holdings(self) -> dict[str, Any]: ...

    def position(self) -> dict[str, Any]: ...

    def order_book(self) -> dict[str, Any]: ...

    def trade_book(self) -> dict[str, Any]: ...


AccountOperation = Callable[..., dict[str, Any]]


def smart_api_account_error(
    message: str,
) -> Callable[[AccountOperation], AccountOperation]:
    def decorator(operation: AccountOperation) -> AccountOperation:
        @wraps(operation)
        def wrapper(*args: Any, **kwargs: Any) -> dict[str, Any]:
            try:
                response = operation(*args, **kwargs)
            except AngelOneSmartApiRestBrokerError:
                raise
            except Exception as exc:
                raise AngelOneSmartApiRestBrokerError(message) from exc

            if not isinstance(response, dict):
                raise AngelOneSmartApiRestBrokerError(
                    message,
                    {"response": response},
                )
            return response

        return wrapper

    return decorator


class AngelOneAccountService:
    def __init__(self, client: SmartApiAccountClient) -> None:
        self._client = client

    @smart_api_account_error("Angel One profile retrieval failed")
    def get_profile(self) -> dict[str, Any]:
        return self._client.get_profile()

    @smart_api_account_error("Angel One funds retrieval failed")
    def get_funds(self) -> dict[str, Any]:
        return self._client.rms_limit()

    @smart_api_account_error("Angel One holdings retrieval failed")
    def get_holdings(self) -> dict[str, Any]:
        return self._client.holdings()

    @smart_api_account_error("Angel One positions retrieval failed")
    def get_positions(self) -> dict[str, Any]:
        return self._client.position()

    @smart_api_account_error("Angel One order book retrieval failed")
    def get_order_book(self) -> dict[str, Any]:
        return self._client.order_book()

    @smart_api_account_error("Angel One trade book retrieval failed")
    def get_trade_book(self) -> dict[str, Any]:
        return self._client.trade_book()


__all__ = [
    "AngelOneAccountService",
    "SmartApiAccountClient",
    "smart_api_account_error",
]
