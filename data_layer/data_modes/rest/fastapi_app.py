from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

try:
    from .api_docs import APP_DESCRIPTION, APP_TITLE, APP_VERSION, OPENAPI_TAGS
    from .api_models import DerivativeHistoryRequest
    from .api_routers import build_router_bundle
    from .http_core import handle_http_request
    from .security import (
        enforce_request_security,
        load_settings,
        validate_rest_request,
    )
except ImportError:  # pragma: no cover
    from api_docs import APP_DESCRIPTION, APP_TITLE, APP_VERSION, OPENAPI_TAGS
    from api_models import DerivativeHistoryRequest
    from api_routers import build_router_bundle
    from http_core import handle_http_request
    from security import (
        enforce_request_security,
        load_settings,
        validate_rest_request,
    )

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    openapi_tags=OPENAPI_TAGS,
)


@app.middleware("http")
async def rest_security_middleware(request: Request, call_next):
    security_response = await enforce_request_security(request)
    if security_response is not None:
        return security_response

    response = await call_next(request)
    origin = request.headers.get("origin")
    settings = load_settings()
    if origin and origin in settings.allowed_origins:
        response.headers.setdefault("Access-Control-Allow-Origin", origin)
        response.headers.setdefault("Vary", "Origin")
    return response


@app.exception_handler(ValueError)
async def value_error_handler(
    request: Request, exc: ValueError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "type": "BAD_REQUEST",
                "message": str(exc),
                "details": [],
            },
            "meta": {
                "request_id": _request_id(request),
            },
        },
    )


def _request_id(request: Request) -> str | None:
    return request.headers.get("x-request-id")


def _json_response(
    *,
    path: str,
    method: str,
    request: Request,
    query: dict[str, str] | None = None,
    body: dict | None = None,
) -> JSONResponse:
    validate_rest_request(
        path=path,
        method=method,
        query=query,
        body=body,
    )
    status_code, payload = handle_http_request(
        path=path,
        method=method,
        query=query or {},
        body=body or {},
        request_id=_request_id(request),
    )
    return JSONResponse(status_code=status_code, content=payload)


_ROUTERS = build_router_bundle(_json_response)

system_router = _ROUTERS.system_router
reference_router = _ROUTERS.reference_router
cash_router = _ROUTERS.cash_router
derivatives_router = _ROUTERS.derivatives_router

health = _ROUTERS.health
instruments = _ROUTERS.instruments
exchanges = _ROUTERS.exchanges
instrument_types = _ROUTERS.instrument_types
exchange_symbol_name_map = _ROUTERS.exchange_symbol_name_map
nse_listed_stocks = _ROUTERS.nse_listed_stocks
bse_listed_stocks = _ROUTERS.bse_listed_stocks
derivative_symbols = _ROUTERS.derivative_symbols
derivative_underlyings = _ROUTERS.derivative_underlyings
derivative_expiries = _ROUTERS.derivative_expiries
derivative_strikes = _ROUTERS.derivative_strikes
derivative_contracts = _ROUTERS.derivative_contracts
quotes = _ROUTERS.quotes
candles = _ROUTERS.candles
derivative_history = _ROUTERS.derivative_history
resolve_derivative = _ROUTERS.resolve_derivative


app.include_router(system_router)
app.include_router(reference_router)
app.include_router(cash_router)
app.include_router(derivatives_router)

__all__ = [
    "app",
    "bse_listed_stocks",
    "candles",
    "cash_router",
    "derivative_contracts",
    "DerivativeHistoryRequest",
    "derivative_expiries",
    "derivative_history",
    "derivative_strikes",
    "derivative_symbols",
    "derivative_underlyings",
    "derivatives_router",
    "exchange_symbol_name_map",
    "exchanges",
    "health",
    "instrument_types",
    "instruments",
    "nse_listed_stocks",
    "quotes",
    "reference_router",
    "resolve_derivative",
    "rest_security_middleware",
    "system_router",
]
