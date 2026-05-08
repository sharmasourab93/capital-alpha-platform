from __future__ import annotations

from data_layer.abs import BrokerRequestContext, CandleRequest, QuoteRequest

from .common import listify, optional_int, require_value


def fetch_quotes(*, broker, data: dict, context: BrokerRequestContext):
    mode = data.get("mode") or "FULL"
    symbols = listify(data.get("symbols"))
    return broker.fetch_quotes(
        QuoteRequest(
            mode=mode,
            exchange=require_value(data, "exchange").upper(),
            symbols=tuple(symbols),
        ),
        context=context,
    )


def fetch_candles(*, broker, data: dict, context: BrokerRequestContext):
    exchange = require_value(data, "exchange").upper()
    symbol = require_value(data, "symbol")
    instrument_token = broker._resolve_symbol_tokens((symbol,), exchange)[0]

    return broker.fetch_candles(
        CandleRequest(
            exchange=exchange,
            interval=require_value(data, "interval"),
            from_date=require_value(data, "from"),
            to_date=require_value(data, "to"),
            symbol=symbol,
            instrument_token=instrument_token,
        ),
        context=context,
    )


def fetch_nse_listed_stocks(
    *, broker, data: dict, context: BrokerRequestContext
):
    return broker.fetch_listed_equities(
        exchange="NSE",
        offset=optional_int(data.get("offset"), default=0),
        limit=optional_int(data.get("limit"), default=100),
        context=context,
    )


def fetch_bse_listed_stocks(
    *, broker, data: dict, context: BrokerRequestContext
):
    return broker.fetch_listed_equities(
        exchange="BSE",
        offset=optional_int(data.get("offset"), default=0),
        limit=optional_int(data.get("limit"), default=100),
        context=context,
    )
