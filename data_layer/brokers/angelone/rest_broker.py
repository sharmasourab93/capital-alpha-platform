from __future__ import annotations

import os
from dataclasses import asdict

from data_layer.abs.broker_abs import (
    BrokerCapabilities,
    BrokerRequestContext,
    BrokerResponse,
    CandleRequest,
    InstrumentRequest,
    MarketDataBroker,
    QuoteRequest,
)

from .client import AngelOneCredentials, AngelOneHttpClient


class AngelOneRestBroker(MarketDataBroker):
    broker_name = "angelone"
    capabilities = BrokerCapabilities(
        supports_rest_quotes=True,
        supports_rest_candles=True,
        supports_rest_instruments=True,
    )

    QUOTE_PATH = "/rest/secure/angelbroking/market/v1/quote"
    CANDLE_PATH = "/rest/secure/angelbroking/historical/v1/getCandleData"
    SEARCH_SCRIP_PATH = "/rest/secure/angelbroking/order/v1/searchScrip"

    def __init__(self, client: AngelOneHttpClient | None = None) -> None:
        self.client = client or AngelOneHttpClient(
            credentials=self._credentials_from_env()
        )

    def fetch_quotes(
        self,
        request: QuoteRequest,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        if not request.instrument_tokens:
            raise ValueError("Angel One quotes require instrument_tokens")

        raw = self.client.post(
            self.QUOTE_PATH,
            {
                "mode": "FULL",
                "exchangeTokens": {
                    request.exchange: list(request.instrument_tokens),
                },
            },
        )
        return BrokerResponse(
            broker_name=self.broker_name,
            operation="fetch_quotes",
            payload=raw,
            response_meta={"exchange": request.exchange},
        )

    def fetch_candles(
        self,
        request: CandleRequest,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        if not request.instrument_token:
            raise ValueError("Angel One candles require instrument_token")

        raw = self.client.post(
            self.CANDLE_PATH,
            {
                "exchange": request.exchange,
                "symboltoken": request.instrument_token,
                "interval": self._map_interval(request.interval),
                "fromdate": request.from_date,
                "todate": request.to_date,
            },
        )
        return BrokerResponse(
            broker_name=self.broker_name,
            operation="fetch_candles",
            payload=raw,
            response_meta={
                "exchange": request.exchange,
                "interval": request.interval,
                "symbol": request.symbol,
                "instrument_token": request.instrument_token,
            },
        )

    def fetch_instruments(
        self,
        request: InstrumentRequest,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        if not request.query:
            raise ValueError("Angel One instrument search requires query")

        raw = self.client.post(
            self.SEARCH_SCRIP_PATH,
            {
                "exchange": request.exchange,
                "searchscrip": request.query,
            },
        )
        return BrokerResponse(
            broker_name=self.broker_name,
            operation="fetch_instruments",
            payload=raw,
            response_meta={
                "exchange": request.exchange,
                "query": request.query,
            },
        )

    def healthcheck(
        self,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        return BrokerResponse(
            broker_name=self.broker_name,
            operation="healthcheck",
            payload={"status": "configured"},
            response_meta={"capabilities": asdict(self.capabilities)},
        )

    @staticmethod
    def _map_interval(interval: str) -> str:
        mapping = {
            "1m": "ONE_MINUTE",
            "3m": "THREE_MINUTE",
            "5m": "FIVE_MINUTE",
            "10m": "TEN_MINUTE",
            "15m": "FIFTEEN_MINUTE",
            "30m": "THIRTY_MINUTE",
            "1h": "ONE_HOUR",
            "1d": "ONE_DAY",
        }
        try:
            return mapping[interval]
        except KeyError as exc:
            raise ValueError(
                "Unsupported Angel One interval: {0}".format(interval)
            ) from exc

    @staticmethod
    def _credentials_from_env() -> AngelOneCredentials:
        return AngelOneCredentials(
            api_key=_required_env("ANGELONE_API_KEY"),
            jwt_token=_required_env("ANGELONE_JWT_TOKEN"),
            client_local_ip=_required_env("ANGELONE_CLIENT_LOCAL_IP"),
            client_public_ip=_required_env("ANGELONE_CLIENT_PUBLIC_IP"),
            mac_address=_required_env("ANGELONE_MAC_ADDRESS"),
            user_type=os.getenv("ANGELONE_USER_TYPE", "USER"),
            source_id=os.getenv("ANGELONE_SOURCE_ID", "WEB"),
        )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError("{0} is not set".format(name))
    return value
