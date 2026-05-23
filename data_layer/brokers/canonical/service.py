"""Canonical broker REST service."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from data_layer.brokers.canonical.errors import (
    BrokerOperationError,
    CanonicalBrokerError,
)
from data_layer.brokers.canonical.models import (
    AccountRequest,
    AccountResponse,
    CandleRequest,
    CandleResponse,
    LtpRequest,
    LtpResponse,
    QuoteRequest,
    QuoteResponse,
    ScripListRequest,
    ScripListResponse,
    ScripRequest,
    ScripResponse,
)
from data_layer.brokers.canonical.ports import RestBrokerPort
from data_layer.brokers.canonical.registry import BrokerRegistry

ResponseT = TypeVar("ResponseT")


class BrokerRestService:
    """Canonical entry point for broker REST data access."""

    def __init__(self, registry: BrokerRegistry) -> None:
        """Create a service backed by a broker registry."""
        self._registry = registry

    @property
    def broker_names(self) -> list[str]:
        """Return registered broker names."""
        return self._registry.broker_names

    def get_scrip(self, request: ScripRequest) -> ScripResponse:
        """Return one broker instrument."""
        return self._dispatch(
            request.broker,
            "get_scrip",
            lambda adapter: adapter.get_scrip(request),
        )

    def get_all_scrips(self, request: ScripListRequest) -> ScripListResponse:
        """Return broker instruments for an exchange."""
        return self._dispatch(
            request.broker,
            "get_all_scrips",
            lambda adapter: adapter.get_all_scrips(request),
        )

    def get_ltp(self, request: LtpRequest) -> LtpResponse:
        """Return last traded price."""
        return self._dispatch(
            request.broker,
            "get_ltp",
            lambda adapter: adapter.get_ltp(request),
        )

    def get_quote(self, request: QuoteRequest) -> QuoteResponse:
        """Return quote data."""
        return self._dispatch(
            request.broker,
            "get_quote",
            lambda adapter: adapter.get_quote(request),
        )

    def get_candles(self, request: CandleRequest) -> CandleResponse:
        """Return historical candles."""
        return self._dispatch(
            request.broker,
            "get_candles",
            lambda adapter: adapter.get_candles(request),
        )

    def get_profile(self, request: AccountRequest) -> AccountResponse:
        """Return account profile."""
        return self._dispatch(
            request.broker,
            "get_profile",
            lambda adapter: adapter.get_profile(request),
        )

    def get_funds(self, request: AccountRequest) -> AccountResponse:
        """Return funds and margin details."""
        return self._dispatch(
            request.broker,
            "get_funds",
            lambda adapter: adapter.get_funds(request),
        )

    def get_holdings(self, request: AccountRequest) -> AccountResponse:
        """Return account holdings."""
        return self._dispatch(
            request.broker,
            "get_holdings",
            lambda adapter: adapter.get_holdings(request),
        )

    def get_positions(self, request: AccountRequest) -> AccountResponse:
        """Return account positions."""
        return self._dispatch(
            request.broker,
            "get_positions",
            lambda adapter: adapter.get_positions(request),
        )

    def get_order_book(self, request: AccountRequest) -> AccountResponse:
        """Return order book data."""
        return self._dispatch(
            request.broker,
            "get_order_book",
            lambda adapter: adapter.get_order_book(request),
        )

    def get_trade_book(self, request: AccountRequest) -> AccountResponse:
        """Return trade book data."""
        return self._dispatch(
            request.broker,
            "get_trade_book",
            lambda adapter: adapter.get_trade_book(request),
        )

    def _dispatch(
        self,
        broker: str,
        operation: str,
        call: Callable[[RestBrokerPort], ResponseT],
    ) -> ResponseT:
        """Resolve a broker and run one canonical operation."""
        adapter = self._registry.get(broker)
        try:
            return call(adapter)
        except CanonicalBrokerError:
            raise
        except Exception as exc:
            raise BrokerOperationError(
                "Broker operation failed",
                broker=broker,
                operation=operation,
                details={"reason": str(exc)},
            ) from exc
