from __future__ import annotations

import time
from dataclasses import asdict

from SmartApi import SmartConnect

from data_layer.abs import (
    BrokerCapabilities,
    BrokerRequestContext,
    BrokerResponse,
    CandleRequest,
    DerivativeInstrumentRequest,
    InstrumentRequest,
    MarketDataBroker,
    QuoteRequest,
)

from .errors import AngelOneSmartApiRestBrokerError, broker_error_handler
from .instrument_master import AngelInstrumentMaster
from .smartapi import (
    SmartApiCredentials,
    SmartApiSessionManager,
    SmartApiTransport,
)
from .smartapi.utils import (
    chunk_sequence,
    map_interval,
    require_symbols,
    require_tokens,
    required_env,
    validate_bulk_chunk_size,
)


class AngelOneSmartApiRestBroker(MarketDataBroker):
    broker_name = "angelone"
    capabilities = BrokerCapabilities(
        supports_rest_quotes=True,
        supports_rest_candles=True,
        supports_rest_instruments=True,
    )

    def __init__(
        self,
        client: SmartConnect | None = None,
        client_code: str | None = None,
        password: str | None = None,
        totp_secret: str | None = None,
    ) -> None:
        credentials = SmartApiCredentials(
            api_key=required_env("ANGELONE_API_KEY"),
            client_code=client_code or required_env("ANGELONE_CLIENTCODE"),
            password=password or required_env("ANGELONE_PASSWORD"),
            totp_secret=totp_secret or required_env("ANGELONE_TOTP_SECRET"),
        )
        resolved_client = client or SmartConnect(credentials.api_key)

        self.api_key = credentials.api_key
        self.client_code = credentials.client_code
        self.password = credentials.password
        self.totp_secret = credentials.totp_secret

        self._session_manager = SmartApiSessionManager(
            client=resolved_client,
            credentials=credentials,
        )
        self._transport = SmartApiTransport(resolved_client)
        self.market_data: AngelInstrumentMaster | None = None

    @property
    def client(self) -> SmartConnect:
        return self._session_manager.client

    @property
    def session(self) -> dict | None:
        return self._session_manager.session

    @broker_error_handler("Angel One authentication failed")
    def authenticate(self) -> dict:
        return self._session_manager.authenticate()

    def fetch_quotes(
        self,
        request: QuoteRequest,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        symbols = require_symbols(request.symbols, "quotes")
        tokens = self._resolve_symbol_tokens(symbols, request.exchange)
        return self.fetch_quotes_by_tokens(
            exchange=request.exchange,
            instrument_tokens=tuple(tokens),
            mode=request.mode or "FULL",
            context=context,
            symbols=symbols,
        )

    def fetch_quotes_by_tokens(
        self,
        exchange: str,
        instrument_tokens: tuple[str, ...],
        mode: str = "FULL",
        context: BrokerRequestContext | None = None,
        symbols: tuple[str, ...] | None = None,
    ) -> BrokerResponse:
        del context
        normalized_exchange = exchange.upper()
        tokens = require_tokens(instrument_tokens, "quotes_by_tokens")
        payload = {
            "mode": mode,
            "exchangeTokens": {normalized_exchange: list(tokens)},
        }

        self._ensure_authenticated()
        raw = self._call_market_data(payload)
        return self._response(
            operation="fetch_quotes_by_tokens",
            payload=raw,
            exchange=normalized_exchange,
            symbols=symbols or (),
            tokens=list(tokens),
            mode=mode,
        )

    def fetch_bulk_quotes(
        self,
        request: QuoteRequest,
        context: BrokerRequestContext | None = None,
        chunk_size: int = 50,
        pause_seconds: float = 1.05,
    ) -> BrokerResponse:
        symbols = require_symbols(request.symbols, "bulk_quotes")
        tokens = self._resolve_symbol_tokens(symbols, request.exchange)
        return self.fetch_bulk_quotes_by_tokens(
            exchange=request.exchange,
            instrument_tokens=tuple(tokens),
            mode=request.mode or "LTP",
            context=context,
            symbols=symbols,
            chunk_size=chunk_size,
            pause_seconds=pause_seconds,
        )

    def fetch_bulk_quotes_by_tokens(
        self,
        exchange: str,
        instrument_tokens: tuple[str, ...],
        mode: str = "LTP",
        context: BrokerRequestContext | None = None,
        symbols: tuple[str, ...] | None = None,
        chunk_size: int = 50,
        pause_seconds: float = 1.05,
    ) -> BrokerResponse:
        del context
        normalized_exchange = exchange.upper()
        tokens = require_tokens(instrument_tokens, "bulk_quotes_by_tokens")
        normalized_chunk_size = validate_bulk_chunk_size(chunk_size)
        token_chunks = list(chunk_sequence(tokens, normalized_chunk_size))
        chunk_responses: list[dict] = []
        merged_data: list[dict] = []

        for index, token_chunk in enumerate(token_chunks):
            payload = {
                "mode": mode,
                "exchangeTokens": {
                    normalized_exchange: list(token_chunk),
                },
            }
            raw = self._call_market_data(payload)
            self._validate_bulk_quote_chunk_response(
                raw=raw,
                exchange=normalized_exchange,
                mode=mode,
                token_chunk=token_chunk,
                chunk_index=index,
            )
            chunk_responses.append(raw)

            if isinstance(raw, dict) and isinstance(raw.get("data"), list):
                merged_data.extend(raw["data"])

            if pause_seconds > 0 and index < len(token_chunks) - 1:
                time.sleep(pause_seconds)

        return self._response(
            operation="fetch_bulk_quotes",
            payload=self._merge_bulk_quote_payloads(
                chunk_responses,
                merged_data,
            ),
            exchange=normalized_exchange,
            symbols=symbols or (),
            tokens=list(tokens),
            mode=mode,
            chunk_size=normalized_chunk_size,
            chunk_count=len(token_chunks),
            rate_limit_pause_seconds=pause_seconds,
        )

    @broker_error_handler(
        "Angel One candle request failed",
        lambda self, request, context=None: {
            "exchange": request.exchange,
            "interval": request.interval,
            "fromdate": request.from_date,
            "todate": request.to_date,
            "instrument_token": request.instrument_token,
        },
    )
    def fetch_candles(
        self,
        request: CandleRequest,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        if not request.instrument_token:
            raise AngelOneSmartApiRestBrokerError(
                "Angel One candles require instrument_token"
            )

        payload = {
            "exchange": request.exchange,
            "symboltoken": request.instrument_token,
            "interval": map_interval(request.interval),
            "fromdate": request.from_date,
            "todate": request.to_date,
        }

        self._ensure_authenticated()
        raw = self._transport.get_candle_data(payload)
        return self._response(
            operation="fetch_candles",
            payload=raw,
            exchange=request.exchange,
            interval=request.interval,
            instrument_token=request.instrument_token,
            symbol=request.symbol,
        )

    @broker_error_handler(
        "Angel One instrument search failed",
        lambda self, request, context=None: {
            "exchange": request.exchange,
            "query": request.query,
        },
    )
    def fetch_instruments(
        self,
        request: InstrumentRequest,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        if not request.query:
            raise AngelOneSmartApiRestBrokerError(
                "Angel One instrument search requires query"
            )

        self._ensure_authenticated()
        raw = self._transport.search_scrip(request.exchange, request.query)
        return self._response(
            operation="fetch_instruments",
            payload=raw,
            exchange=request.exchange,
            query=request.query,
        )

    def fetch_exchange_symbol_name_map(
        self,
        exchange: str | None = None,
        query: str | None = None,
        offset: int = 0,
        limit: int = 100,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        market_data = self._get_market_data()
        if exchange:
            payload = market_data.get_symbol_name_page(
                exchange,
                query=query,
                offset=offset,
                limit=limit,
            )
            return self._response(
                operation="fetch_exchange_symbol_name_map",
                payload=payload,
                mode="page",
                exchange=exchange.upper(),
                query=query,
                offset=offset,
                limit=limit,
            )

        counts_by_exchange = market_data.get_symbol_name_counts_by_exchange()
        payload = {
            "exchanges": [
                {
                    "exchange": exchange_name,
                    "symbol_count": symbol_count,
                }
                for exchange_name, symbol_count in sorted(
                    counts_by_exchange.items()
                )
            ]
        }
        return self._response(
            operation="fetch_exchange_symbol_name_map",
            payload=payload,
            mode="summary",
            exchange_count=len(counts_by_exchange),
        )

    def fetch_exchanges(
        self,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        exchanges = self._get_market_data().get_exchanges()
        return self._response(
            operation="fetch_exchanges",
            payload=exchanges,
            exchange_count=len(exchanges),
        )

    def fetch_instrument_types(
        self,
        exchange: str | None = None,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        instrument_types = self._get_market_data().get_instrument_types(
            exchange
        )
        return self._response(
            operation="fetch_instrument_types",
            payload=instrument_types,
            exchange=exchange.upper() if exchange else None,
            instrument_type_count=len(instrument_types),
        )

    def fetch_listed_equities(
        self,
        exchange: str,
        offset: int = 0,
        limit: int = 100,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        payload = self._get_market_data().get_listed_equities(
            exchange,
            offset=offset,
            limit=limit,
        )
        return self._response(
            operation="fetch_listed_equities",
            payload=payload,
            exchange=exchange.upper(),
            offset=offset,
            limit=limit,
            instrument_count=payload["count"],
            instrument_total=payload["total"],
        )

    def fetch_stock_names(
        self,
        exchange: str,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        names = self._get_market_data().get_stock_names(exchange)
        return self._response(
            operation="fetch_stock_names",
            payload=names,
            exchange=exchange.upper(),
            stock_count=len(names),
        )

    def fetch_stock_instruments(
        self,
        exchange: str,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        instruments = self._get_market_data().get_stock_instruments(exchange)
        return self._response(
            operation="fetch_stock_instruments",
            payload=[instrument.as_dict() for instrument in instruments],
            exchange=exchange.upper(),
            stock_count=len(instruments),
        )

    def fetch_stock_instruments_by_name(
        self,
        *,
        exchange: str,
        name: str,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        instruments = (
            self._get_market_data().resolve_equity_instruments_by_name(
                exchange,
                name,
            )
        )
        return self._response(
            operation="fetch_stock_instruments_by_name",
            payload=[instrument.as_dict() for instrument in instruments],
            exchange=exchange.upper(),
            name=name,
            stock_count=len(instruments),
        )

    def fetch_derivative_symbols(
        self,
        exchange: str | None = None,
        instrument_type: str | None = None,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        derivative_symbols = self._get_market_data().get_derivative_symbols(
            exchange=exchange,
            instrument_type=instrument_type,
        )
        return self._response(
            operation="fetch_derivative_symbols",
            payload=derivative_symbols,
            exchange=exchange.upper() if exchange else None,
            instrument_type=(
                instrument_type.upper() if instrument_type else None
            ),
            exchange_count=len(derivative_symbols),
        )

    def fetch_derivative_underlyings(
        self,
        *,
        exchange: str | None = None,
        instrument_type: str | None = None,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        derivative_underlyings = (
            self._get_market_data().get_derivative_underlyings(
                exchange=exchange,
                instrument_type=instrument_type,
            )
        )
        return self._response(
            operation="fetch_derivative_underlyings",
            payload=derivative_underlyings,
            exchange=exchange.upper() if exchange else None,
            instrument_type=(
                instrument_type.upper() if instrument_type else None
            ),
            exchange_count=len(derivative_underlyings),
        )

    def fetch_derivative_market_catalog(
        self,
        *,
        exchange: str,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        catalog = self._get_market_data().get_derivative_catalog(exchange)
        if catalog is None:
            payload = None
            exchange_count = 0
        else:
            payload = {
                "exchange": catalog.exchange,
                "instrument_types": {
                    instrument_type: list(underlyings)
                    for instrument_type, underlyings in sorted(
                        catalog.underlyings_by_instrument_type.items()
                    )
                },
            }
            exchange_count = len(catalog.families_by_instrument_type)
        return self._response(
            operation="fetch_derivative_market_catalog",
            payload=payload,
            exchange=exchange.upper(),
            instrument_type_count=exchange_count,
        )

    def fetch_derivative_expiries(
        self,
        *,
        exchange: str,
        underlying: str,
        instrument_type: str,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        expiries = self._get_market_data().get_derivative_expiries(
            exchange=exchange,
            underlying=underlying,
            instrument_type=instrument_type,
        )
        return self._response(
            operation="fetch_derivative_expiries",
            payload=expiries,
            exchange=exchange.upper(),
            underlying=underlying.upper(),
            instrument_type=instrument_type.upper(),
            expiry_count=len(expiries),
        )

    def fetch_derivative_contracts(
        self,
        *,
        exchange: str,
        underlying: str,
        instrument_type: str,
        expiry: str,
        option_type: str | None = None,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        contracts = self._get_market_data().get_derivative_contracts(
            exchange=exchange,
            underlying=underlying,
            instrument_type=instrument_type,
            expiry=expiry,
            option_type=option_type,
        )
        return self._response(
            operation="fetch_derivative_contracts",
            payload=contracts,
            exchange=exchange.upper(),
            underlying=underlying.upper(),
            instrument_type=instrument_type.upper(),
            expiry=expiry,
            option_type=option_type.upper() if option_type else None,
            contract_count=len(contracts),
        )

    def fetch_derivative_strikes(
        self,
        *,
        exchange: str,
        underlying: str,
        instrument_type: str,
        expiry: str,
        option_type: str | None = None,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        strikes = self._get_market_data().get_derivative_strikes(
            exchange=exchange,
            underlying=underlying,
            instrument_type=instrument_type,
            expiry=expiry,
            option_type=option_type,
        )
        return self._response(
            operation="fetch_derivative_strikes",
            payload=strikes,
            exchange=exchange.upper(),
            underlying=underlying.upper(),
            instrument_type=instrument_type.upper(),
            expiry=expiry,
            option_type=option_type.upper() if option_type else None,
            strike_count=len(strikes),
        )

    def fetch_instruments_by_exchange(
        self,
        exchange: str,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        instruments = self._get_market_data().get_instruments_by_exchange(
            exchange
        )
        return self._response(
            operation="fetch_instruments_by_exchange",
            payload=instruments,
            exchange=exchange.upper(),
            instrument_count=len(instruments),
        )

    def resolve_derivative_instruments(
        self,
        requests: tuple[DerivativeInstrumentRequest, ...],
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        if not requests:
            raise AngelOneSmartApiRestBrokerError(
                "Angel One derivative resolution requires requests"
            )

        market_data = self._get_market_data()
        resolved_instruments = []

        for request in requests:
            try:
                instrument = market_data.resolve_derivative_instrument(request)
            except LookupError as exc:
                raise AngelOneSmartApiRestBrokerError(
                    "Angel One derivative instrument lookup failed",
                    {
                        "exchange": request.exchange,
                        "underlying": request.underlying,
                        "instrument_type": request.instrument_type,
                        "expiry": request.expiry,
                        "strike": request.strike,
                        "option_type": request.option_type,
                        "reason": str(exc),
                    },
                ) from exc

            resolved_instruments.append(instrument.as_dict())

        return self._response(
            operation="resolve_derivative_instruments",
            payload=resolved_instruments,
            instrument_count=len(resolved_instruments),
        )

    def healthcheck(
        self,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        del context
        self._ensure_authenticated()
        return self._response(
            operation="healthcheck",
            payload={"status": "authenticated"},
            capabilities=asdict(self.capabilities),
        )

    def terminate_session(self) -> dict | None:
        return self._session_manager.terminate()

    @broker_error_handler(
        "Angel One market data request failed",
        lambda self, payload: {"payload": payload},
    )
    def _call_market_data(self, payload: dict) -> dict:
        return self._transport.get_market_data(payload)

    @broker_error_handler("Angel One instrument master load failed")
    def _get_market_data(self) -> AngelInstrumentMaster:
        if self.market_data is None:
            self.market_data = AngelInstrumentMaster.from_url()
        return self.market_data

    def _resolve_symbol_tokens(
        self,
        symbols: tuple[str, ...],
        exchange: str,
    ) -> list[str]:
        market_data = self._get_market_data()
        tokens: list[str] = []

        for symbol in symbols:
            try:
                instrument = market_data.resolve_equity_instrument(
                    symbol,
                    exchange,
                )
            except LookupError as exc:
                raise AngelOneSmartApiRestBrokerError(
                    "Angel One instrument lookup failed",
                    {
                        "exchange": exchange,
                        "symbol": symbol,
                        "reason": str(exc),
                    },
                ) from exc
            tokens.append(instrument.token)
        return tokens

    def _ensure_authenticated(self) -> None:
        self._session_manager.ensure_authenticated()

    def _response(
        self,
        *,
        operation: str,
        payload,
        **response_meta,
    ) -> BrokerResponse:
        return BrokerResponse(
            broker_name=self.broker_name,
            operation=operation,
            payload=payload,
            response_meta=response_meta,
        )

    @staticmethod
    def _merge_bulk_quote_payloads(
        chunk_responses: list[dict],
        merged_data: list[dict],
    ) -> dict:
        if not chunk_responses:
            return {
                "status": False,
                "message": "No bulk quote responses received",
                "errorcode": "NO_DATA",
                "data": [],
            }

        first_response = chunk_responses[0]
        if not isinstance(first_response, dict):
            return {
                "status": True,
                "message": "SUCCESS",
                "errorcode": "",
                "data": merged_data,
            }

        merged_payload = dict(first_response)
        merged_payload["data"] = merged_data
        merged_payload["chunk_responses"] = len(chunk_responses)
        return merged_payload

    @staticmethod
    def _validate_bulk_quote_chunk_response(
        raw: dict,
        exchange: str,
        mode: str,
        token_chunk: tuple[str, ...],
        chunk_index: int,
    ) -> None:
        if not isinstance(raw, dict):
            raise AngelOneSmartApiRestBrokerError(
                "Angel One bulk quote request returned unexpected payload",
                {
                    "exchange": exchange,
                    "mode": mode,
                    "chunk_index": chunk_index,
                    "token_chunk": list(token_chunk),
                    "payload_type": type(raw).__name__,
                },
            )
        if raw.get("status") is False:
            raise AngelOneSmartApiRestBrokerError(
                "Angel One bulk quote request failed",
                {
                    "exchange": exchange,
                    "mode": mode,
                    "chunk_index": chunk_index,
                    "token_chunk": list(token_chunk),
                    "message": raw.get("message"),
                    "errorcode": raw.get("errorcode"),
                },
            )


__all__ = ["AngelOneSmartApiRestBroker"]
