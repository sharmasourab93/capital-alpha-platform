from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, Protocol

from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
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


SmartApiClientFactory = Callable[[str], SmartApiClient]
TransportOperation = Callable[..., dict[str, Any]]


def default_smart_api_client_factory(api_key: str) -> SmartApiClient:
    return SmartConnect(api_key=api_key)


def smart_api_transport_error(
    message: str,
) -> Callable[[TransportOperation], TransportOperation]:
    def decorator(operation: TransportOperation) -> TransportOperation:
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


class SmartApiTransport:
    def __init__(self, client: SmartApiClient) -> None:
        self._client = client

    @smart_api_transport_error("Angel One candle retrieval failed")
    def get_candles(self, request: CandleRequest) -> dict[str, Any]:
        return self._client.get_candle_data(request.to_payload())

    @smart_api_transport_error("Angel One LTP retrieval failed")
    def get_ltp(self, request: LtpRequest) -> dict[str, Any]:
        return self._client.ltp_data(
            request.exchange,
            request.tradingsymbol,
            request.symboltoken,
        )

    @smart_api_transport_error("Angel One quote retrieval failed")
    def get_quote(self, request: QuoteRequest) -> dict[str, Any]:
        return self._client.get_market_data(
            request.mode,
            request.exchange_tokens,
        )


__all__ = [
    "SmartApiClient",
    "SmartApiClientFactory",
    "SmartApiTransport",
    "default_smart_api_client_factory",
]
