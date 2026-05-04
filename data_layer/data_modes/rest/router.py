from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(PROJECT_ROOT))

from data_layer.abs import (
    BrokerRequestContext,
    BrokerResponse,
    CandleRequest,
    DerivativeInstrumentRequest,
    InstrumentRequest,
    QuoteRequest,
)


class RestRouter:
    def __init__(self) -> None:
        self._brokers = {
            "angelone": "angelone",
            "zerodha": None,
        }
        self._broker_instances: dict[str, object] = {}
        self._route_handlers: dict[
            str, dict[str, Callable[..., BrokerResponse | dict]]
        ] = {
            "/health": {"GET": self._health},
            "/market/instruments": {"GET": self._instruments},
            "/market/exchanges": {"GET": self._exchanges},
            "/market/instrument-types": {"GET": self._instrument_types},
            "/market/instruments-by-exchange": {
                "GET": self._instruments_by_exchange
            },
            "/market/exchange-symbol-name-map": {
                "GET": self._exchange_symbol_name_map
            },
            "/market/derivative-symbols": {"GET": self._derivative_symbols},
            "/market/derivative-underlyings": {
                "GET": self._derivative_underlyings
            },
            "/market/derivative-expiries": {"GET": self._derivative_expiries},
            "/market/derivative-strikes": {"GET": self._derivative_strikes},
            "/market/derivative-contracts": {"GET": self._derivative_contracts},
            "/market/quotes": {"POST": self._quotes},
            "/market/candles": {"POST": self._candles},
            "/market/derivatives/history": {"POST": self._derivative_history},
            "/market/derivatives/resolve": {"POST": self._resolve_derivative},
        }

    def handle(
        self,
        path: str,
        method: str,
        query: dict[str, str],
        body: dict,
        request_id: str,
    ) -> tuple[int, dict]:
        route_methods = self._route_handlers.get(path)
        if route_methods is None:
            return 404, self._error(
                error_type="NOT_FOUND",
                message="Route not found",
            )

        handler = route_methods.get(method)
        if handler is None:
            return 405, self._error(
                error_type="METHOD_NOT_ALLOWED",
                message="Method {0} is not supported for {1}".format(
                    method, path
                ),
            )

        if path == "/health":
            return 200, {"data": handler()}

        source = body if method == "POST" else query
        broker_name = self._require(source, "provider").lower()
        broker = self._resolve_broker(broker_name)
        context = BrokerRequestContext(request_id=request_id)
        started_at = perf_counter()
        response = handler(
            broker=broker,
            data=source,
            context=context,
        )
        elapsed_ms = (perf_counter() - started_at) * 1000
        response.response_meta["router_elapsed_ms"] = round(elapsed_ms, 3)
        return 200, self._ok(response)

    def _health(self) -> dict:
        return {"status": "ok", "mode": "rest"}

    def _quotes(self, *, broker, data: dict, context: BrokerRequestContext):
        mode = data.get("mode") or "FULL"
        symbols = self._listify(data.get("symbols"))
        return broker.fetch_quotes(
            QuoteRequest(
                mode=mode,
                exchange=self._require(data, "exchange").upper(),
                symbols=tuple(symbols),
            ),
            context=context,
        )

    def _candles(self, *, broker, data: dict, context: BrokerRequestContext):
        exchange = self._require(data, "exchange").upper()
        symbol = self._require(data, "symbol")
        instrument_token = broker._resolve_symbol_tokens((symbol,), exchange)[
            0
        ]

        return broker.fetch_candles(
            CandleRequest(
                exchange=exchange,
                interval=self._require(data, "interval"),
                from_date=self._require(data, "from"),
                to_date=self._require(data, "to"),
                symbol=symbol,
                instrument_token=instrument_token,
            ),
            context=context,
        )

    def _instruments(
        self, *, broker, data: dict, context: BrokerRequestContext
    ):
        market = data.get("market") or data.get("exchange")
        query = data.get("query")
        return broker.fetch_instruments(
            InstrumentRequest(
                exchange=self._require({"market": market}, "market").upper(),
                query=self._require({"query": query}, "query"),
            ),
            context=context,
        )

    def _exchanges(self, *, broker, data: dict, context: BrokerRequestContext):
        return broker.fetch_exchanges(context=context)

    def _instrument_types(
        self,
        *,
        broker,
        data: dict,
        context: BrokerRequestContext,
    ):
        return broker.fetch_instrument_types(
            exchange=data.get("exchange"),
            context=context,
        )

    def _instruments_by_exchange(
        self,
        *,
        broker,
        data: dict,
        context: BrokerRequestContext,
    ):
        return broker.fetch_instruments_by_exchange(
            exchange=self._require(data, "exchange").upper(),
            context=context,
        )

    def _exchange_symbol_name_map(
        self,
        *,
        broker,
        data: dict,
        context: BrokerRequestContext,
    ):
        return broker.fetch_exchange_symbol_name_map(
            exchange=data.get("exchange"),
            query=data.get("query"),
            offset=self._optional_int(data.get("offset"), default=0),
            limit=self._optional_int(data.get("limit"), default=100),
            context=context,
        )

    def _derivative_symbols(
        self,
        *,
        broker,
        data: dict,
        context: BrokerRequestContext,
    ):
        return broker.fetch_derivative_symbols(
            exchange=data.get("exchange"),
            instrument_type=data.get("instrument_type"),
            context=context,
        )

    def _derivative_expiries(
        self,
        *,
        broker,
        data: dict,
        context: BrokerRequestContext,
    ):
        return broker.fetch_derivative_expiries(
            exchange=self._require(data, "exchange").upper(),
            underlying=self._require(data, "underlying"),
            instrument_type=self._require(data, "instrument_type"),
            context=context,
        )

    def _derivative_contracts(
        self,
        *,
        broker,
        data: dict,
        context: BrokerRequestContext,
    ):
        return broker.fetch_derivative_contracts(
            exchange=self._require(data, "exchange").upper(),
            underlying=self._require(data, "underlying"),
            instrument_type=self._require(data, "instrument_type"),
            expiry=self._require(data, "expiry"),
            option_type=data.get("option_type"),
            context=context,
        )

    def _derivative_strikes(
        self,
        *,
        broker,
        data: dict,
        context: BrokerRequestContext,
    ):
        return broker.fetch_derivative_strikes(
            exchange=self._require(data, "exchange").upper(),
            underlying=self._require(data, "underlying"),
            instrument_type=self._require(data, "instrument_type"),
            expiry=self._require(data, "expiry"),
            option_type=data.get("option_type"),
            context=context,
        )

    def _derivative_underlyings(
        self,
        *,
        broker,
        data: dict,
        context: BrokerRequestContext,
    ):
        return broker.fetch_derivative_underlyings(
            exchange=data.get("exchange"),
            instrument_type=data.get("instrument_type"),
            context=context,
        )

    def _derivative_history(
        self,
        *,
        broker,
        data: dict,
        context: BrokerRequestContext,
    ):
        derivative_request = self._derivative_request(data)
        resolved_response = broker.resolve_derivative_instruments(
            requests=(derivative_request,),
            context=context,
        )
        instrument = resolved_response.payload[0]

        return broker.fetch_candles(
            CandleRequest(
                exchange=self._require(data, "exchange").upper(),
                interval=self._require(data, "interval"),
                from_date=self._require(data, "from"),
                to_date=self._require(data, "to"),
                symbol=str(instrument["symbol"]),
                instrument_token=str(instrument["token"]),
            ),
            context=context,
        )

    def _resolve_derivative(
        self,
        *,
        broker,
        data: dict,
        context: BrokerRequestContext,
    ):
        requests = self._derivative_requests(data)
        return broker.resolve_derivative_instruments(
            requests=requests,
            context=context,
        )

    def _derivative_requests(
        self, data: dict
    ) -> tuple[DerivativeInstrumentRequest, ...]:
        request_items = data.get("requests")
        if request_items:
            return tuple(
                self._derivative_request(item) for item in request_items
            )
        return (self._derivative_request(data),)

    def _derivative_request(self, data: dict) -> DerivativeInstrumentRequest:
        return DerivativeInstrumentRequest(
            exchange=self._require(data, "exchange").upper(),
            underlying=self._require(data, "underlying"),
            instrument_type=self._require(data, "instrument_type"),
            expiry=self._require(data, "expiry"),
            strike=self._optional_float(data.get("strike")),
            option_type=data.get("option_type"),
        )

    def _resolve_broker(self, name: str):
        cached_broker = self._broker_instances.get(name)
        if cached_broker is not None:
            return cached_broker

        broker_ref = self._brokers.get(name)
        if broker_ref is None:
            if name == "zerodha":
                raise NotImplementedError(
                    "Zerodha REST broker is not implemented yet"
                )
            raise ValueError("Unsupported provider: {0}".format(name))

        if broker_ref == "angelone":
            from data_layer.brokers.angelone.rest import (
                AngelOneSmartApiRestBroker,
            )

            broker = AngelOneSmartApiRestBroker()
            self._broker_instances[name] = broker
            return broker

        broker = broker_ref()
        self._broker_instances[name] = broker
        return broker

    @staticmethod
    def _ok(response: BrokerResponse) -> dict:
        response_meta = dict(response.response_meta)
        response_meta.pop("tokens", None)
        response_meta.pop("instrument_token", None)
        response_meta.pop("instrument_tokens", None)

        return {
            "data": response.payload,
            "meta": {
                "broker": response.broker_name,
                "operation": response.operation,
                "response_meta": response_meta,
            },
        }

    @staticmethod
    def _error(
        error_type: str, message: str, details: list | None = None
    ) -> dict:
        return {
            "error": {
                "type": error_type,
                "message": message,
                "details": details or [],
            }
        }

    @staticmethod
    def _require(data: dict, key: str) -> str:
        value = data.get(key)
        if value is None:
            raise ValueError("{0} is required".format(key))
        if isinstance(value, str):
            value = value.strip()
        if value == "":
            raise ValueError("{0} is required".format(key))
        return value

    @staticmethod
    def _listify(value) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return [str(value).strip()]

    @staticmethod
    def _optional_float(value) -> float | None:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return float(value)

    @staticmethod
    def _optional_int(value, *, default: int) -> int:
        if value is None:
            return default
        if isinstance(value, str) and not value.strip():
            return default
        return int(value)
