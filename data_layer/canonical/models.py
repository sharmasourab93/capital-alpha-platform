from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CanonicalQuote:
    """Broker-agnostic snapshot of a tradable symbol's latest quote."""

    provider: str
    exchange: str
    symbol: str
    broker_symbol: str
    token: str | None
    ltp: float
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: int | None = None
    as_of: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CanonicalCandle:
    """Broker-agnostic OHLCV candle for a single symbol and interval."""

    provider: str
    exchange: str
    symbol: str
    interval: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int | None = None
    raw: list[Any] = field(default_factory=list)


@dataclass(frozen=True)
class CanonicalInstrument:
    """Broker-agnostic instrument record for cash and derivative symbols."""

    provider: str
    exchange: str
    symbol: str
    broker_symbol: str
    token: str | None
    name: str
    instrument_type: str | None = None
    underlying: str | None = None
    expiry: str | None = None
    strike: float | None = None
    option_type: str | None = None
    lot_size: int | None = None
    exchange_segment: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CanonicalDerivativeUnderlying:
    """Broker-agnostic derivative family key used for underlying discovery."""

    provider: str
    exchange: str
    instrument_type: str
    underlying: str
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CanonicalDerivativeExpiry:
    """Broker-agnostic expiry row for an underlying and instrument type."""

    provider: str
    exchange: str
    instrument_type: str
    underlying: str
    expiry: str
    raw: dict[str, Any] = field(default_factory=dict)
