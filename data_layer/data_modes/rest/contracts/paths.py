from __future__ import annotations

HEALTH = "/health"

REFERENCE_INSTRUMENTS = "/market/reference/instruments"
REFERENCE_EXCHANGES = "/market/reference/exchanges"
REFERENCE_INSTRUMENT_TYPES = "/market/reference/instrument-types"
REFERENCE_EXCHANGE_SYMBOL_NAME_MAP = (
    "/market/reference/exchange-symbol-name-map"
)

CASH_NSE_LISTED_STOCKS = "/market/cash/nse-listed-stocks"
CASH_BSE_LISTED_STOCKS = "/market/cash/bse-listed-stocks"
CASH_QUOTES = "/market/cash/quotes"
CASH_CANDLES = "/market/cash/candles"

DERIVATIVES_SYMBOLS = "/market/derivatives/symbols"
DERIVATIVES_UNDERLYINGS = "/market/derivatives/underlyings"
DERIVATIVES_EXPIRIES = "/market/derivatives/expiries"
DERIVATIVES_STRIKES = "/market/derivatives/strikes"
DERIVATIVES_CONTRACTS = "/market/derivatives/contracts"
DERIVATIVES_HISTORY = "/market/derivatives/history"
DERIVATIVES_RESOLVE = "/market/derivatives/resolve"

REFERENCE_PATHS = frozenset(
    {
        REFERENCE_INSTRUMENTS,
        REFERENCE_EXCHANGES,
        REFERENCE_INSTRUMENT_TYPES,
        REFERENCE_EXCHANGE_SYMBOL_NAME_MAP,
    }
)

CASH_PATHS = frozenset(
    {
        CASH_NSE_LISTED_STOCKS,
        CASH_BSE_LISTED_STOCKS,
        CASH_QUOTES,
        CASH_CANDLES,
    }
)

DERIVATIVES_PATHS = frozenset(
    {
        DERIVATIVES_SYMBOLS,
        DERIVATIVES_UNDERLYINGS,
        DERIVATIVES_EXPIRIES,
        DERIVATIVES_STRIKES,
        DERIVATIVES_CONTRACTS,
        DERIVATIVES_HISTORY,
        DERIVATIVES_RESOLVE,
    }
)

LIMITED_PAGE_PATHS = frozenset(
    {
        REFERENCE_EXCHANGE_SYMBOL_NAME_MAP,
        CASH_NSE_LISTED_STOCKS,
        CASH_BSE_LISTED_STOCKS,
    }
)

BODY_DATE_PATHS = frozenset(
    {
        CASH_CANDLES,
        DERIVATIVES_HISTORY,
    }
)
