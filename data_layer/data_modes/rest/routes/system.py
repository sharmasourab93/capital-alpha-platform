from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from ..contracts.docs import HEALTH_DOC
from ..contracts.paths import HEALTH
from .common import JsonResponseBuilder


def build_system_router(
    json_response: JsonResponseBuilder,
) -> tuple[APIRouter, Callable[..., JSONResponse]]:
    router = APIRouter(tags=["system"])

    @router.get(
        HEALTH,
        summary=HEALTH_DOC.summary,
        description=HEALTH_DOC.description,
    )
    def health(request: Request) -> JSONResponse:
        return json_response(
            path=HEALTH,
            method="GET",
            request=request,
            query={},
            body={},
        )

    return router, health
