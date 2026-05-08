from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from .common import (
    EXCHANGE_DESCRIPTION,
    INTERVAL_DESCRIPTION,
    PROVIDER_DESCRIPTION,
    QUOTE_MODE_DESCRIPTION,
    CompatBaseModel,
)


class QuotesRequest(CompatBaseModel):
    provider: str = Field(
        ...,
        example="angelone",
        description=PROVIDER_DESCRIPTION,
    )
    exchange: str = Field(
        ...,
        example="NSE",
        description=EXCHANGE_DESCRIPTION,
    )
    mode: Literal["LTP", "OHLC", "FULL"] = Field(
        default="FULL",
        description=QUOTE_MODE_DESCRIPTION,
    )
    symbols: Optional[list[str]] = Field(
        ...,
        example=["SBIN", "RELIANCE", "BHEL"],
        description=(
            "User-facing ticker symbols. For equities plain symbols like "
            "`SBIN` are accepted. Requests are capped at 50 symbols."
        ),
    )

    class Config:
        schema_extra = {
            "example": {
                "provider": "angelone",
                "exchange": "NSE",
                "mode": "LTP",
                "symbols": ["SBIN", "RELIANCE", "BHEL"],
            }
        }


class BulkQuotesRequest(QuotesRequest):
    mode: Literal["LTP", "OHLC", "FULL"] = Field(
        default="LTP",
        description=QUOTE_MODE_DESCRIPTION,
    )
    chunk_size: int = Field(
        default=50,
        ge=1,
        le=50,
        description=(
            "Per-request symbol batch size. Current Angel One limit is 50 "
            "instruments per market-data call."
        ),
    )
    pause_seconds: float = Field(
        default=1.05,
        ge=0,
        description="Pause between chunks to stay under provider rate limits.",
    )

    class Config:
        schema_extra = {
            "example": {
                "provider": "angelone",
                "exchange": "NSE",
                "mode": "LTP",
                "symbols": ["SBIN", "RELIANCE", "UBL", "BHEL", "MTARTECH"],
                "chunk_size": 50,
                "pause_seconds": 1.05,
            }
        }


class CandlesRequest(CompatBaseModel):
    provider: str = Field(
        ..., example="angelone", description=PROVIDER_DESCRIPTION
    )
    exchange: str = Field(..., example="NSE", description=EXCHANGE_DESCRIPTION)
    interval: Literal["1m", "3m", "5m", "10m", "15m", "30m", "1h", "1d"] = (
        Field(
            ...,
            description=INTERVAL_DESCRIPTION,
        )
    )
    from_value: str = Field(
        ...,
        alias="from",
        example="2025-01-01 09:15",
        description="Start datetime in provider format.",
    )
    to_value: str = Field(
        ...,
        alias="to",
        example="2025-04-10 15:30",
        description="End datetime in provider format.",
    )
    symbol: str = Field(
        ...,
        example="SBIN",
        description="User-facing ticker symbol. Plain symbols like `SBIN` are accepted.",
    )

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "provider": "angelone",
                "exchange": "NSE",
                "interval": "1d",
                "from": "2025-01-01 09:15",
                "to": "2025-04-10 15:30",
                "symbol": "SBIN",
            }
        }
