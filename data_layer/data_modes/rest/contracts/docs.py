from __future__ import annotations

from dataclasses import dataclass

APP_TITLE = "Capital Alpha Market Data REST Layer"
APP_DESCRIPTION = (
    "REST facade for broker-backed market data APIs.\n\n"
    "Current provider support: `angelone`.\n\n"
    "Top-level route families:\n"
    "1. `/market/reference/*` for broker-aware reference data\n"
    "2. `/market/cash/*` for cash-equity listings, quotes, and candles\n"
    "3. `/market/derivatives/*` for derivative discovery, history, and resolution"
)
APP_VERSION = "1.0.0"

OPENAPI_TAGS = [
    {
        "name": "system",
        "description": "Service health and transport-level diagnostics.",
    },
    {
        "name": "reference",
        "description": (
            "Broker-aware reference data such as exchanges, instrument types, "
            "and symbol-to-name maps."
        ),
    },
    {
        "name": "cash",
        "description": (
            "Cash-equity endpoints for exchange stock lists, quotes, and candles."
        ),
    },
    {
        "name": "derivatives",
        "description": (
            "Derivative discovery, history, and resolution endpoints."
        ),
    },
]


@dataclass(frozen=True)
class EndpointDoc:
    summary: str
    description: str


HEALTH_DOC = EndpointDoc(
    summary="Healthcheck",
    description="Return a lightweight service health response for the REST layer itself.",
)
REFERENCE_INSTRUMENTS_DOC = EndpointDoc(
    summary="Search instruments",
    description=(
        "Search broker instruments within one market or exchange. Use this for "
        "free-text symbol or name lookup when the client does not already know "
        "the instrument family."
    ),
)
REFERENCE_EXCHANGES_DOC = EndpointDoc(
    summary="List exchanges",
    description="List exchanges currently available from the selected broker integration.",
)
REFERENCE_INSTRUMENT_TYPES_DOC = EndpointDoc(
    summary="List instrument types",
    description=(
        "List broker instrument types, optionally filtered by exchange. Useful "
        "for building broker-aware discovery UIs and diagnostics."
    ),
)
REFERENCE_EXCHANGE_SYMBOL_NAME_MAP_DOC = EndpointDoc(
    summary="Get exchange to symbol-name map",
    description=(
        "Return a compact symbol-to-name reference view. Without `exchange`, "
        "the endpoint returns only per-exchange counts. With `exchange`, it "
        "returns a paged symbol/name listing suitable for search UIs."
    ),
)
CASH_NSE_LISTED_STOCKS_DOC = EndpointDoc(
    summary="List NSE listed stocks",
    description=(
        "Return a compact paged list of NSE-listed cash equities with canonical "
        "symbols and stock names."
    ),
)
CASH_BSE_LISTED_STOCKS_DOC = EndpointDoc(
    summary="List BSE listed stocks",
    description=(
        "Return a compact paged list of BSE-listed cash equities with canonical "
        "symbols and stock names."
    ),
)
CASH_QUOTES_DOC = EndpointDoc(
    summary="Fetch cash quotes",
    description=(
        "Fetch live quote data for one or more cash-market symbols. This "
        "endpoint is optimized for user-facing equity symbols rather than "
        "broker tokens."
    ),
)
CASH_CANDLES_DOC = EndpointDoc(
    summary="Fetch cash candles",
    description=(
        "Fetch historical OHLCV candles for a cash-market symbol. The REST "
        "layer resolves the broker token internally from the provided symbol."
    ),
)
DERIVATIVES_SYMBOLS_DOC = EndpointDoc(
    summary="List derivative symbols",
    description=(
        "Return grouped broker-native derivative symbols by exchange and "
        "instrument type. Prefer underlyings, expiries, strikes, and contracts "
        "for user-facing selection flows."
    ),
)
DERIVATIVES_UNDERLYINGS_DOC = EndpointDoc(
    summary="List derivative underlyings",
    description=(
        "List derivative underlyings grouped by exchange and instrument type. "
        "This is the recommended first step for building derivative selection "
        "dropdowns."
    ),
)
DERIVATIVES_EXPIRIES_DOC = EndpointDoc(
    summary="List derivative expiries",
    description=(
        "List available expiries for one derivative family, defined by "
        "exchange, underlying, and instrument type."
    ),
)
DERIVATIVES_STRIKES_DOC = EndpointDoc(
    summary="List derivative strikes",
    description=(
        "List unique sorted strikes for a selected derivative family and "
        "expiry. Returns strikes only, not full contract rows."
    ),
)
DERIVATIVES_CONTRACTS_DOC = EndpointDoc(
    summary="List derivative contracts",
    description=(
        "List full derivative contract rows for a selected underlying family "
        "and expiry. Use this when the client needs more than a strike list."
    ),
)
DERIVATIVES_HISTORY_DOC = EndpointDoc(
    summary="Fetch derivative candles/history",
    description=(
        "Fetch historical OHLCV candles for one derivative contract. The REST "
        "layer resolves the derivative instrument internally from the provided "
        "family, expiry, strike, and option side."
    ),
)
DERIVATIVES_RESOLVE_DOC = EndpointDoc(
    summary="Resolve derivative instruments",
    description=(
        "Resolve one or more user-facing derivative selections into concrete "
        "broker instrument rows."
    ),
)
