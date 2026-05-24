"""Run the FastAPI REST runtime locally."""

from __future__ import annotations

import uvicorn

from data_layer.runtimes.rest.app import app
from data_layer.runtimes.rest.config import RestRuntimeSettings
from data_layer.runtimes.rest.log_config import configure_logging

APP_IMPORT_PATH = "data_layer.runtimes.rest.app:app"


def main() -> None:
    """Start the REST runtime."""
    settings = RestRuntimeSettings.from_env()
    configure_logging(settings.log_level)
    application = APP_IMPORT_PATH if settings.reload else app
    uvicorn.run(
        application,
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
