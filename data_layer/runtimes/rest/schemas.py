"""Pydantic schemas for REST request payloads."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

MAX_MARKET_SYMBOLS = 50
QuoteMode = Literal["LTP", "OHLC", "FULL"]


class QuotePayload(BaseModel):
    """Payload for quote requests."""

    symbols: list[str] = Field(min_length=1, max_length=MAX_MARKET_SYMBOLS)
    mode: QuoteMode = "FULL"

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, symbols: list[str]) -> list[str]:
        """Trim symbols and reject blank entries."""
        normalized_symbols = []
        for symbol in symbols:
            normalized_symbol = _normalize_required_string(symbol, "symbols")
            normalized_symbols.append(normalized_symbol)
        return normalized_symbols

    @field_validator("mode", mode="before")
    @classmethod
    def normalize_mode(cls, mode: str) -> str:
        """Normalize quote mode before enum validation."""
        return _normalize_required_string(mode, "mode").upper()


class CandlePayload(BaseModel):
    """Payload for candle requests."""

    symbol: str
    interval: str
    from_time: str
    to_time: str

    @field_validator("symbol", "interval", "from_time", "to_time")
    @classmethod
    def normalize_required_text(cls, value: str, info) -> str:
        """Trim required candle text fields."""
        return _normalize_required_string(value, info.field_name)


def _normalize_required_string(value: str, field_name: str) -> str:
    """Return stripped text or raise a request validation error."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} is required")
    return normalized_value
