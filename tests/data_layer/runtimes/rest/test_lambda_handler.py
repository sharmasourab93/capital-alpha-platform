"""Tests for the AWS Lambda REST runtime entrypoint."""

from pathlib import Path


def test_lambda_handler_declares_expected_handler() -> None:
    """Verify the Lambda handler module exposes the expected symbols."""
    source = Path("data_layer/runtimes/rest/lambda_handler.py").read_text()

    assert "from mangum import Mangum" in source
    assert "handler = Mangum(app)" in source
    assert '__all__ = ["app", "handler"]' in source
