"""FastAPI application factory for the REST runtime."""

from __future__ import annotations

from data_layer.runtimes.rest.errors import register_exception_handlers
from data_layer.runtimes.rest.middleware import register_request_logging
from data_layer.runtimes.rest.routes import include_routers
from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create the REST runtime app."""
    app = FastAPI(title="Capital Alpha Data Layer")
    register_exception_handlers(app)
    register_request_logging(app)
    include_routers(app)
    return app


app = create_app()


__all__ = ["app", "create_app"]
