"""Tests for the AWS Lambda REST runtime entrypoint."""

import sys
from pathlib import Path
from types import ModuleType

_mangum_module = ModuleType("mangum")


class _Mangum:
    """Minimal Mangum test double for importing the Lambda handler module."""

    def __init__(self, app, **kwargs) -> None:
        """Store constructor inputs."""
        self.app = app
        self.kwargs = kwargs

    def __call__(self, event, context):
        """Return the event for simple wrapper tests."""
        return event


_mangum_module.Mangum = _Mangum
sys.modules.setdefault("mangum", _mangum_module)

from data_layer.runtimes.rest.lambda_handler import _without_stage_prefix


def test_lambda_handler_declares_expected_handler() -> None:
    """Verify the Lambda handler module exposes the expected symbols."""
    source = Path("data_layer/runtimes/rest/lambda_handler.py").read_text()

    assert "from mangum import Mangum" in source
    assert '_handler = Mangum(app, lifespan="off")' in source
    assert "def handler(" in source
    assert '__all__ = ["app", "handler"]' in source


def test_lambda_handler_removes_http_api_stage_prefix() -> None:
    """Verify HTTP API stage paths are normalized before FastAPI routing."""
    event = {
        "rawPath": "/dev/health",
        "path": "/dev/health",
        "requestContext": {
            "stage": "dev",
            "http": {
                "path": "/dev/health",
            },
        },
    }

    normalized = _without_stage_prefix(event)

    assert normalized["rawPath"] == "/health"
    assert normalized["path"] == "/health"
    assert normalized["requestContext"]["http"]["path"] == "/health"
    assert event["rawPath"] == "/dev/health"


def test_lambda_handler_keeps_default_stage_paths() -> None:
    """Verify default-stage events are left unchanged."""
    event = {
        "rawPath": "/health",
        "requestContext": {
            "stage": "$default",
            "http": {
                "path": "/health",
            },
        },
    }

    assert _without_stage_prefix(event) is event
