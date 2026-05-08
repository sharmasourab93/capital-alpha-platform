from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import JSONResponse

from ..api_models import (
    EXCHANGE_DESCRIPTION,
    INSTRUMENT_TYPE_DESCRIPTION,
    PROVIDER_DESCRIPTION,
    DerivativeHistoryRequest,
    DerivativeResolveRequest,
    model_dump,
)
from ..contracts import docs, paths
from .common import JsonResponseBuilder, with_optional_values


@dataclass(frozen=True)
class DerivativesEndpoints:
    derivative_symbols: Callable[..., JSONResponse]
    derivative_underlyings: Callable[..., JSONResponse]
    derivative_expiries: Callable[..., JSONResponse]
    derivative_strikes: Callable[..., JSONResponse]
    derivative_contracts: Callable[..., JSONResponse]
    derivative_history: Callable[..., JSONResponse]
    resolve_derivative: Callable[..., JSONResponse]


def build_derivatives_router(
    json_response: JsonResponseBuilder,
) -> tuple[APIRouter, DerivativesEndpoints]:
    router = APIRouter(tags=["derivatives"])

    @router.get(
        paths.DERIVATIVES_SYMBOLS,
        summary=docs.DERIVATIVES_SYMBOLS_DOC.summary,
        description=docs.DERIVATIVES_SYMBOLS_DOC.description,
    )
    def derivative_symbols(
        request: Request,
        provider: str = Query(
            ..., description=PROVIDER_DESCRIPTION, example="angelone"
        ),
        exchange: Optional[str] = Query(
            default=None,
            description=EXCHANGE_DESCRIPTION,
            example="NFO",
        ),
        instrument_type: Optional[str] = Query(
            default=None,
            description=INSTRUMENT_TYPE_DESCRIPTION,
            example="OPTIDX",
        ),
    ) -> JSONResponse:
        return json_response(
            path=paths.DERIVATIVES_SYMBOLS,
            method="GET",
            request=request,
            query=with_optional_values(
                {"provider": provider},
                exchange=exchange,
                instrument_type=instrument_type,
            ),
            body={},
        )

    @router.get(
        paths.DERIVATIVES_UNDERLYINGS,
        summary=docs.DERIVATIVES_UNDERLYINGS_DOC.summary,
        description=docs.DERIVATIVES_UNDERLYINGS_DOC.description,
    )
    def derivative_underlyings(
        request: Request,
        provider: str = Query(
            ..., description=PROVIDER_DESCRIPTION, example="angelone"
        ),
        exchange: Optional[str] = Query(
            default=None,
            description=EXCHANGE_DESCRIPTION,
            example="NFO",
        ),
        instrument_type: Optional[str] = Query(
            default=None,
            description=INSTRUMENT_TYPE_DESCRIPTION,
            example="OPTIDX",
        ),
    ) -> JSONResponse:
        return json_response(
            path=paths.DERIVATIVES_UNDERLYINGS,
            method="GET",
            request=request,
            query=with_optional_values(
                {"provider": provider},
                exchange=exchange,
                instrument_type=instrument_type,
            ),
            body={},
        )

    @router.get(
        paths.DERIVATIVES_EXPIRIES,
        summary=docs.DERIVATIVES_EXPIRIES_DOC.summary,
        description=docs.DERIVATIVES_EXPIRIES_DOC.description,
    )
    def derivative_expiries(
        request: Request,
        provider: str = Query(
            ..., description=PROVIDER_DESCRIPTION, example="angelone"
        ),
        exchange: str = Query(
            ..., description=EXCHANGE_DESCRIPTION, example="NFO"
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
        return json_response(
            path=paths.DERIVATIVES_EXPIRIES,
            method="GET",
            request=request,
            query={
                "provider": provider,
                "exchange": exchange,
                "underlying": underlying,
                "instrument_type": instrument_type,
            },
            body={},
        )

    @router.get(
        paths.DERIVATIVES_STRIKES,
        summary=docs.DERIVATIVES_STRIKES_DOC.summary,
        description=docs.DERIVATIVES_STRIKES_DOC.description,
    )
    def derivative_strikes(
        request: Request,
        provider: str = Query(
            ..., description=PROVIDER_DESCRIPTION, example="angelone"
        ),
        exchange: str = Query(
            ..., description=EXCHANGE_DESCRIPTION, example="NFO"
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
        option_type: Optional[str] = Query(
            default=None,
            description="Optional option side filter for option contracts.",
            example="CE",
        ),
    ) -> JSONResponse:
        return json_response(
            path=paths.DERIVATIVES_STRIKES,
            method="GET",
            request=request,
            query=with_optional_values(
                {
                    "provider": provider,
                    "exchange": exchange,
                    "underlying": underlying,
                    "instrument_type": instrument_type,
                    "expiry": expiry,
                },
                option_type=option_type,
            ),
            body={},
        )

    @router.get(
        paths.DERIVATIVES_CONTRACTS,
        summary=docs.DERIVATIVES_CONTRACTS_DOC.summary,
        description=docs.DERIVATIVES_CONTRACTS_DOC.description,
    )
    def derivative_contracts(
        request: Request,
        provider: str = Query(
            ..., description=PROVIDER_DESCRIPTION, example="angelone"
        ),
        exchange: str = Query(
            ..., description=EXCHANGE_DESCRIPTION, example="NFO"
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
        option_type: Optional[str] = Query(
            default=None,
            description="Optional option side filter for option contracts.",
            example="CE",
        ),
    ) -> JSONResponse:
        return json_response(
            path=paths.DERIVATIVES_CONTRACTS,
            method="GET",
            request=request,
            query=with_optional_values(
                {
                    "provider": provider,
                    "exchange": exchange,
                    "underlying": underlying,
                    "instrument_type": instrument_type,
                    "expiry": expiry,
                },
                option_type=option_type,
            ),
            body={},
        )

    @router.post(
        paths.DERIVATIVES_HISTORY,
        summary=docs.DERIVATIVES_HISTORY_DOC.summary,
        description=docs.DERIVATIVES_HISTORY_DOC.description,
    )
    def derivative_history(
        request: Request,
        payload: DerivativeHistoryRequest = Body(...),
    ) -> JSONResponse:
        return json_response(
            path=paths.DERIVATIVES_HISTORY,
            method="POST",
            request=request,
            query={},
            body=model_dump(payload),
        )

    @router.post(
        paths.DERIVATIVES_RESOLVE,
        summary=docs.DERIVATIVES_RESOLVE_DOC.summary,
        description=docs.DERIVATIVES_RESOLVE_DOC.description,
    )
    def resolve_derivative(
        request: Request,
        payload: DerivativeResolveRequest = Body(...),
    ) -> JSONResponse:
        return json_response(
            path=paths.DERIVATIVES_RESOLVE,
            method="POST",
            request=request,
            query={},
            body=model_dump(payload),
        )

    return router, DerivativesEndpoints(
        derivative_symbols=derivative_symbols,
        derivative_underlyings=derivative_underlyings,
        derivative_expiries=derivative_expiries,
        derivative_strikes=derivative_strikes,
        derivative_contracts=derivative_contracts,
        derivative_history=derivative_history,
        resolve_derivative=resolve_derivative,
    )
