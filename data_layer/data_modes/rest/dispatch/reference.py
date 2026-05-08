from __future__ import annotations

from data_layer.abs import BrokerRequestContext, InstrumentRequest

from .common import optional_int, require_value


def fetch_instruments(*, broker, data: dict, context: BrokerRequestContext):
    market = data.get("market") or data.get("exchange")
    query = data.get("query")
    return broker.fetch_instruments(
        InstrumentRequest(
            exchange=require_value({"market": market}, "market").upper(),
            query=require_value({"query": query}, "query"),
        ),
        context=context,
    )


def fetch_exchanges(*, broker, data: dict, context: BrokerRequestContext):
    return broker.fetch_exchanges(context=context)


def fetch_instrument_types(
    *, broker, data: dict, context: BrokerRequestContext
):
    return broker.fetch_instrument_types(
        exchange=data.get("exchange"),
        context=context,
    )


def fetch_exchange_symbol_name_map(
    *, broker, data: dict, context: BrokerRequestContext
):
    return broker.fetch_exchange_symbol_name_map(
        exchange=data.get("exchange"),
        query=data.get("query"),
        offset=optional_int(data.get("offset"), default=0),
        limit=optional_int(data.get("limit"), default=100),
        context=context,
    )
