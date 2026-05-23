"""Canonical broker REST request and response models."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from data_layer.brokers.canonical.errors import BrokerValidationError

SUPPORTED_QUOTE_MODES = frozenset({"LTP", "OHLC", "FULL"})


@dataclass(frozen=True, slots=True)
class AccountRequest:
    """Canonical account request for one broker."""

    broker: str

    def __post_init__(self) -> None:
        """Validate and normalize account request fields."""
        _set_normalized(
            self, "broker", _normalize_required(self.broker, "broker")
        )


@dataclass(frozen=True, slots=True)
class ScripRequest(AccountRequest):
    """Canonical instrument lookup request."""

    exchange: str
    symbol: str

    def __post_init__(self) -> None:
        """Validate and normalize instrument lookup fields."""
        AccountRequest.__post_init__(self)
        _set_normalized(
            self,
            "exchange",
            _normalize_required(self.exchange, "exchange").upper(),
        )
        _set_normalized(
            self, "symbol", _normalize_required(self.symbol, "symbol")
        )


@dataclass(frozen=True, slots=True)
class ScripListRequest(AccountRequest):
    """Canonical instrument-list request."""

    exchange: str = "NSE"

    def __post_init__(self) -> None:
        """Validate and normalize instrument-list fields."""
        AccountRequest.__post_init__(self)
        _set_normalized(
            self,
            "exchange",
            _normalize_required(self.exchange, "exchange").upper(),
        )


@dataclass(frozen=True, slots=True)
class LtpRequest(ScripRequest):
    """Canonical LTP request."""


@dataclass(frozen=True, slots=True)
class CandleRequest(ScripRequest):
    """Canonical historical candle request."""

    interval: str
    from_time: str
    to_time: str

    def __post_init__(self) -> None:
        """Validate and normalize candle request fields."""
        ScripRequest.__post_init__(self)
        _set_normalized(
            self,
            "interval",
            _normalize_required(self.interval, "interval").upper(),
        )
        _set_normalized(
            self,
            "from_time",
            _normalize_required(self.from_time, "from_time"),
        )
        _set_normalized(
            self,
            "to_time",
            _normalize_required(self.to_time, "to_time"),
        )


@dataclass(frozen=True, slots=True)
class QuoteRequest(AccountRequest):
    """Canonical quote request."""

    exchange: str
    symbols: tuple[str, ...]
    mode: str = "FULL"

    def __init__(
        self,
        broker: str,
        exchange: str,
        symbols: Sequence[str],
        mode: str = "FULL",
    ) -> None:
        """Create a quote request from one or more symbols."""
        object.__setattr__(self, "broker", broker)
        object.__setattr__(self, "exchange", exchange)
        object.__setattr__(self, "symbols", tuple(symbols))
        object.__setattr__(self, "mode", mode)
        self.__post_init__()

    def __post_init__(self) -> None:
        """Validate and normalize quote request fields."""
        AccountRequest.__post_init__(self)
        _set_normalized(
            self,
            "exchange",
            _normalize_required(self.exchange, "exchange").upper(),
        )
        if not self.symbols:
            raise BrokerValidationError(
                "At least one symbol is required",
                {"field": "symbols"},
            )
        normalized_symbols = tuple(
            _normalize_required(symbol, "symbols") for symbol in self.symbols
        )
        _set_normalized(self, "symbols", normalized_symbols)
        mode = _normalize_required(self.mode, "mode").upper()
        if mode not in SUPPORTED_QUOTE_MODES:
            raise BrokerValidationError(
                "Unsupported quote mode",
                {
                    "field": "mode",
                    "mode": self.mode,
                    "supported_modes": sorted(SUPPORTED_QUOTE_MODES),
                },
            )
        _set_normalized(self, "mode", mode)


@dataclass(frozen=True, slots=True)
class BrokerResponse:
    """Canonical broker response envelope."""

    broker: str
    operation: str
    success: bool
    data: Any
    message: str | None = None
    error_code: str | None = None

    def __post_init__(self) -> None:
        """Validate and normalize response metadata."""
        _set_normalized(
            self, "broker", _normalize_required(self.broker, "broker")
        )
        _set_normalized(
            self,
            "operation",
            _normalize_required(self.operation, "operation"),
        )
        if not isinstance(self.success, bool):
            raise BrokerValidationError(
                "Response success must be boolean",
                {"field": "success", "value": self.success},
            )


@dataclass(frozen=True, slots=True)
class AccountResponse(BrokerResponse):
    """Canonical account operation response."""


@dataclass(frozen=True, slots=True)
class ScripResponse(BrokerResponse):
    """Canonical instrument lookup response."""


@dataclass(frozen=True, slots=True)
class ScripListResponse(BrokerResponse):
    """Canonical instrument-list response."""


@dataclass(frozen=True, slots=True)
class LtpResponse(BrokerResponse):
    """Canonical LTP response."""


@dataclass(frozen=True, slots=True)
class CandleResponse(BrokerResponse):
    """Canonical candle response."""


@dataclass(frozen=True, slots=True)
class QuoteResponse(BrokerResponse):
    """Canonical quote response."""


def _normalize_required(value: str, field_name: str) -> str:
    """Return stripped text or raise a validation error."""
    if not isinstance(value, str):
        raise BrokerValidationError(
            "Field must be a string",
            {"field": field_name, "value": value},
        )
    normalized = value.strip()
    if not normalized:
        raise BrokerValidationError(
            "Field is required",
            {"field": field_name},
        )
    return normalized


def _set_normalized(instance: object, field_name: str, value: Any) -> None:
    """Set a normalized value on a frozen dataclass."""
    object.__setattr__(instance, field_name, value)
