"""AWS Lambda entrypoint for the FastAPI REST runtime."""

from __future__ import annotations

try:
    from mangum import Mangum
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "Mangum is required to run the REST runtime on AWS Lambda. "
        "Install the deployment dependency before using this handler."
    ) from exc

from data_layer.runtimes.rest.app import create_app

app = create_app()
handler = Mangum(app, lifespan="off")

__all__ = ["app", "handler"]
