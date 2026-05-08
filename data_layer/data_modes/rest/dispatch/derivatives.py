from __future__ import annotations

from data_layer.abs import (
    BrokerRequestContext,
    CandleRequest,
    DerivativeInstrumentRequest,
)

from .common import optional_float, require_value


def fetch_derivative_symbols(
    *, broker, data: dict, context: BrokerRequestContext
):
    return broker.fetch_derivative_symbols(
        exchange=data.get("exchange"),
        instrument_type=data.get("instrument_type"),
        context=context,
    )


def fetch_derivative_underlyings(
    *, broker, data: dict, context: BrokerRequestContext
):
    return broker.fetch_derivative_underlyings(
        exchange=data.get("exchange"),
        instrument_type=data.get("instrument_type"),
        context=context,
    )


def fetch_derivative_expiries(
    *, broker, data: dict, context: BrokerRequestContext
):
    return broker.fetch_derivative_expiries(
        exchange=require_value(data, "exchange").upper(),
        underlying=require_value(data, "underlying"),
        instrument_type=require_value(data, "instrument_type"),
        context=context,
    )


def fetch_derivative_contracts(
    *, broker, data: dict, context: BrokerRequestContext
):
    return broker.fetch_derivative_contracts(
        exchange=require_value(data, "exchange").upper(),
        underlying=require_value(data, "underlying"),
        instrument_type=require_value(data, "instrument_type"),
        expiry=require_value(data, "expiry"),
        option_type=data.get("option_type"),
        context=context,
    )


def fetch_derivative_strikes(
    *, broker, data: dict, context: BrokerRequestContext
):
    return broker.fetch_derivative_strikes(
        exchange=require_value(data, "exchange").upper(),
        underlying=require_value(data, "underlying"),
        instrument_type=require_value(data, "instrument_type"),
        expiry=require_value(data, "expiry"),
        option_type=data.get("option_type"),
        context=context,
    )


def fetch_derivative_history(
    *, broker, data: dict, context: BrokerRequestContext
):
    derivative_request = build_derivative_request(data)
    resolved_response = broker.resolve_derivative_instruments(
        requests=(derivative_request,),
        context=context,
    )
    instrument = resolved_response.payload[0]

    return broker.fetch_candles(
        CandleRequest(
            exchange=require_value(data, "exchange").upper(),
            interval=require_value(data, "interval"),
            from_date=require_value(data, "from"),
            to_date=require_value(data, "to"),
            symbol=str(instrument["symbol"]),
            instrument_token=str(instrument["token"]),
        ),
        context=context,
    )


def resolve_derivative_instruments(
    *, broker, data: dict, context: BrokerRequestContext
):
    return broker.resolve_derivative_instruments(
        requests=build_derivative_requests(data),
        context=context,
    )


def build_derivative_requests(
    data: dict,
) -> tuple[DerivativeInstrumentRequest, ...]:
    request_items = data.get("requests")
    if request_items:
        return tuple(build_derivative_request(item) for item in request_items)
    return (build_derivative_request(data),)


def build_derivative_request(data: dict) -> DerivativeInstrumentRequest:
    return DerivativeInstrumentRequest(
        exchange=require_value(data, "exchange").upper(),
        underlying=require_value(data, "underlying"),
        instrument_type=require_value(data, "instrument_type"),
        expiry=require_value(data, "expiry"),
        strike=optional_float(data.get("strike")),
        option_type=data.get("option_type"),
    )
