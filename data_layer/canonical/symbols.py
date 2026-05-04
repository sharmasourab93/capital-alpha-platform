from __future__ import annotations

from typing import Any

_EQUITY_SUFFIXES = ("-EQ",)
_EQUITY_INSTRUMENT_TYPES = {"EQ", "EQUITY"}


def canonicalize_symbol(
    value: Any,
    *,
    instrument_type: Any = None,
) -> str:
    """
    Canonical symbol contract for the shared layer:

    - symbols are always uppercased and trimmed
    - cash equities drop broker equity suffixes such as ``-EQ``
    - derivatives and any non-equity instruments keep the full broker symbol
    """
    if value is None:
        return ""

    symbol = str(value).upper().strip()
    if not symbol:
        return ""

    normalized_instrument_type = _normalize_instrument_type(instrument_type)
    if _is_explicit_equity_symbol(symbol, normalized_instrument_type):
        for suffix in _EQUITY_SUFFIXES:
            if symbol.endswith(suffix):
                return symbol[: -len(suffix)]

    return symbol


def _normalize_instrument_type(value: Any) -> str | None:
    if value in ("", None):
        return None
    return str(value).upper().strip()


def _is_explicit_equity_symbol(
    symbol: str,
    instrument_type: str | None,
) -> bool:
    if instrument_type in _EQUITY_INSTRUMENT_TYPES:
        return True
    return any(symbol.endswith(suffix) for suffix in _EQUITY_SUFFIXES)
