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
        "REST facade for broker-backed market data APIs.\n\n"
        "Current provider support: `angelone`.\n\n"
        "Recommended derivative discovery flow:\n"
        "1. `/market/derivative-underlyings`\n"
        "2. `/market/derivative-expiries`\n"
        "3. `/market/derivative-strikes`\n"
        "4. `/market/derivative-contracts` when full contract rows are needed\n"
        "5. `/market/quotes` or `/market/derivatives/history` for live or historical market data"
    ),
    version="1.0.0",
    openapi_tags=[
        {"name": "system", "description": "Service health and transport-level diagnostics."},
        {"name": "reference", "description": "Static or semi-static market reference data such as exchanges, instrument types, and broker search results."},
        {"name": "discovery", "description": "Derivative discovery endpoints used to populate UI dropdowns for underlying, expiry, strike, and contract selection."},
        {"name": "market-data", "description": "Live and historical market data endpoints for quotes and candles."},
        {"name": "resolution", "description": "Endpoints that resolve a user-facing derivative selection into a concrete broker instrument."},
    ],
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
        example="26MAY2026",
        description=(
            "Derivative expiry in the same format as Angel One scrip master. "
            "This must be a currently listed contract expiry."
        ),
    )
    strike: float | None = Field(
        default=None,
        example=43000,
        description=(
            "Human-readable strike price. Usually required for options. "
            "For current valid combinations, discover contracts via "
            "`/market/derivative-symbols` or `/market/instruments?provider=angelone&market=NFO&query=BANKNIFTY`."
        ),
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
                        "expiry": "26MAY2026",
                        "strike": 43000,
                        "option_type": "CE",
                    }
                ],
            }
        }


class DerivativeHistoryRequest(BaseModel):
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
    strike: float | None = Field(
        default=None,
        example=43000,
        description="Human-readable strike. Required for options.",
    )
    option_type: Literal["CE", "PE"] | None = Field(
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


@app.get(
    "/health",
    summary="Healthcheck",
    description="Return a lightweight service health response for the REST layer itself.",
    tags=["system"],
)
def health(request: Request) -> JSONResponse:
    return _json_response(
        path="/health",
        method="GET",
        query={},
        body={},
        request_id=_request_id(request),
    )


@app.get(
    "/market/instruments",
    summary="Search instruments",
    description=(
        "Search broker instruments within one market or exchange. "
        "Use this for free-text symbol or name lookup when the client does not already know the instrument family."
    ),
    tags=["reference"],
)
def instruments(
    request: Request,
    provider: str = Query(
        ..., description=PROVIDER_DESCRIPTION, example="angelone"
    ),
    market: str = Query(
        ...,
        description=(
            "Market/exchange to search in. "
            "Common values: `NSE`, `BSE`, `NFO`, `BFO`, `CDS`, `MCX`."
        ),
        example="NSE",
    ),
    query_value: str = Query(
        ...,
        alias="query",
        description=(
            "Symbol or name search term, e.g. `SBIN`, `RELIANCE`, `BANKNIFTY`."
        ),
        example="SBIN",
    ),
) -> JSONResponse:
    query = {
        "provider": provider,
        "market": market,
        "query": query_value,
    }
    return _json_response(
        path="/market/instruments",
        method="GET",
        query=query,
        body={},
        request_id=_request_id(request),
    )


@app.get(
    "/market/exchanges",
    summary="List exchanges",
    description="List exchanges currently available from the selected broker integration.",
    tags=["reference"],
)
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


@app.get(
    "/market/instrument-types",
    summary="List instrument types",
    description=(
        "List broker instrument types, optionally filtered by exchange. "
        "Useful for building broker-aware discovery UIs and diagnostics."
    ),
    tags=["reference"],
)
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
    "/market/instruments-by-exchange",
    summary="List instruments by exchange",
    description=(
        "Return the broker's instrument master rows for a single exchange. "
        "This is a broad reference-data endpoint and can produce large responses."
    ),
    tags=["reference"],
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
    description=(
        "Return a compact symbol-to-name reference view. "
        "Without `exchange`, the endpoint returns only per-exchange counts. "
        "With `exchange`, it returns a paged symbol/name listing suitable for search UIs."
    ),
    tags=["reference"],
)
def exchange_symbol_name_map(
    request: Request,
    provider: str = Query(
        ..., description=PROVIDER_DESCRIPTION, example="angelone"
    ),
    exchange: str | None = Query(
        default=None,
        description=(
            "Optional exchange filter. "
            "When omitted, the endpoint returns a compact per-exchange summary."
        ),
        example="NSE",
    ),
    query_value: str | None = Query(
        default=None,
        alias="query",
        description=(
            "Optional symbol/name search term. "
            "Applied only when `exchange` is provided."
        ),
        example="SBIN",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Paging offset for exchange-scoped symbol listings.",
        example=0,
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Maximum number of symbol rows to return for an exchange-scoped listing.",
        example=100,
    ),
) -> JSONResponse:
    query = {"provider": provider}
    if exchange:
        query["exchange"] = exchange
    if query_value:
        query["query"] = query_value
    if exchange or offset != 0:
        query["offset"] = str(offset)
    if exchange or limit != 100:
        query["limit"] = str(limit)

    return _json_response(
        path="/market/exchange-symbol-name-map",
        method="GET",
        query=query,
        body={},
        request_id=_request_id(request),
    )


