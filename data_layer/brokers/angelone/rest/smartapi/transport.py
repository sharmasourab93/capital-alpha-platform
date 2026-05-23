"""SmartAPI transport adapters for AngelOne market data."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from SmartApi import SmartConnect

from data_layer.brokers.angelone.rest.smartapi.errors import (
    smart_api_error_handler,
)
from data_layer.brokers.angelone.rest.smartapi.payloads import (
    CandleRequest,
    LtpRequest,
    QuoteRequest,
)


class SmartApiClient(Protocol):
    """Snake-case protocol for the SmartAPI methods this package uses."""

    def generate_session(
        self, client_code: str, password: str, totp: str
    ) -> dict[str, Any]:
        """Create a SmartAPI session."""
        ...

    def terminate_session(self, client_code: str) -> dict[str, Any]:
        """Terminate a SmartAPI session."""
        ...

    def get_candle_data(
        self, historic_data_params: dict[str, str]
    ) -> dict[str, Any]:
        """Return candle data from SmartAPI."""
        ...

    def get_market_data(
        self, mode: str, exchange_tokens: dict[str, list[str]]
    ) -> dict[str, Any]:
        """Return quote data from SmartAPI."""
        ...

    def ltp_data(
        self, exchange: str, tradingsymbol: str, symboltoken: str
    ) -> dict[str, Any]:
        """Return LTP data from SmartAPI."""
        ...

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
        """Return account positions."""
        ...

    def order_book(self) -> dict[str, Any]:
        """Return order book entries."""
        ...

    def trade_book(self) -> dict[str, Any]:
        """Return trade book entries."""
        ...


SmartApiClientFactory = Callable[[str], SmartApiClient]


class SmartConnectAdapter:
    """Adapt SmartAPI SDK camelCase calls to the local protocol."""

    def __init__(self, client: SmartConnect) -> None:
        """Store the SmartAPI SDK client."""
        self._client = client

    def generate_session(
        self, client_code: str, password: str, totp: str
    ) -> dict[str, Any]:
        """Create a SmartAPI session."""
        return self._client.generateSession(client_code, password, totp)

    def terminate_session(self, client_code: str) -> dict[str, Any]:
        """Terminate a SmartAPI session."""
        return self._client.terminateSession(client_code)

    def get_candle_data(
        self, historic_data_params: dict[str, str]
    ) -> dict[str, Any]:
        """Return candle data from SmartAPI."""
        return self._client.getCandleData(historic_data_params)

    def get_market_data(
        self, mode: str, exchange_tokens: dict[str, list[str]]
    ) -> dict[str, Any]:
        """Return quote data from SmartAPI."""
        return self._client.getMarketData(mode, exchange_tokens)

    def ltp_data(
        self, exchange: str, tradingsymbol: str, symboltoken: str
    ) -> dict[str, Any]:
        """Return LTP data from SmartAPI."""
        return self._client.ltpData(exchange, tradingsymbol, symboltoken)

    def get_profile(self) -> dict[str, Any]:
        """Return account profile details."""
        return self._client.getProfile()

    def rms_limit(self) -> dict[str, Any]:
        """Return funds and margin limits."""
        return self._client.rmsLimit()

    def holdings(self) -> dict[str, Any]:
        """Return account holdings."""
        return self._client.holding()

    def position(self) -> dict[str, Any]:
        """Return account positions."""
        return self._client.position()

    def order_book(self) -> dict[str, Any]:
        """Return order book entries."""
        return self._client.orderBook()

    def trade_book(self) -> dict[str, Any]:
        """Return trade book entries."""
        return self._client.tradeBook()


def default_smart_api_client_factory(api_key: str) -> SmartApiClient:
    """Create the default SmartAPI SDK-backed client."""
    return SmartConnectAdapter(SmartConnect(api_key=api_key))


class SmartApiTransport:
    """Validate SmartAPI market-data calls."""

    def __init__(self, client: SmartApiClient) -> None:
        """Store the SmartAPI client."""
        self._client = client

    @smart_api_error_handler("Angel One candle retrieval failed")
    def get_candles(self, request: CandleRequest) -> dict[str, Any]:
        """Return candle data for a prepared request."""
        return self._client.get_candle_data(request.to_payload())

    @smart_api_error_handler("Angel One LTP retrieval failed")
    def get_ltp(self, request: LtpRequest) -> dict[str, Any]:
        """Return LTP data for a prepared request."""
        return self._client.ltp_data(
            request.exchange,
            request.tradingsymbol,
            request.symboltoken,
        )

    @smart_api_error_handler("Angel One quote retrieval failed")
    def get_quote(self, request: QuoteRequest) -> dict[str, Any]:
        """Return quote data for a prepared request."""
        return self._client.get_market_data(
            request.mode,
            request.exchange_tokens,
        )


__all__ = [
    "SmartApiClient",
    "SmartApiClientFactory",
    "SmartConnectAdapter",
    "SmartApiTransport",
    "default_smart_api_client_factory",
]
