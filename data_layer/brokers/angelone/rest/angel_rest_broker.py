from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from data_layer.abstractions.brokers.rest_broker import RestBroker
from data_layer.abstractions.instruments import BaseScripData
from data_layer.brokers.angelone.rest.angel_instrument import AngelOneBroker
from data_layer.brokers.angelone.rest.smartapi.account import (
    AngelOneAccountService,
)
from data_layer.brokers.angelone.rest.smartapi.instrument_resolver import (
    AngelInstrumentResolver,
)
from data_layer.brokers.angelone.rest.smartapi.payloads import (
    CandleRequest,
    LtpRequest,
    QuoteRequest,
)
from data_layer.brokers.angelone.rest.smartapi.session import (
    AngelOneSessionManager,
    SmartApiCredentials,
    TotpProvider,
    default_totp_provider,
)
from data_layer.brokers.angelone.rest.smartapi.transport import (
    SmartApiClient,
    SmartApiClientFactory,
    SmartApiTransport,
    default_smart_api_client_factory,
)


class AngelRestBroker(RestBroker):
    broker_name = "angelone"
    region = "INDIA"
    capabilities = {
        "supports_rest_quotes": True,
        "supports_rest_candles": True,
        "supports_rest_instruments": True,
    }

    def __init__(
        self,
        credentials: SmartApiCredentials,
        client: SmartApiClient | None = None,
        instruments: AngelOneBroker | None = None,
        *,
        client_factory: SmartApiClientFactory = default_smart_api_client_factory,
        account_service: AngelOneAccountService | None = None,
        resolver: AngelInstrumentResolver | None = None,
        session_manager: AngelOneSessionManager | None = None,
        totp_provider: TotpProvider = default_totp_provider,
        transport: SmartApiTransport | None = None,
    ) -> None:
        self._credentials = credentials
        self._client = client or client_factory(credentials.api_key)
        self._session_manager = session_manager or AngelOneSessionManager(
            self._client,
            credentials,
            totp_provider,
        )
        self._account_service = account_service or AngelOneAccountService(
            self._client
        )
        self._transport = transport or SmartApiTransport(self._client)
        self._resolver = resolver or AngelInstrumentResolver(
            instruments or AngelOneBroker.from_url()
        )
        self.instruments = self._resolver.instruments

    @property
    def client(self) -> SmartApiClient:
        return self._client

    @property
    def session(self) -> dict[str, Any] | None:
        return self._session_manager.session

    def login(self) -> dict[str, Any]:
        return self.authenticate()

    def logout(self) -> dict[str, Any]:
        return self.terminate()

    def authenticate(self) -> dict[str, Any]:
        return self._session_manager.authenticate()

    def ensure_authenticated(self) -> None:
        self._session_manager.ensure_authenticated()

    def terminate(self) -> dict[str, Any]:
        return self._session_manager.terminate()

    def get_scrip(self, exchange: str, key: str) -> BaseScripData | None:
        return self._resolver.get_scrip(exchange, key)

    def get_all_scrips(self, exchange: str = "NSE") -> list[str]:
        return self._resolver.get_all_scrips(exchange)

    def get_profile(self) -> dict[str, Any]:
        self.ensure_authenticated()
        return self._account_service.get_profile()

    def get_funds(self) -> dict[str, Any]:
        self.ensure_authenticated()
        return self._account_service.get_funds()

    def get_holdings(self) -> dict[str, Any]:
        self.ensure_authenticated()
        return self._account_service.get_holdings()

    def get_positions(self) -> dict[str, Any]:
        self.ensure_authenticated()
        return self._account_service.get_positions()

    def get_order_book(self) -> dict[str, Any]:
        self.ensure_authenticated()
        return self._account_service.get_order_book()

    def get_trade_book(self) -> dict[str, Any]:
        self.ensure_authenticated()
        return self._account_service.get_trade_book()

    def get_candles(
        self,
        exchange: str,
        key: str,
        interval: str,
        fromdate: str,
        todate: str,
    ) -> dict[str, Any]:
        scrip = self._resolver.require_scrip(exchange, key)
        request = CandleRequest.from_scrip(
            scrip,
            interval,
            fromdate,
            todate,
        )
        self.ensure_authenticated()
        return self._transport.get_candles(request)

    def get_ltp(self, exchange: str, key: str) -> dict[str, Any]:
        scrip = self._resolver.require_scrip(exchange, key)
        request = LtpRequest.from_scrip(scrip)
        self.ensure_authenticated()
        return self._transport.get_ltp(request)

    def get_quote(
        self,
        exchange: str,
        key: str | Sequence[str],
        mode: str = "FULL",
    ) -> dict[str, Any]:
        scrips = self._resolver.require_scrips(exchange, key)
        request = QuoteRequest.from_scrips(mode, scrips)
        self.ensure_authenticated()
        return self._transport.get_quote(request)


SmartAPICredentials = SmartApiCredentials


__all__ = [
    "AngelRestBroker",
    "CandleRequest",
    "SmartAPICredentials",
    "SmartApiCredentials",
]
