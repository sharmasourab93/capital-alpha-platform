from __future__ import annotations

from pydantic import BaseModel

PROVIDER_DESCRIPTION = "Broker provider. Supported now: `angelone`."
EXCHANGE_DESCRIPTION = (
    "Exchange code. Common Angel One values include `NSE`, `BSE`, `NFO`, "
    "`BFO`, `CDS`, `MCX`."
)
QUOTE_MODE_DESCRIPTION = (
    "Quote mode. Allowed values: `LTP`, `OHLC`, `FULL`. "
    "`LTP` is lightest, `OHLC` adds day open/high/low/close, `FULL` is the "
    "richest payload."
)
INTERVAL_DESCRIPTION = (
    "Candle interval. Allowed values: `1m`, `3m`, `5m`, `10m`, `15m`, `30m`, "
    "`1h`, `1d`."
)
INSTRUMENT_TYPE_DESCRIPTION = (
    "Angel One instrument type. Common values: `EQ`, `FUTIDX`, `FUTSTK`, "
    "`OPTIDX`, `OPTSTK`."
)


class CompatBaseModel(BaseModel):
    @classmethod
    def model_validate(cls, payload):
        if hasattr(BaseModel, "model_validate"):
            return BaseModel.model_validate.__get__(cls, cls)(payload)
        return cls.parse_obj(payload)


def model_dump(payload: BaseModel) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_none=True, by_alias=True)
    return payload.dict(exclude_none=True, by_alias=True)
