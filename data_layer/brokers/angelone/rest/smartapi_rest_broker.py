from __future__ import annotations

import os
import time
from dataclasses import asdict

import pyotp
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
        self.api_key = _required_env("ANGELONE_API_KEY")
        self.client_code = client_code or _required_env("ANGELONE_CLIENTCODE")
        self.password = password or _required_env("ANGELONE_PASSWORD")
        self.totp_secret = totp_secret or _required_env("ANGELONE_TOTP_SECRET")
        self.client = client or SmartConnect(self.api_key)
        self.session = None
        self.market_data: AngelInstrumentMaster | None = None

    @broker_error_handler("Angel One authentication failed")
    def authenticate(self) -> dict:
        totp = pyotp.TOTP(self.totp_secret).now()
        session = self.client.generateSession(
            self.client_code,
            self.password,
            totp,
        )

        if not session or "data" not in session:
            raise AngelOneSmartApiRestBrokerError(
                "Angel One authentication returned invalid session",
                {"session": session},
            )

        self.session = session
        return session

    def fetch_quotes(
        self,
        request: QuoteRequest,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        symbols = self._require_symbols(request.symbols, "quotes")
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
        tokens = self._require_tokens(instrument_tokens, "quotes_by_tokens")
        payload = {
            "mode": mode,
            "exchangeTokens": {
                exchange.upper(): list(tokens),
            },
        }

        self._ensure_authenticated()
        raw = self._call_market_data(payload)
        return BrokerResponse(
            broker_name=self.broker_name,
            operation="fetch_quotes_by_tokens",
            payload=raw,
            response_meta={
                "exchange": exchange.upper(),
                "symbols": symbols or (),
                "tokens": list(tokens),
                "mode": mode,
            },
        )

    def fetch_bulk_quotes(
        self,
        request: QuoteRequest,
        context: BrokerRequestContext | None = None,
        chunk_size: int = 50,
        pause_seconds: float = 1.05,
    ) -> BrokerResponse:
        symbols = self._require_symbols(request.symbols, "bulk_quotes")
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
        tokens = self._require_tokens(
            instrument_tokens,
            "bulk_quotes_by_tokens",
        )
        normalized_exchange = exchange.upper()
        normalized_chunk_size = self._validate_bulk_chunk_size(chunk_size)
        token_chunks = list(_chunk_sequence(tokens, normalized_chunk_size))
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

        payload = self._merge_bulk_quote_payloads(
            chunk_responses,
            merged_data,
        )

        return BrokerResponse(
            broker_name=self.broker_name,
            operation="fetch_bulk_quotes",
            payload=payload,
            response_meta={
                "exchange": normalized_exchange,
                "symbols": symbols or (),
                "tokens": list(tokens),
                "mode": mode,
                "chunk_size": normalized_chunk_size,
                "chunk_count": len(token_chunks),
                "rate_limit_pause_seconds": pause_seconds,
            },
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
        if not request.instrument_token:
            raise AngelOneSmartApiRestBrokerError(
                "Angel One candles require instrument_token"
            )

        payload = {
            "exchange": request.exchange,
            "symboltoken": request.instrument_token,
            "interval": self._map_interval(request.interval),
            "fromdate": request.from_date,
            "todate": request.to_date,
        }

        self._ensure_authenticated()
        raw = self.client.getCandleData(payload)

        return BrokerResponse(
            broker_name=self.broker_name,
            operation="fetch_candles",
            payload=raw,
            response_meta={
                "exchange": request.exchange,
                "interval": request.interval,
                "instrument_token": request.instrument_token,
                "symbol": request.symbol,
            },
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
        if not request.query:
            raise AngelOneSmartApiRestBrokerError(
                "Angel One instrument search requires query"
            )

        self._ensure_authenticated()
        raw = self.client.searchScrip(
            request.exchange,
            request.query,
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

    def fetch_exchange_symbol_name_map(
        self,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        market_data = self._get_market_data()
        exchange_map = market_data.get_symbol_name_map_by_exchange()

        return BrokerResponse(
            broker_name=self.broker_name,
            operation="fetch_exchange_symbol_name_map",
            payload=exchange_map,
            response_meta={
                "exchanges": market_data.get_exchanges(),
                "exchange_count": len(exchange_map),
            },
        )

    def fetch_exchanges(
        self,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        market_data = self._get_market_data()
        exchanges = market_data.get_exchanges()

        return BrokerResponse(
            broker_name=self.broker_name,
            operation="fetch_exchanges",
            payload=exchanges,
            response_meta={"exchange_count": len(exchanges)},
        )

    def fetch_instrument_types(
        self,
        exchange: str | None = None,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        market_data = self._get_market_data()
        instrument_types = market_data.get_instrument_types(exchange)

        return BrokerResponse(
            broker_name=self.broker_name,
            operation="fetch_instrument_types",
            payload=instrument_types,
            response_meta={
                "exchange": exchange.upper() if exchange else None,
                "instrument_type_count": len(instrument_types),
            },
        )

    def fetch_derivative_symbols(
        self,
        exchange: str | None = None,
        instrument_type: str | None = None,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        market_data = self._get_market_data()
        derivative_symbols = market_data.get_derivative_symbols(
            exchange=exchange,
            instrument_type=instrument_type,
        )

        return BrokerResponse(
            broker_name=self.broker_name,
            operation="fetch_derivative_symbols",
            payload=derivative_symbols,
            response_meta={
                "exchange": exchange.upper() if exchange else None,
                "instrument_type": (
                    instrument_type.upper() if instrument_type else None
                ),
                "exchange_count": len(derivative_symbols),
            },
        )

    def fetch_instruments_by_exchange(
        self,
        exchange: str,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        market_data = self._get_market_data()
        instruments = market_data.get_instruments_by_exchange(exchange)

        return BrokerResponse(
            broker_name=self.broker_name,
            operation="fetch_instruments_by_exchange",
            payload=instruments,
            response_meta={
                "exchange": exchange.upper(),
                "instrument_count": len(instruments),
            },
        )

    def resolve_derivative_instruments(
        self,
        requests: tuple[DerivativeInstrumentRequest, ...],
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
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

        return BrokerResponse(
            broker_name=self.broker_name,
            operation="resolve_derivative_instruments",
            payload=resolved_instruments,
            response_meta={"instrument_count": len(resolved_instruments)},
        )

    def fetch_derivative_tokens(
        self,
        requests: tuple[DerivativeInstrumentRequest, ...],
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        resolved_response = self.resolve_derivative_instruments(
            requests, context
        )
        tokens_by_exchange: dict[str, list[str]] = {}

        for instrument in resolved_response.payload:
            exchange_bucket = tokens_by_exchange.setdefault(
                instrument["exchange"], []
            )
            exchange_bucket.append(instrument["token"])

        return BrokerResponse(
            broker_name=self.broker_name,
            operation="fetch_derivative_tokens",
            payload=tokens_by_exchange,
            response_meta={
                "exchange_count": len(tokens_by_exchange),
                "instrument_count": len(resolved_response.payload),
            },
        )

    def healthcheck(
        self,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        if self.session is None:
            self.authenticate()

        return BrokerResponse(
            broker_name=self.broker_name,
            operation="healthcheck",
            payload={"status": "authenticated"},
            response_meta={"capabilities": asdict(self.capabilities)},
        )

    def terminate_session(self) -> dict | None:
        try:
            return self.client.terminateSession(self.client_code)
        except Exception:  # noqa: BLE001
            return None

    @broker_error_handler(
        "Angel One market data request failed",
        lambda self, payload: {"payload": payload},
    )
    def _call_market_data(self, payload: dict) -> dict:
        return self.client.getMarketData(**payload)

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
                    symbol, exchange
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
        if self.session is None:
            self.authenticate()

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

    @staticmethod
    def _validate_bulk_chunk_size(chunk_size: int) -> int:
        if chunk_size <= 0:
            raise AngelOneSmartApiRestBrokerError(
                "Angel One bulk quotes chunk_size must be positive"
            )
        if chunk_size > 50:
            raise AngelOneSmartApiRestBrokerError(
                "Angel One bulk quotes chunk_size cannot exceed 50",
                {"chunk_size": chunk_size},
            )
        return chunk_size

    @staticmethod
    def _require_symbols(
        symbols: tuple[str, ...],
        operation: str,
    ) -> tuple[str, ...]:
        if not symbols:
            raise AngelOneSmartApiRestBrokerError(
                "Angel One {0} requires symbols".format(operation)
            )
        return symbols

    @staticmethod
    def _require_tokens(
        tokens: tuple[str, ...],
        operation: str,
    ) -> tuple[str, ...]:
        if not tokens:
            raise AngelOneSmartApiRestBrokerError(
                "Angel One {0} requires instrument_tokens".format(operation)
            )
        return tuple(str(token) for token in tokens)

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
            raise AngelOneSmartApiRestBrokerError(
                "Unsupported Angel One interval: {0}".format(interval)
            ) from exc


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError("{0} is not set".format(name))
    return value


def _chunk_sequence(
    values: tuple[str, ...],
    chunk_size: int,
):
    for index in range(0, len(values), chunk_size):
        yield values[index : index + chunk_size]
