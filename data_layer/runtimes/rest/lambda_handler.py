"""AWS Lambda entrypoint for the FastAPI REST runtime."""

from __future__ import annotations

from typing import Any

try:
    from mangum import Mangum
except ImportError as exc:  # pragma: no cover
    raise RuntimeError(
        "Mangum is required to run the REST runtime on AWS Lambda. "
        "Install the deployment dependency before using this handler."
    ) from exc

from data_layer.runtimes.rest.app import create_app

app = create_app()
_handler = Mangum(app, lifespan="off")


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Normalize API Gateway stage paths before dispatching to FastAPI."""
    return _handler(_without_stage_prefix(event), context)


def _without_stage_prefix(event: dict[str, Any]) -> dict[str, Any]:
    """Remove HTTP API stage prefix from paths when API Gateway includes it."""
    request_context = event.get("requestContext")
    if not isinstance(request_context, dict):
        return event

    stage = request_context.get("stage")
    if not isinstance(stage, str) or not stage or stage == "$default":
        return event

    stage_prefix = f"/{stage}"
    normalized_event = dict(event)

    for key in ("rawPath", "path"):
        value = normalized_event.get(key)
        if isinstance(value, str) and value.startswith(stage_prefix):
            normalized_event[key] = value.removeprefix(stage_prefix) or "/"

    http_context = request_context.get("http")
    if isinstance(http_context, dict):
        normalized_request_context = dict(request_context)
        normalized_http_context = dict(http_context)
        value = normalized_http_context.get("path")
        if isinstance(value, str) and value.startswith(stage_prefix):
            normalized_http_context["path"] = (
                value.removeprefix(stage_prefix) or "/"
            )
        normalized_request_context["http"] = normalized_http_context
        normalized_event["requestContext"] = normalized_request_context

    return normalized_event


__all__ = ["app", "handler"]
