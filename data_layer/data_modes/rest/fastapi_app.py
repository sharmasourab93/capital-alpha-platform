from __future__ import annotations

from typing import Literal

from fastapi import Body, FastAPI, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

try:
    from .http_core import handle_http_request
except ImportError:  # pragma: no cover
    from http_core import handle_http_request

app = FastAPI(
    title="Capital Alpha Market Data REST Layer",
    description=(
        "REST facade for market data brokers. "
        "Angel One is currently the implemented provider."
    ),
)

PROVIDER_DESCRIPTION = "Broker provider. Supported now: `angelone`."
EXCHANGE_DESCRIPTION = "Exchange code. Common Angel One values include `NSE`, `BSE`, `NFO`, `BFO`, `CDS`, `MCX`."
QUOTE_MODE_DESCRIPTION = (
    "Quote mode. Allowed values: `LTP`, `OHLC`, `FULL`. "
    "`LTP` is lightest, `OHLC` adds day open/high/low/close, `FULL` is the richest payload."
)
INTERVAL_DESCRIPTION = "Candle interval. Allowed values: `1m`, `3m`, `5m`, `10m`, `15m`, `30m`, `1h`, `1d`."
INSTRUMENT_TYPE_DESCRIPTION = "Angel One instrument type. Common values: `EQ`, `FUTIDX`, `FUTSTK`, `OPTIDX`, `OPTSTK`."


class QuotesRequest(BaseModel):
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
    symbols: list[str] | None = Field(
        ...,
        example=["SBIN", "RELIANCE", "BHEL"],
        description="User-facing ticker symbols. For equities plain symbols like `SBIN` are accepted.",
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
        description="Per-request symbol batch size. Current Angel One limit is 50 instruments per market-data call.",
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


class CandlesRequest(BaseModel):
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


class DerivativeRequestItem(BaseModel):
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
        example="29MAY2025",
        description="Derivative expiry in the same format as Angel One scrip master.",
    )
    strike: float | None = Field(
        default=None,
        example=50000,
        description="Strike price. Usually required for options.",
    )
    option_type: Literal["CE", "PE"] | None = Field(
        default=None,
        description="Option side. Allowed values: `CE`, `PE`.",
    )


class DerivativeResolveRequest(BaseModel):
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
                        "expiry": "29MAY2025",
                        "strike": 50000,
                        "option_type": "CE",
                    }
                ],
            }
        }


def _json_response(
    path: str,
    method: str,
    query: dict[str, str] | None,
    body: dict | None,
    request_id: str | None,
) -> JSONResponse:
    status_code, payload = handle_http_request(
        path=path,
        method=method,
        query=query or {},
        body=body or {},
        request_id=request_id,
    )
    return JSONResponse(status_code=status_code, content=payload)


def _request_id(request: Request) -> str | None:
    return request.headers.get("x-request-id")


@app.get("/health", summary="Healthcheck")
def health(request: Request) -> JSONResponse:
    return _json_response(
        path="/health",
        method="GET",
        query={},
        body={},
        request_id=_request_id(request),
    )


@app.get("/market/instruments", summary="Search instruments")
def instruments(
    request: Request,
    provider: str = Query(
        ..., description=PROVIDER_DESCRIPTION, example="angelone"
    ),
    exchange: str = Query(
        ..., description=EXCHANGE_DESCRIPTION, example="NSE"
    ),
    query_value: str | None = Query(
        default=None,
        alias="query",
        description="Free-text search term, e.g. `SBIN`, `BANKNIFTY`, `RELIANCE`.",
        example="SBIN",
    ),
    segment: str | None = Query(
        default=None,
        description="Optional segment filter, e.g. `EQ`, `OPTIDX`, `FUTIDX`.",
        example="EQ",
    ),
    symbol: str | None = Query(
        default=None,
        description="Optional exact/near-exact symbol hint, e.g. `SBIN`, `SBIN-EQ`.",
        example="SBIN",
    ),
) -> JSONResponse:
    query = {
        "provider": provider,
        "exchange": exchange,
    }
    if query_value:
        query["query"] = query_value
    if segment:
        query["segment"] = segment
    if symbol:
        query["symbol"] = symbol
    return _json_response(
        path="/market/instruments",
        method="GET",
        query=query,
        body={},
        request_id=_request_id(request),
    )


