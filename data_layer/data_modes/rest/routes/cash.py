from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import JSONResponse

from ..api_models import (
    PROVIDER_DESCRIPTION,
    CandlesRequest,
    QuotesRequest,
    model_dump,
)
from ..contracts import docs, paths
from .common import JsonResponseBuilder


@dataclass(frozen=True)
class CashEndpoints:
    nse_listed_stocks: Callable[..., JSONResponse]
    bse_listed_stocks: Callable[..., JSONResponse]
    quotes: Callable[..., JSONResponse]
    candles: Callable[..., JSONResponse]


def build_cash_router(
    json_response: JsonResponseBuilder,
) -> tuple[APIRouter, CashEndpoints]:
    router = APIRouter(tags=["cash"])

    @router.get(
        paths.CASH_NSE_LISTED_STOCKS,
        summary=docs.CASH_NSE_LISTED_STOCKS_DOC.summary,
        description=docs.CASH_NSE_LISTED_STOCKS_DOC.description,
    )
    def nse_listed_stocks(
        request: Request,
        provider: str = Query(
            ..., description=PROVIDER_DESCRIPTION, example="angelone"
        ),
        offset: int = Query(
            default=0,
            ge=0,
            description="Paging offset for NSE listed stock rows.",
            example=0,
        ),
        limit: int = Query(
            default=100,
            ge=1,
            le=500,
            description="Maximum number of NSE listed stock rows to return.",
            example=100,
        ),
    ) -> JSONResponse:
        return json_response(
            path=paths.CASH_NSE_LISTED_STOCKS,
            method="GET",
            request=request,
            query={
                "provider": provider,
                "offset": str(offset),
                "limit": str(limit),
            },
            body={},
        )

    @router.get(
        paths.CASH_BSE_LISTED_STOCKS,
        summary=docs.CASH_BSE_LISTED_STOCKS_DOC.summary,
        description=docs.CASH_BSE_LISTED_STOCKS_DOC.description,
    )
    def bse_listed_stocks(
        request: Request,
        provider: str = Query(
            ..., description=PROVIDER_DESCRIPTION, example="angelone"
        ),
        offset: int = Query(
            default=0,
            ge=0,
            description="Paging offset for BSE listed stock rows.",
            example=0,
        ),
        limit: int = Query(
            default=100,
            ge=1,
            le=500,
            description="Maximum number of BSE listed stock rows to return.",
            example=100,
        ),
    ) -> JSONResponse:
        return json_response(
            path=paths.CASH_BSE_LISTED_STOCKS,
            method="GET",
            request=request,
            query={
                "provider": provider,
                "offset": str(offset),
                "limit": str(limit),
            },
            body={},
        )

    @router.post(
        paths.CASH_QUOTES,
        summary=docs.CASH_QUOTES_DOC.summary,
        description=docs.CASH_QUOTES_DOC.description,
    )
    def quotes(
        request: Request,
        payload: QuotesRequest = Body(...),
    ) -> JSONResponse:
        return json_response(
            path=paths.CASH_QUOTES,
            method="POST",
            request=request,
            query={},
            body=model_dump(payload),
        )

    @router.post(
        paths.CASH_CANDLES,
        summary=docs.CASH_CANDLES_DOC.summary,
        description=docs.CASH_CANDLES_DOC.description,
    )
    def candles(
        request: Request,
        payload: CandlesRequest = Body(...),
    ) -> JSONResponse:
        return json_response(
            path=paths.CASH_CANDLES,
            method="POST",
            request=request,
            query={},
            body=model_dump(payload),
        )

    return router, CashEndpoints(
        nse_listed_stocks=nse_listed_stocks,
        bse_listed_stocks=bse_listed_stocks,
        quotes=quotes,
        candles=candles,
    )
