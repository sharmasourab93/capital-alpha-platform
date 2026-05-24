"""REST route registration."""

from __future__ import annotations

from fastapi import FastAPI

from data_layer.runtimes.rest.routes import account, brokers, funda, health
from data_layer.runtimes.rest.routes import market


def include_routers(app: FastAPI) -> None:
    """Register all REST routers."""
    app.include_router(health.router)
    app.include_router(brokers.router)
    app.include_router(market.router)
    app.include_router(account.router)
    app.include_router(funda.router)
