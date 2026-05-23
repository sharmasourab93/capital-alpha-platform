"""Canonical broker ports."""

from __future__ import annotations

from typing import Protocol

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


class RestBrokerPort(Protocol):
    """Broker-neutral REST operations required by the canonical service."""

    broker_name: str

    def get_scrip(self, request: ScripRequest) -> ScripResponse:
        """Return one broker instrument."""
        ...

    def get_all_scrips(self, request: ScripListRequest) -> ScripListResponse:
        """Return broker instruments for an exchange."""
        ...

    def get_ltp(self, request: LtpRequest) -> LtpResponse:
        """Return last traded price."""
        ...

    def get_quote(self, request: QuoteRequest) -> QuoteResponse:
        """Return quote data."""
        ...

    def get_candles(self, request: CandleRequest) -> CandleResponse:
        """Return historical candles."""
        ...

    def get_profile(self, request: AccountRequest) -> AccountResponse:
        """Return account profile."""
        ...

    def get_funds(self, request: AccountRequest) -> AccountResponse:
        """Return funds and margin details."""
        ...

    def get_holdings(self, request: AccountRequest) -> AccountResponse:
        """Return account holdings."""
        ...

    def get_positions(self, request: AccountRequest) -> AccountResponse:
        """Return account positions."""
        ...

    def get_order_book(self, request: AccountRequest) -> AccountResponse:
        """Return order book data."""
        ...

    def get_trade_book(self, request: AccountRequest) -> AccountResponse:
        """Return trade book data."""
        ...
