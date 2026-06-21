"""Market-data REST routes."""

from __future__ import annotations

from typing import Any

from data_layer.brokers import get_available_rest_brokers
from data_layer.brokers.canonical.errors import BrokerValidationError
from data_layer.brokers.canonical.models import (
    CandleRequest,
    LtpRequest,
    QuoteRequest,
    ScripListRequest,
)
from data_layer.brokers.canonical.service import BrokerRestService
from data_layer.runtimes.rest.dependencies import get_broker_rest_service
from data_layer.runtimes.rest.errors import call_or_raise
from data_layer.runtimes.rest.responses import response_body
from data_layer.runtimes.rest.schemas import (
    MAX_MARKET_SYMBOLS,
    CandlePayload,
    QuotePayload,
)
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/market", tags=["market"])

ANGELONE_INTERVALS = [
    {"label": "1m", "value": "ONE_MINUTE"},
    {"label": "3m", "value": "THREE_MINUTE"},
    {"label": "5m", "value": "FIVE_MINUTE"},
    {"label": "10m", "value": "TEN_MINUTE"},
    {"label": "15m", "value": "FIFTEEN_MINUTE"},
    {"label": "30m", "value": "THIRTY_MINUTE"},
    {"label": "1h", "value": "ONE_HOUR"},
    {"label": "1D", "value": "ONE_DAY"},
]


@router.get("/brokers")
def list_brokers() -> dict[str, list[str]]:
    """Return registered market brokers."""
    return {"brokers": get_available_rest_brokers()}


@router.get("/{broker}/{exchange}/intervals")
def get_intervals(broker: str, exchange: str) -> dict[str, Any]:
    """Return candle intervals supported by a broker."""
    intervals = ANGELONE_INTERVALS if broker.lower() == "angelone" else []
    return {
        "broker": broker,
        "exchange": exchange.upper(),
        "intervals": intervals,
    }


@router.get("/{broker}/{exchange}/scrips")
def get_all_scrips(
    broker: str,
    exchange: str,
    service: BrokerRestService = Depends(get_broker_rest_service),
) -> dict[str, Any]:
    """Return all known scrips for a broker exchange."""
    return call_or_raise(
        lambda: response_body(
            service.get_all_scrips(
                ScripListRequest(broker=broker, exchange=exchange)
            )
        )
    )


@router.get("/{broker}/{exchange}/ltp")
def get_ltp(
    broker: str,
    exchange: str,
    symbol: str,
    service: BrokerRestService = Depends(get_broker_rest_service),
) -> dict[str, Any]:
    """Return LTP for one or more comma-separated symbols."""
    symbols = call_or_raise(lambda: _parse_symbols(symbol))
    if len(symbols) == 1:
        return call_or_raise(
            lambda: response_body(
                service.get_ltp(
                    LtpRequest(
                        broker=broker,
                        exchange=exchange,
                        symbol=symbols[0],
                    )
                )
            )
        )
    return call_or_raise(
        lambda: response_body(
            service.get_quote(
                QuoteRequest(
                    broker=broker,
                    exchange=exchange,
                    symbols=symbols,
                    mode="LTP",
                )
            )
        )
    )


@router.post("/{broker}/{exchange}/quotes")
def get_quote(
    broker: str,
    exchange: str,
    payload: QuotePayload,
    service: BrokerRestService = Depends(get_broker_rest_service),
) -> dict[str, Any]:
    """Return quote data."""
    return call_or_raise(
        lambda: response_body(
            service.get_quote(
                QuoteRequest(
                    broker=broker,
                    exchange=exchange,
                    symbols=payload.symbols,
                    mode=payload.mode,
                )
            )
        )
    )


@router.post("/{broker}/{exchange}/candles")
def get_candles(
    broker: str,
    exchange: str,
    payload: CandlePayload,
    service: BrokerRestService = Depends(get_broker_rest_service),
) -> dict[str, Any]:
    """Return historical candle data."""
    return call_or_raise(
        lambda: response_body(
            service.get_candles(
                CandleRequest(
                    broker=broker,
                    exchange=exchange,
                    symbol=payload.symbol,
                    interval=payload.interval,
                    from_time=payload.from_time,
                    to_time=payload.to_time,
                )
            )
        )
    )


def _parse_symbols(symbols: str) -> list[str]:
    """Parse comma-separated query symbols."""
    parsed_symbols = [
        symbol.strip() for symbol in symbols.split(",") if symbol.strip()
    ]
    if len(parsed_symbols) > MAX_MARKET_SYMBOLS:
        raise BrokerValidationError(
            "Too many symbols requested",
            {
                "field": "symbol",
                "max_symbols": MAX_MARKET_SYMBOLS,
                "actual_symbols": len(parsed_symbols),
            },
        )
    return parsed_symbols
