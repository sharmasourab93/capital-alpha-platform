"""AngelOne SmartAPI account operations."""

from __future__ import annotations

from typing import Any, Protocol

from data_layer.brokers.angelone.rest.smartapi.errors import (
    smart_api_error_handler,
)


class SmartApiAccountClient(Protocol):
    """SmartAPI account methods used by AngelOneAccountService."""

    def get_profile(self) -> dict[str, Any]:
        """Return account profile details."""
        ...

    def rms_limit(self) -> dict[str, Any]:
        """Return funds and margin limits."""
        ...

    def holdings(self) -> dict[str, Any]:
        """Return account holdings."""
        ...

    def position(self) -> dict[str, Any]:
        """Return open positions."""
        ...

    def order_book(self) -> dict[str, Any]:
        """Return order book entries."""
        ...

    def trade_book(self) -> dict[str, Any]:
        """Return trade book entries."""
        ...


class AngelOneAccountService:
    """Validate and normalize SmartAPI account calls."""

    def __init__(self, client: SmartApiAccountClient) -> None:
        """Store the SmartAPI account client."""
        self._client = client

    @smart_api_error_handler("Angel One profile retrieval failed")
    def get_profile(self) -> dict[str, Any]:
        """Return account profile details."""
        return self._client.get_profile()

    @smart_api_error_handler("Angel One funds retrieval failed")
    def get_funds(self) -> dict[str, Any]:
        """Return funds and margin limits."""
        return self._client.rms_limit()

    @smart_api_error_handler("Angel One holdings retrieval failed")
    def get_holdings(self) -> dict[str, Any]:
        """Return account holdings."""
        return self._client.holdings()

    @smart_api_error_handler("Angel One positions retrieval failed")
    def get_positions(self) -> dict[str, Any]:
        """Return open positions."""
        return self._client.position()

    @smart_api_error_handler("Angel One order book retrieval failed")
    def get_order_book(self) -> dict[str, Any]:
        """Return order book entries."""
        return self._client.order_book()

    @smart_api_error_handler("Angel One trade book retrieval failed")
    def get_trade_book(self) -> dict[str, Any]:
        """Return trade book entries."""
        return self._client.trade_book()


__all__ = [
    "AngelOneAccountService",
    "SmartApiAccountClient",
]
