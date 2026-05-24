"""Pydantic schemas for REST request payloads."""

from __future__ import annotations

from pydantic import BaseModel, Field

MAX_MARKET_SYMBOLS = 50


class QuotePayload(BaseModel):
    """Payload for quote requests."""

    symbols: list[str] = Field(min_length=1, max_length=MAX_MARKET_SYMBOLS)
    mode: str = "FULL"


class CandlePayload(BaseModel):
    """Payload for candle requests."""

    symbol: str
    interval: str
    from_time: str
    to_time: str
