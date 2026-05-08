from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from .common import (
    EXCHANGE_DESCRIPTION,
    INSTRUMENT_TYPE_DESCRIPTION,
    INTERVAL_DESCRIPTION,
    PROVIDER_DESCRIPTION,
    CompatBaseModel,
)


class DerivativeRequestItem(CompatBaseModel):
    exchange: str = Field(..., example="NFO", description=EXCHANGE_DESCRIPTION)
    underlying: str = Field(
        ...,
        example="BANKNIFTY",
        description="Underlying symbol/name used for derivative resolution.",
    )
    instrument_type: str = Field(
        ...,
        example="OPTIDX",
        description=INSTRUMENT_TYPE_DESCRIPTION,
    )
    expiry: str = Field(
        ...,
        example="26MAY2026",
        description=(
            "Derivative expiry in the same format as Angel One scrip master. "
            "This must be a currently listed contract expiry."
        ),
    )
    strike: Optional[float] = Field(
        default=None,
        example=43000,
        description=(
            "Human-readable strike price. Usually required for options. "
            "For current valid combinations, discover contracts via "
            "`/market/derivatives/symbols` or "
            "`/market/reference/instruments?provider=angelone&market=NFO&query=BANKNIFTY`."
        ),
    )
    option_type: Optional[Literal["CE", "PE"]] = Field(
        default=None,
        description="Option side. Allowed values: `CE`, `PE`.",
    )


class DerivativeResolveRequest(CompatBaseModel):
    provider: str = Field(
        ..., example="angelone", description=PROVIDER_DESCRIPTION
    )
    requests: list[DerivativeRequestItem] = Field(
        ...,
        description="One or more derivative resolution requests.",
    )

    class Config:
        schema_extra = {
            "example": {
                "provider": "angelone",
                "requests": [
                    {
                        "exchange": "NFO",
                        "underlying": "BANKNIFTY",
                        "instrument_type": "OPTIDX",
                        "expiry": "26MAY2026",
                        "strike": 43000,
                        "option_type": "CE",
                    }
                ],
            }
        }


class DerivativeHistoryRequest(CompatBaseModel):
    provider: str = Field(
        ..., example="angelone", description=PROVIDER_DESCRIPTION
    )
    exchange: str = Field(..., example="NFO", description=EXCHANGE_DESCRIPTION)
    underlying: str = Field(
        ...,
        example="BANKNIFTY",
        description="Underlying symbol/name used for derivative lookup.",
    )
    instrument_type: str = Field(
        ...,
        example="OPTIDX",
        description=INSTRUMENT_TYPE_DESCRIPTION,
    )
    expiry: str = Field(
        ...,
        example="26MAY2026",
        description="Derivative expiry in broker master format.",
    )
    strike: Optional[float] = Field(
        default=None,
        example=43000,
        description="Human-readable strike. Required for options.",
    )
    option_type: Optional[Literal["CE", "PE"]] = Field(
        default=None,
        description="Option side for option contracts.",
    )
    interval: Literal["1m", "3m", "5m", "10m", "15m", "30m", "1h", "1d"] = (
        Field(
            ...,
            description=INTERVAL_DESCRIPTION,
        )
    )
    from_value: str = Field(
        ...,
        alias="from",
        example="2026-05-01 09:15",
        description="Start datetime in provider format.",
    )
    to_value: str = Field(
        ...,
        alias="to",
        example="2026-05-04 15:30",
        description="End datetime in provider format.",
    )

    class Config:
        allow_population_by_field_name = True
        schema_extra = {
            "example": {
                "provider": "angelone",
                "exchange": "NFO",
                "underlying": "BANKNIFTY",
                "instrument_type": "OPTIDX",
                "expiry": "26MAY2026",
                "strike": 43000,
                "option_type": "CE",
                "interval": "1d",
                "from": "2026-05-01 09:15",
                "to": "2026-05-04 15:30",
            }
        }
