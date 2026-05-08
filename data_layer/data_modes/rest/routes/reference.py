from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from ..api_models import EXCHANGE_DESCRIPTION, PROVIDER_DESCRIPTION
from ..contracts import docs, paths
from .common import JsonResponseBuilder, with_optional_values


@dataclass(frozen=True)
class ReferenceEndpoints:
    instruments: Callable[..., JSONResponse]
    exchanges: Callable[..., JSONResponse]
    instrument_types: Callable[..., JSONResponse]
    exchange_symbol_name_map: Callable[..., JSONResponse]


def build_reference_router(
    json_response: JsonResponseBuilder,
) -> tuple[APIRouter, ReferenceEndpoints]:
    router = APIRouter(tags=["reference"])

    @router.get(
        paths.REFERENCE_INSTRUMENTS,
        summary=docs.REFERENCE_INSTRUMENTS_DOC.summary,
        description=docs.REFERENCE_INSTRUMENTS_DOC.description,
    )
    def instruments(
        request: Request,
        provider: str = Query(
            ..., description=PROVIDER_DESCRIPTION, example="angelone"
        ),
        market: str = Query(
            ...,
            description=(
                "Market/exchange to search in. Common values: `NSE`, `BSE`, "
                "`NFO`, `BFO`, `CDS`, `MCX`."
            ),
            example="NSE",
        ),
        query_value: str = Query(
            ...,
            alias="query",
            description=(
                "Symbol or name search term, e.g. `SBIN`, `RELIANCE`, "
                "`BANKNIFTY`."
            ),
            example="SBIN",
        ),
    ) -> JSONResponse:
        return json_response(
            path=paths.REFERENCE_INSTRUMENTS,
            method="GET",
            request=request,
            query={
                "provider": provider,
                "market": market,
                "query": query_value,
            },
            body={},
        )

    @router.get(
        paths.REFERENCE_EXCHANGES,
        summary=docs.REFERENCE_EXCHANGES_DOC.summary,
        description=docs.REFERENCE_EXCHANGES_DOC.description,
    )
    def exchanges(
        request: Request,
        provider: str = Query(
            ..., description=PROVIDER_DESCRIPTION, example="angelone"
        ),
    ) -> JSONResponse:
        return json_response(
            path=paths.REFERENCE_EXCHANGES,
            method="GET",
            request=request,
            query={"provider": provider},
            body={},
        )

    @router.get(
        paths.REFERENCE_INSTRUMENT_TYPES,
        summary=docs.REFERENCE_INSTRUMENT_TYPES_DOC.summary,
        description=docs.REFERENCE_INSTRUMENT_TYPES_DOC.description,
    )
    def instrument_types(
        request: Request,
        provider: str = Query(
            ..., description=PROVIDER_DESCRIPTION, example="angelone"
        ),
        exchange: Optional[str] = Query(
            default=None,
            description=EXCHANGE_DESCRIPTION,
            example="NFO",
        ),
    ) -> JSONResponse:
        return json_response(
            path=paths.REFERENCE_INSTRUMENT_TYPES,
            method="GET",
            request=request,
            query=with_optional_values(
                {"provider": provider}, exchange=exchange
            ),
            body={},
        )

    @router.get(
        paths.REFERENCE_EXCHANGE_SYMBOL_NAME_MAP,
        summary=docs.REFERENCE_EXCHANGE_SYMBOL_NAME_MAP_DOC.summary,
        description=docs.REFERENCE_EXCHANGE_SYMBOL_NAME_MAP_DOC.description,
    )
    def exchange_symbol_name_map(
        request: Request,
        provider: str = Query(
            ..., description=PROVIDER_DESCRIPTION, example="angelone"
        ),
        exchange: Optional[str] = Query(
            default=None,
            description=(
                "Optional exchange filter. When omitted, the endpoint returns "
                "a compact per-exchange summary."
            ),
            example="NSE",
        ),
        query_value: Optional[str] = Query(
            default=None,
            alias="query",
            description=(
                "Optional symbol/name search term applied only when `exchange` "
                "is provided."
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
            description=(
                "Maximum number of symbol rows to return for an "
                "exchange-scoped listing."
            ),
            example=100,
        ),
    ) -> JSONResponse:
        query = with_optional_values(
            {"provider": provider},
            exchange=exchange,
            query=query_value,
        )
        if exchange or offset != 0:
            query["offset"] = str(offset)
        if exchange or limit != 100:
            query["limit"] = str(limit)

        return json_response(
            path=paths.REFERENCE_EXCHANGE_SYMBOL_NAME_MAP,
            method="GET",
            request=request,
            query=query,
            body={},
        )

    return router, ReferenceEndpoints(
        instruments=instruments,
        exchanges=exchanges,
        instrument_types=instrument_types,
        exchange_symbol_name_map=exchange_symbol_name_map,
    )
