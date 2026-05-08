from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:  # pragma: no cover
    sys.path.insert(0, str(PROJECT_ROOT))

from data_layer.abs import BrokerRequestContext, BrokerResponse
from data_layer.data_modes.rest import dispatch
from data_layer.data_modes.rest.contracts import paths
from data_layer.data_modes.rest.dispatch.common import require_value


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
            paths.HEALTH: {"GET": self._health},
            paths.REFERENCE_INSTRUMENTS: {"GET": dispatch.fetch_instruments},
            paths.REFERENCE_EXCHANGES: {"GET": dispatch.fetch_exchanges},
            paths.REFERENCE_INSTRUMENT_TYPES: {
                "GET": dispatch.fetch_instrument_types
            },
            paths.REFERENCE_EXCHANGE_SYMBOL_NAME_MAP: {
                "GET": dispatch.fetch_exchange_symbol_name_map
            },
            paths.CASH_NSE_LISTED_STOCKS: {
                "GET": dispatch.fetch_nse_listed_stocks
            },
            paths.CASH_BSE_LISTED_STOCKS: {
                "GET": dispatch.fetch_bse_listed_stocks
            },
            paths.DERIVATIVES_SYMBOLS: {
                "GET": dispatch.fetch_derivative_symbols
            },
            paths.DERIVATIVES_UNDERLYINGS: {
                "GET": dispatch.fetch_derivative_underlyings
            },
            paths.DERIVATIVES_EXPIRIES: {
                "GET": dispatch.fetch_derivative_expiries
            },
            paths.DERIVATIVES_STRIKES: {
                "GET": dispatch.fetch_derivative_strikes
            },
            paths.DERIVATIVES_CONTRACTS: {
                "GET": dispatch.fetch_derivative_contracts
            },
            paths.CASH_QUOTES: {"POST": dispatch.fetch_quotes},
            paths.CASH_CANDLES: {"POST": dispatch.fetch_candles},
            paths.DERIVATIVES_HISTORY: {
                "POST": dispatch.fetch_derivative_history
            },
            paths.DERIVATIVES_RESOLVE: {
                "POST": dispatch.resolve_derivative_instruments
            },
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

        if path == paths.HEALTH:
            return 200, {"data": handler()}

        source = body if method == "POST" else query
        broker_name = require_value(source, "provider").lower()
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
