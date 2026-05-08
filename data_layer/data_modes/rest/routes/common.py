from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse

JsonResponseBuilder = Callable[..., JSONResponse]


@dataclass(frozen=True)
class RouterBundle:
    system_router: APIRouter
    reference_router: APIRouter
    cash_router: APIRouter
    derivatives_router: APIRouter
    health: Callable[..., JSONResponse]
    instruments: Callable[..., JSONResponse]
    exchanges: Callable[..., JSONResponse]
    instrument_types: Callable[..., JSONResponse]
    exchange_symbol_name_map: Callable[..., JSONResponse]
    nse_listed_stocks: Callable[..., JSONResponse]
    bse_listed_stocks: Callable[..., JSONResponse]
    derivative_symbols: Callable[..., JSONResponse]
    derivative_underlyings: Callable[..., JSONResponse]
    derivative_expiries: Callable[..., JSONResponse]
    derivative_strikes: Callable[..., JSONResponse]
    derivative_contracts: Callable[..., JSONResponse]
    quotes: Callable[..., JSONResponse]
    candles: Callable[..., JSONResponse]
    derivative_history: Callable[..., JSONResponse]
    resolve_derivative: Callable[..., JSONResponse]


def with_optional_values(
    base: dict[str, str],
    **optional_values: Optional[str],
) -> dict[str, str]:
    query = dict(base)
    for key, value in optional_values.items():
        if value is not None and value != "":
            query[key] = value
    return query
