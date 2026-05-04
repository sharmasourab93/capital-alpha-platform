from __future__ import annotations

from typing import Any

from data_layer.abs import BrokerResponse

from ..models import (
    CanonicalCandle,
    CanonicalDerivativeExpiry,
    CanonicalDerivativeUnderlying,
    CanonicalInstrument,
    CanonicalQuote,
)
from ..symbols import canonicalize_symbol

_QUOTE_SYMBOL_KEYS = ("tradingSymbol", "tradingsymbol", "symbol")
_QUOTE_TOKEN_KEYS = ("symbolToken", "symboltoken")
_INSTRUMENT_SYMBOL_KEYS = ("symbol", "tradingsymbol", "tradingSymbol")
_INSTRUMENT_TOKEN_KEYS = ("token", "symboltoken", "symbolToken")
_INSTRUMENT_NAME_KEYS = ("name", "symbolname", "underlying")
_INSTRUMENT_TYPE_KEYS = ("instrument_type", "instrumenttype")
_INSTRUMENT_EXCHANGE_KEYS = ("exchange", "exch_seg")
_INSTRUMENT_LOT_SIZE_KEYS = ("lot_size", "lotsize")
_INSTRUMENT_EXCHANGE_SEGMENT_KEYS = ("exchange_segment", "exch_seg")
_DIRECT_INSTRUMENT_OPERATIONS = frozenset(
    {
        "fetch_instruments_by_exchange",
        "fetch_derivative_contracts",
        "resolve_derivative_instruments",
    }
)


def normalize_quotes(response: BrokerResponse) -> list[CanonicalQuote]:
    """Normalize Angel One quote payloads into canonical quote rows."""

    quotes: list[CanonicalQuote] = []
    fallback_exchange = _upper_string(response.response_meta.get("exchange"))

    for row in _payload_rows(response.payload):
        quote = _normalize_quote_row(
            row,
            provider=response.broker_name,
            fallback_exchange=fallback_exchange,
        )
        if quote is not None:
            quotes.append(quote)

    return quotes


def normalize_candles(response: BrokerResponse) -> list[CanonicalCandle]:
    """Normalize Angel One candle payloads into canonical candle rows."""

    candles: list[CanonicalCandle] = []
    exchange = _upper_string(response.response_meta.get("exchange"))
    interval = _string_or_none(response.response_meta.get("interval")) or ""
    symbol = canonicalize_symbol(response.response_meta.get("symbol"))

    for row in _payload_candle_rows(response.payload):
        candle = _normalize_candle_row(
            row,
            provider=response.broker_name,
            exchange=exchange,
            interval=interval,
            symbol=symbol,
        )
        if candle is not None:
            candles.append(candle)

    return candles


def normalize_instruments(
    response: BrokerResponse,
) -> list[CanonicalInstrument]:
    """Normalize Angel One search, master, and derivative-contract rows."""

    instruments: list[CanonicalInstrument] = []

    for row in _instrument_rows(response):
        instrument = _normalize_instrument_row(
            row,
            provider=response.broker_name,
        )
        if instrument is not None:
            instruments.append(instrument)

    return instruments


def normalize_derivative_underlyings(
    response: BrokerResponse,
) -> list[CanonicalDerivativeUnderlying]:
    """Flatten grouped Angel One derivative underlyings into canonical rows."""

    payload = response.payload if isinstance(response.payload, dict) else {}
    underlyings: list[CanonicalDerivativeUnderlying] = []

    for exchange, instrument_type_map in payload.items():
        if not isinstance(instrument_type_map, dict):
            continue

        normalized_exchange = _upper_string(exchange)
        for instrument_type, values in instrument_type_map.items():
            if not isinstance(values, list):
                continue

            normalized_instrument_type = _upper_string(instrument_type)
            for underlying in values:
                normalized_underlying = _upper_string(underlying)
                if not normalized_underlying:
                    continue

                underlyings.append(
                    CanonicalDerivativeUnderlying(
                        provider=response.broker_name,
                        exchange=normalized_exchange,
                        instrument_type=normalized_instrument_type,
                        underlying=normalized_underlying,
                        raw={
                            "exchange": normalized_exchange,
                            "instrument_type": normalized_instrument_type,
                            "underlying": normalized_underlying,
                        },
                    )
                )

    return underlyings


def normalize_derivative_expiries(
    response: BrokerResponse,
) -> list[CanonicalDerivativeExpiry]:
    """Expand Angel One expiry lists into canonical expiry rows."""

    if not isinstance(response.payload, (list, tuple)):
        return []

    exchange = _upper_string(response.response_meta.get("exchange"))
    underlying = _upper_string(response.response_meta.get("underlying"))
    instrument_type = _upper_string(
        response.response_meta.get("instrument_type")
    )
    expiries: list[CanonicalDerivativeExpiry] = []

    for value in response.payload:
        expiry = _string_or_none(value)
        if expiry is None:
            continue

        expiries.append(
            CanonicalDerivativeExpiry(
                provider=response.broker_name,
                exchange=exchange,
                instrument_type=instrument_type,
                underlying=underlying,
                expiry=expiry,
                raw={
                    "exchange": exchange,
                    "instrument_type": instrument_type,
                    "underlying": underlying,
                    "expiry": expiry,
                },
            )
        )

    return expiries