@app.get("/market/exchanges", summary="List exchanges")
def exchanges(
    request: Request,
    provider: str = Query(
        ..., description=PROVIDER_DESCRIPTION, example="angelone"
    ),
) -> JSONResponse:
    return _json_response(
        path="/market/exchanges",
        method="GET",
        query={"provider": provider},
        body={},
        request_id=_request_id(request),
    )


@app.get("/market/instrument-types", summary="List instrument types")
def instrument_types(
    request: Request,
    provider: str = Query(
        ..., description=PROVIDER_DESCRIPTION, example="angelone"
    ),
    exchange: str | None = Query(
        default=None,
        description=EXCHANGE_DESCRIPTION,
        example="NFO",
    ),
) -> JSONResponse:
    query = {"provider": provider}
    if exchange:
        query["exchange"] = exchange
    return _json_response(
        path="/market/instrument-types",
        method="GET",
        query=query,
        body={},
        request_id=_request_id(request),
    )


@app.get(
    "/market/instruments-by-exchange", summary="List instruments by exchange"
)
def instruments_by_exchange(
    request: Request,
    provider: str = Query(
        ..., description=PROVIDER_DESCRIPTION, example="angelone"
    ),
    exchange: str = Query(
        ..., description=EXCHANGE_DESCRIPTION, example="NSE"
    ),
) -> JSONResponse:
    return _json_response(
        path="/market/instruments-by-exchange",
        method="GET",
        query={"provider": provider, "exchange": exchange},
        body={},
        request_id=_request_id(request),
    )


@app.get(
    "/market/exchange-symbol-name-map",
    summary="Get exchange to symbol-name map",
)
def exchange_symbol_name_map(
    request: Request,
    provider: str = Query(
        ..., description=PROVIDER_DESCRIPTION, example="angelone"
    ),
) -> JSONResponse:
    return _json_response(
        path="/market/exchange-symbol-name-map",
        method="GET",
        query={"provider": provider},
        body={},
        request_id=_request_id(request),
    )


@app.get("/market/derivative-symbols", summary="List derivative symbols")
def derivative_symbols(
    request: Request,
    provider: str = Query(
        ..., description=PROVIDER_DESCRIPTION, example="angelone"
    ),
    exchange: str | None = Query(
        default=None,
        description=EXCHANGE_DESCRIPTION,
        example="NFO",
    ),
    instrument_type: str | None = Query(
        default=None,
        description=INSTRUMENT_TYPE_DESCRIPTION,
        example="OPTIDX",
    ),
) -> JSONResponse:
    query = {"provider": provider}
    if exchange:
        query["exchange"] = exchange
    if instrument_type:
        query["instrument_type"] = instrument_type
    return _json_response(
        path="/market/derivative-symbols",
        method="GET",
        query=query,
        body={},
        request_id=_request_id(request),
    )


@app.post("/market/quotes", summary="Fetch quotes")
@app.post("/market/marketdata", summary="Fetch quotes")
def quotes(
    request: Request, payload: QuotesRequest = Body(...)
) -> JSONResponse:
    return _json_response(
        path="/market/quotes",
        method="POST",
        query={},
        body=payload.dict(exclude_none=True, by_alias=True),
        request_id=_request_id(request),
    )


@app.post("/market/candles", summary="Fetch candles")
def candles(
    request: Request, payload: CandlesRequest = Body(...)
) -> JSONResponse:
    return _json_response(
        path="/market/candles",
        method="POST",
        query={},
        body=payload.dict(exclude_none=True, by_alias=True),
        request_id=_request_id(request),
    )


@app.post(
    "/market/derivatives/resolve", summary="Resolve derivative instruments"
)
def resolve_derivative(
    request: Request,
    payload: DerivativeResolveRequest = Body(...),
) -> JSONResponse:
    return _json_response(
        path="/market/derivatives/resolve",
        method="POST",
        query={},
        body=payload.dict(exclude_none=True, by_alias=True),
        request_id=_request_id(request),
    )


@app.post("/market/derivatives/tokens", summary="Resolve derivative tokens")
def derivative_tokens(
    request: Request,
    payload: DerivativeResolveRequest = Body(...),
) -> JSONResponse:
    return _json_response(
        path="/market/derivatives/tokens",
        method="POST",
        query={},
        body=payload.dict(exclude_none=True, by_alias=True),
        request_id=_request_id(request),
    )
