from __future__ import annotations

from datetime import datetime
import re

from .classification import classify_instrument
from .models import AngelInstrument

_DERIVATIVE_STRIKE_PATTERN = re.compile(r"\d{2}[A-Z]{3}\d{4}(\d+)(CE|PE)$")
_DERIVATIVE_UNDERLYING_PATTERN = re.compile(r"^(.*?)(\d{2}[A-Z]{3}\d{4})")


def parse_instrument_rows(rows: list[dict]) -> list[AngelInstrument]:
    instruments: list[AngelInstrument] = []
    for row in rows:
        instrument = try_parse_instrument_row(row)
        if instrument is not None:
            instruments.append(instrument)
    return instruments


def try_parse_instrument_row(row: dict) -> AngelInstrument | None:
    token = row.get("token")
    symbol = row.get("symbol")
    exchange = row.get("exch_seg")
    if token in ("", None) or symbol in ("", None) or exchange in ("", None):
        return None

    try:
        return parse_instrument_row(row)
    except (TypeError, ValueError, KeyError):
        return None


def parse_instrument_row(row: dict) -> AngelInstrument:
    symbol = (row.get("symbol") or "").upper()
    exchange = (row.get("exch_seg") or "").upper()
    instrument_type = (row.get("instrumenttype") or "").upper()
    option_type = extract_option_type(symbol)
    classification = classify_instrument(
        exchange=exchange,
        symbol=symbol,
        name=row.get("name") or "",
        instrument_type=instrument_type,
    )

    return AngelInstrument(
        token=str(row["token"]),
        symbol=symbol,
        name=row.get("name") or "",
        underlying=normalize_underlying(
            row.get("name") or "",
            symbol=symbol,
            instrument_type=instrument_type,
        ),
        exchange=exchange,
        exchange_segment=exchange,
        instrument_type=instrument_type,
        expiry=row.get("expiry") or None,
        strike=parse_strike(
            row.get("strike"),
            symbol=symbol,
            instrument_type=instrument_type,
            option_type=option_type,
        ),
        lot_size=parse_lot_size(row.get("lotsize")),
        tick_size=parse_tick_size(row.get("tick_size")),
        option_type=option_type,
        classification=classification,
    )


def extract_option_type(symbol: str) -> str | None:
    if symbol.endswith("CE"):
        return "CE"
    if symbol.endswith("PE"):
        return "PE"
    return None


def parse_strike(
    value,
    *,
    symbol: str,
    instrument_type: str,
    option_type: str | None,
) -> float | None:
    symbol_strike = extract_strike_from_symbol(
        symbol,
        instrument_type=instrument_type,
        option_type=option_type,
    )
    if symbol_strike is not None:
        return symbol_strike

    if value in ("", None):
        return None

    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    if parsed >= 100000:
        return parsed / 100.0
    return parsed


def parse_lot_size(value) -> int | None:
    if value in ("", None):
        return None
    return int(value)


def parse_tick_size(value) -> float | None:
    if value in ("", None):
        return None

    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def extract_strike_from_symbol(
    symbol: str,
    *,
    instrument_type: str,
    option_type: str | None,
) -> float | None:
    if option_type is None or "OPT" not in instrument_type:
        return None

    match = _DERIVATIVE_STRIKE_PATTERN.search(symbol)
    if match is None:
        return None

    return float(match.group(1))


def normalize_underlying(
    value: str,
    *,
    symbol: str,
    instrument_type: str,
) -> str:
    normalized_value = normalize_underlying_text(value)
    if normalized_value:
        return normalized_value

    inferred_underlying = infer_underlying_from_symbol(
        symbol,
        instrument_type=instrument_type,
    )
    if inferred_underlying:
        return inferred_underlying

    return normalize_underlying_text(symbol)


def normalize_underlying_text(value: str) -> str:
    return " ".join(str(value).upper().split())


def infer_underlying_from_symbol(
    symbol: str,
    *,
    instrument_type: str,
) -> str:
    if "FUT" not in instrument_type and "OPT" not in instrument_type:
        return ""

    match = _DERIVATIVE_UNDERLYING_PATTERN.search(symbol)
    if match is None:
        return ""

    return match.group(1).upper().strip()


def expiry_sort_key(expiry: str) -> tuple[int, datetime | str]:
    try:
        return (0, datetime.strptime(expiry.upper(), "%d%b%Y"))
    except ValueError:
        return (1, expiry)


__all__ = [
    "expiry_sort_key",
    "extract_option_type",
    "normalize_underlying",
    "parse_instrument_row",
    "parse_instrument_rows",
    "try_parse_instrument_row",
]
