from __future__ import annotations

from .cash import build_cash_router
from .common import RouterBundle
from .derivatives import build_derivatives_router
from .reference import build_reference_router
from .system import build_system_router


def build_router_bundle(json_response) -> RouterBundle:
    system_router, health = build_system_router(json_response)
    reference_router, reference_endpoints = build_reference_router(
        json_response
    )
    cash_router, cash_endpoints = build_cash_router(json_response)
    derivatives_router, derivatives_endpoints = build_derivatives_router(
        json_response
    )

    return RouterBundle(
        system_router=system_router,
        reference_router=reference_router,
        cash_router=cash_router,
        derivatives_router=derivatives_router,
        health=health,
        instruments=reference_endpoints.instruments,
        exchanges=reference_endpoints.exchanges,
        instrument_types=reference_endpoints.instrument_types,
        exchange_symbol_name_map=reference_endpoints.exchange_symbol_name_map,
        nse_listed_stocks=cash_endpoints.nse_listed_stocks,
        bse_listed_stocks=cash_endpoints.bse_listed_stocks,
        derivative_symbols=derivatives_endpoints.derivative_symbols,
        derivative_underlyings=derivatives_endpoints.derivative_underlyings,
        derivative_expiries=derivatives_endpoints.derivative_expiries,
        derivative_strikes=derivatives_endpoints.derivative_strikes,
        derivative_contracts=derivatives_endpoints.derivative_contracts,
        quotes=cash_endpoints.quotes,
        candles=cash_endpoints.candles,
        derivative_history=derivatives_endpoints.derivative_history,
        resolve_derivative=derivatives_endpoints.resolve_derivative,
    )
