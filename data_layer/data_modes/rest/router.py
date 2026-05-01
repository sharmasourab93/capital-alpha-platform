from __future__ import annotations

from data_layer.abs.broker_abs import (
    BrokerRequestContext,
    CandleRequest,
    InstrumentRequest,
    QuoteRequest,
)
from data_layer.brokers.angelone import AngelOneRestBroker


class RestRouter:
    def __init__(self) -> None:
        self._brokers = {
            "angelone": AngelOneRestBroker,
            "zerodha": None,
        }

    def handle(
        self, path: str, method: str, query: dict[str, str], request_id: str
    ) -> tuple[int, dict]:
        if method != "GET":
            return 405, {
                "error": {
                    "type": "METHOD_NOT_ALLOWED",
                    "message": "Only GET is supported",
                    "details": [],
                }
            }

        if path == "/health":
            return 200, {"data": {"status": "ok", "mode": "rest"}}

        broker_name = self._require(query, "provider").lower()
        broker = self._resolve_broker(broker_name)
        context = BrokerRequestContext(request_id=request_id)

        if path == "/market/quotes":
            response = broker.fetch_quotes(
                QuoteRequest(
                    exchange=self._require(query, "exchange").upper(),
                    symbols=tuple(self._csv(query.get("symbols"))),
                    instrument_tokens=tuple(
                        self._csv(query.get("instrument_tokens"))
                    ),
                ),
                context=context,
            )
            return 200, {
                "data": response.payload,
                "meta": {
                    "broker": response.broker_name,
                    "operation": response.operation,
                },
            }

        if path == "/market/candles":
            response = broker.fetch_candles(
                CandleRequest(
                    exchange=self._require(query, "exchange").upper(),
                    interval=self._require(query, "interval"),
                    from_date=self._require(query, "from"),
                    to_date=self._require(query, "to"),
                    symbol=query.get("symbol"),
                    instrument_token=query.get("instrument_token"),
                ),
                context=context,
            )
            return 200, {
                "data": response.payload,
                "meta": {
                    "broker": response.broker_name,
                    "operation": response.operation,
                },
            }

        if path == "/market/instruments":
            response = broker.fetch_instruments(
                InstrumentRequest(
                    exchange=self._require(query, "exchange").upper(),
                    segment=query.get("segment"),
                    symbol=query.get("symbol"),
                    query=query.get("query") or query.get("symbol"),
                ),
                context=context,
            )
            return 200, {
                "data": response.payload,
                "meta": {
                    "broker": response.broker_name,
                    "operation": response.operation,
                },
            }

        return 404, {
            "error": {
                "type": "NOT_FOUND",
                "message": "Route not found",
                "details": [],
            }
        }

    def _resolve_broker(self, name: str):
        broker_cls = self._brokers.get(name)
        if broker_cls is None:
            if name == "zerodha":
                raise NotImplementedError(
                    "Zerodha REST broker is not implemented yet"
                )
            raise ValueError("Unsupported provider: {0}".format(name))
        return broker_cls()

    @staticmethod
    def _require(query: dict[str, str], key: str) -> str:
        value = query.get(key)
        if not value:
            raise ValueError("{0} is required".format(key))
        return value.strip()

    @staticmethod
    def _csv(value: str | None) -> list[str]:
        if not value:
            return []
        return [item.strip() for item in value.split(",") if item.strip()]