@app.get(
    "/market/derivative-symbols",
    summary="List derivative symbols",
    description=(
        "Return grouped broker-native derivative symbols by exchange and instrument type. "
        "This is mainly a broker reference endpoint. Prefer underlyings, expiries, and strikes for UI dropdown flows."
    ),
    tags=["reference"],
)
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


@app.get(
    "/market/derivative-expiries",
    summary="List derivative expiries",
    description=(
        "List available expiries for one derivative family, defined by exchange, underlying, and instrument type. "
        "Use this after the underlying selection step."
    ),
    tags=["discovery"],
)
def derivative_expiries(
    request: Request,
    provider: str = Query(
        ..., description=PROVIDER_DESCRIPTION, example="angelone"
    ),
    exchange: str = Query(
        ...,
        description=EXCHANGE_DESCRIPTION,
        example="NFO",
    ),
    underlying: str = Query(
        ...,
        description="Underlying symbol/name, e.g. `BANKNIFTY`.",
        example="BANKNIFTY",
    ),
    instrument_type: str = Query(
        ...,
        description=INSTRUMENT_TYPE_DESCRIPTION,
        example="OPTIDX",
    ),
) -> JSONResponse:
    return _json_response(
        path="/market/derivative-expiries",
        method="GET",
        query={
            "provider": provider,
            "exchange": exchange,
            "underlying": underlying,
            "instrument_type": instrument_type,
        },
        body={},
        request_id=_request_id(request),
    )


@app.get(
    "/market/derivative-underlyings",
    summary="List derivative underlyings",
    description=(
        "List derivative underlyings grouped by exchange and instrument type. "
        "This is the recommended first step for building derivative selection dropdowns."
    ),
    tags=["discovery"],
)
def derivative_underlyings(
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
        path="/market/derivative-underlyings",
        method="GET",
        query=query,
        body={},
        request_id=_request_id(request),
    )


