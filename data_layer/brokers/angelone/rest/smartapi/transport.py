from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol

from data_layer.brokers.angelone.rest.smartapi.errors import (
    smart_api_error_handler,
)
from data_layer.brokers.angelone.rest.smartapi.payloads import (
    CandleRequest,
    LtpRequest,
    QuoteRequest,
)
from SmartApi import SmartConnect


class SmartApiClient(Protocol):
    def generate_session(
        self, client_code: str, password: str, totp: str
    ) -> dict[str, Any]: ...

    def terminate_session(self, client_code: str) -> dict[str, Any]: ...

    def get_candle_data(
        self, historic_data_params: dict[str, str]
    ) -> dict[str, Any]: ...

    def get_market_data(
        self, mode: str, exchange_tokens: dict[str, list[str]]
    ) -> dict[str, Any]: ...

    def ltp_data(
        self, exchange: str, tradingsymbol: str, symboltoken: str
    ) -> dict[str, Any]: ...

    def get_profile(self) -> dict[str, Any]: ...

    def rms_limit(self) -> dict[str, Any]: ...

    def holdings(self) -> dict[str, Any]: ...

    def position(self) -> dict[str, Any]: ...

    def order_book(self) -> dict[str, Any]: ...

    def trade_book(self) -> dict[str, Any]: ...


SmartApiClientFactory = Callable[[str], SmartApiClient]


class SmartConnectAdapter:
    def __init__(self, client: SmartConnect) -> None:
        self._client = client

    def generate_session(
        self, client_code: str, password: str, totp: str
    ) -> dict[str, Any]:
        return self._client.generateSession(client_code, password, totp)

    def terminate_session(self, client_code: str) -> dict[str, Any]:
        return self._client.terminateSession(client_code)

    def get_candle_data(
        self, historic_data_params: dict[str, str]
    ) -> dict[str, Any]:
        return self._client.getCandleData(historic_data_params)

    def get_market_data(
        self, mode: str, exchange_tokens: dict[str, list[str]]
    ) -> dict[str, Any]:
        return self._client.getMarketData(mode, exchange_tokens)

    def ltp_data(
        self, exchange: str, tradingsymbol: str, symboltoken: str
    ) -> dict[str, Any]:
        return self._client.ltpData(exchange, tradingsymbol, symboltoken)

    def get_profile(self) -> dict[str, Any]:
        return self._client.getProfile()

    def rms_limit(self) -> dict[str, Any]:
        return self._client.rmsLimit()

    def holdings(self) -> dict[str, Any]:
        return self._client.holding()

    def position(self) -> dict[str, Any]:
        return self._client.position()

    def order_book(self) -> dict[str, Any]:
        return self._client.orderBook()

    def trade_book(self) -> dict[str, Any]:
        return self._client.tradeBook()


def default_smart_api_client_factory(api_key: str) -> SmartApiClient:
    return SmartConnectAdapter(SmartConnect(api_key=api_key))


class SmartApiTransport:
    def __init__(self, client: SmartApiClient) -> None:
        self._client = client

    @smart_api_error_handler("Angel One candle retrieval failed")
    def get_candles(self, request: CandleRequest) -> dict[str, Any]:
        return self._client.get_candle_data(request.to_payload())

    @smart_api_error_handler("Angel One LTP retrieval failed")
    def get_ltp(self, request: LtpRequest) -> dict[str, Any]:
        return self._client.ltp_data(
            request.exchange,
            request.tradingsymbol,
            request.symboltoken,
        )

    @smart_api_error_handler("Angel One quote retrieval failed")
    def get_quote(self, request: QuoteRequest) -> dict[str, Any]:
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