def _normalize_quote_row(
    row: dict[str, Any],
    *,
    provider: str,
    fallback_exchange: str,
) -> CanonicalQuote | None:
    """Convert one Angel One quote row, skipping rows without a valid LTP."""

    broker_symbol = _string_or_none(_first_present(row, *_QUOTE_SYMBOL_KEYS))
    if broker_symbol is None:
        return None

    ltp = _float_or_none(row.get("ltp"))
    if ltp is None:
        return None

    exchange = _upper_string(
        _first_present(row, "exchange") or fallback_exchange
    )
    return CanonicalQuote(
        provider=provider,
        exchange=exchange,
        symbol=canonicalize_symbol(broker_symbol),
        broker_symbol=broker_symbol.upper(),
        token=_string_or_none(_first_present(row, *_QUOTE_TOKEN_KEYS)),
        ltp=ltp,
        open=_float_or_none(_first_present(row, "open")),
        high=_float_or_none(_first_present(row, "high")),
        low=_float_or_none(_first_present(row, "low")),
        close=_float_or_none(_first_present(row, "close")),
        volume=_int_or_none(_first_present(row, "tradeVolume", "volume")),
        as_of=_string_or_none(
            _first_present(row, "exchFeedTime", "exchTradeTime")
        ),
        raw=dict(row),
    )


def _normalize_candle_row(
    row: list[Any],
    *,
    provider: str,
    exchange: str,
    interval: str,
    symbol: str,
) -> CanonicalCandle | None:
    """Convert one Angel One candle row, skipping malformed OHLC rows."""

    if len(row) < 5:
        return None

    timestamp = _string_or_none(row[0])
    open_price = _float_or_none(row[1])
    high_price = _float_or_none(row[2])
    low_price = _float_or_none(row[3])
    close_price = _float_or_none(row[4])
    if None in (timestamp, open_price, high_price, low_price, close_price):
        return None

    volume = _int_or_none(row[5]) if len(row) > 5 else None
    return CanonicalCandle(
        provider=provider,
        exchange=exchange,
        symbol=symbol,
        interval=interval,
        timestamp=timestamp,
        open=open_price,
        high=high_price,
        low=low_price,
        close=close_price,
        volume=volume,
        raw=list(row),
    )


def _normalize_instrument_row(
    row: dict[str, Any],
    *,
    provider: str,
) -> CanonicalInstrument | None:
    """Convert one Angel One instrument-like row into the shared contract."""

    broker_symbol = _string_or_none(
        _first_present(row, *_INSTRUMENT_SYMBOL_KEYS)
    )
    if broker_symbol is None:
        return None

    instrument_type = _string_or_none(
        _first_present(row, *_INSTRUMENT_TYPE_KEYS)
    )
    return CanonicalInstrument(
        provider=provider,
        exchange=_upper_string(
            _first_present(row, *_INSTRUMENT_EXCHANGE_KEYS)
        ),
        symbol=canonicalize_symbol(
            broker_symbol,
            instrument_type=instrument_type,
        ),
        broker_symbol=broker_symbol.upper(),
        token=_string_or_none(_first_present(row, *_INSTRUMENT_TOKEN_KEYS)),
        name=_string_or_none(_first_present(row, *_INSTRUMENT_NAME_KEYS))
        or "",
        instrument_type=instrument_type,
        underlying=_string_or_none(_first_present(row, "underlying", "name")),
        expiry=_string_or_none(_first_present(row, "expiry")),
        strike=_float_or_none(_first_present(row, "strike")),
        option_type=_string_or_none(_first_present(row, "option_type")),
        lot_size=_int_or_none(_first_present(row, *_INSTRUMENT_LOT_SIZE_KEYS)),
        exchange_segment=_string_or_none(
            _first_present(row, *_INSTRUMENT_EXCHANGE_SEGMENT_KEYS)
        ),
        raw=dict(row),
    )


def _payload_rows(payload: Any) -> list[dict[str, Any]]:
    """Extract dict rows from a broker payload that stores records in `data`."""

    if not isinstance(payload, dict):
        return []

    rows = payload.get("data")
    if not isinstance(rows, list):
        return []

    return [row for row in rows if isinstance(row, dict)]


def _payload_candle_rows(payload: Any) -> list[list[Any]]:
    """Extract candle rows from a broker payload that stores bars in `data`."""

    if not isinstance(payload, dict):
        return []

    rows = payload.get("data")
    if not isinstance(rows, list):
        return []

    return [row for row in rows if isinstance(row, list)]


def _instrument_rows(response: BrokerResponse) -> list[dict[str, Any]]:
    """Return instrument rows from either list payloads or nested `data` payloads."""

    if response.operation in _DIRECT_INSTRUMENT_OPERATIONS and isinstance(
        response.payload, list
    ):
        return [row for row in response.payload if isinstance(row, dict)]

    return _payload_rows(response.payload)


def _first_present(data: dict[str, Any], *keys: str) -> Any:
    """Return the first non-empty value among the provided keys."""

    for key in keys:
        value = data.get(key)
        if value not in ("", None):
            return value
    return None


def _string_or_none(value: Any) -> str | None:
    """Coerce a non-empty value to string, otherwise return `None`."""

    if value in ("", None):
        return None
    return str(value)


def _upper_string(value: Any) -> str:
    """Return an uppercased string value, defaulting missing inputs to `\"\"`."""

    return (_string_or_none(value) or "").upper()


def _float_or_none(value: Any) -> float | None:
    """Parse a float value, returning `None` for missing or invalid inputs."""

    if value in ("", None):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    """Parse an integer-like value, returning `None` on invalid inputs."""

    if value in ("", None):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