@app.get(
    "/market/derivative-strikes",
    summary="List derivative strikes",
    description=(
        "List unique sorted strikes for a selected derivative family and expiry. "
        "This endpoint is intended for strike dropdowns and returns strikes only, not full contract rows."
    ),
    tags=["discovery"],
)
def derivative_strikes(
    request: Request,
    provider: str = Query(
        ..., description=PROVIDER_DESCRIPTION, example="angelone"
    ),
    exchange: str = Query(
        ...,
        description=EXCHANGE_DESCRIPTION,
        example="NFO",
    ),
    underlying: str = Query(
        ...,
        description="Underlying symbol/name, e.g. `BANKNIFTY` or `RELIANCE`.",
        example="BANKNIFTY",
    ),
    instrument_type: str = Query(
        ...,
        description=INSTRUMENT_TYPE_DESCRIPTION,
        example="OPTIDX",
    ),
    expiry: str = Query(
        ...,
        description="Derivative expiry in broker master format.",
        example="26MAY2026",
    ),
    option_type: str | None = Query(
        default=None,
        description="Optional option side filter for option contracts.",
        example="CE",
    ),
) -> JSONResponse:
    query = {
        "provider": provider,
        "exchange": exchange,
        "underlying": underlying,
        "instrument_type": instrument_type,
        "expiry": expiry,
    }
    if option_type:
        query["option_type"] = option_type
    return _json_response(
        path="/market/derivative-strikes",
        method="GET",
        query=query,
        body={},
        request_id=_request_id(request),
    )


@app.get(
    "/market/derivative-contracts",
    summary="List derivative contracts",
    description=(
        "List full derivative contract rows for a selected underlying family and expiry. "
        "Use this when the client needs more than a strike list, such as contract symbols, lot sizes, or option sides."
    ),
    tags=["discovery"],
)
def derivative_contracts(
    request: Request,
    provider: str = Query(
        ..., description=PROVIDER_DESCRIPTION, example="angelone"
    ),
    exchange: str = Query(
        ...,
        description=EXCHANGE_DESCRIPTION,
        example="NFO",
    ),
    underlying: str = Query(
        ...,
        description="Underlying symbol/name, e.g. `BANKNIFTY` or `RELIANCE`.",
        example="BANKNIFTY",
    ),
    instrument_type: str = Query(
        ...,
        description=INSTRUMENT_TYPE_DESCRIPTION,
        example="OPTIDX",
    ),
    expiry: str = Query(
        ...,
        description="Derivative expiry in broker master format.",
        example="26MAY2026",
    ),
    option_type: str | None = Query(
        default=None,
        description="Optional option side filter for option contracts.",
        example="CE",
    ),
) -> JSONResponse:
    query = {
        "provider": provider,
        "exchange": exchange,
        "underlying": underlying,
        "instrument_type": instrument_type,
        "expiry": expiry,
    }
    if option_type:
        query["option_type"] = option_type
    return _json_response(
        path="/market/derivative-contracts",
        method="GET",
        query=query,
        body={},
        request_id=_request_id(request),
    )


@app.post(
    "/market/quotes",
    summary="Fetch quotes",
    description=(
        "Fetch live quote data for one or more symbols. "
        "This endpoint is optimized for user-facing symbols rather than broker tokens."
    ),
    tags=["market-data"],
)
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


@app.post(
    "/market/candles",
    summary="Fetch candles",
    description=(
        "Fetch historical OHLCV candles for a cash-market symbol. "
        "The REST layer resolves the broker token internally from the provided symbol."
    ),
    tags=["market-data"],
)
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
    "/market/derivatives/history",
    summary="Fetch derivative candles/history",
    description=(
        "Fetch historical OHLCV candles for one derivative contract. "
        "The REST layer resolves the derivative instrument internally from the provided family, expiry, strike, and option side."
    ),
    tags=["market-data"],
)
def derivative_history(
    request: Request, payload: DerivativeHistoryRequest = Body(...)
) -> JSONResponse:
    return _json_response(
        path="/market/derivatives/history",
        method="POST",
        query={},
        body=payload.dict(exclude_none=True, by_alias=True),
        request_id=_request_id(request),
    )


@app.post(
    "/market/derivatives/resolve",
    summary="Resolve derivative instruments",
    description=(
        "Resolve one or more user-facing derivative selections into concrete broker instrument rows. "
        "Use this when the client needs the exact exchange symbol and broker token backing a chosen contract."
    ),
    tags=["resolution"],
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
