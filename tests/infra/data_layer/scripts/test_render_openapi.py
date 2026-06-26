"""Tests for data-layer OpenAPI rendering."""

from __future__ import annotations

import yaml
from pathlib import Path

from infra.data_layer.scripts.render_openapi import render_openapi


def test_render_openapi_excludes_disabled_paths_by_default(tmp_path) -> None:
    """Verify disabled paths are not rendered unless enabled."""
    output_path = tmp_path / "rendered.yaml"

    render_openapi(
        source_path=_source_openapi_path(),
        output_path=output_path,
        lambda_invoke_uri=_lambda_invoke_uri(),
    )

    document = yaml.safe_load(output_path.read_text())
    paths = set(document["paths"])

    assert "/health" in paths
    assert "/market/{broker}/{exchange}/ltp" in paths
    assert "/account/{broker}/profile" not in paths
    assert "/account/{broker}/funds" not in paths
    assert "/funda/{market}" not in paths
    assert _does_not_contain_marker(document, "x-capital-alpha-enabled")
    assert _does_not_contain_marker(document, "x-capital-alpha-group")
    assert _does_not_contain_marker(document, "__LAMBDA_INVOKE_URI__")
    assert "security" not in document["paths"]["/health"]["get"]
    assert document["paths"]["/market/brokers"]["get"]["security"] == [{"sigv4": []}]


def test_render_openapi_includes_enabled_path_groups(tmp_path) -> None:
    """Verify account and fundamentals paths can be rendered explicitly."""
    output_path = tmp_path / "rendered.yaml"

    render_openapi(
        source_path=_source_openapi_path(),
        output_path=output_path,
        lambda_invoke_uri=_lambda_invoke_uri(),
        enable_account=True,
        enable_fundamentals=True,
    )

    document = yaml.safe_load(output_path.read_text())
    paths = set(document["paths"])

    assert "/account/{broker}/profile" in paths
    assert "/account/{broker}/funds" in paths
    assert "/account/{broker}/holdings" in paths
    assert "/account/{broker}/positions" in paths
    assert "/account/{broker}/orders" in paths
    assert "/account/{broker}/trades" in paths
    assert "/funda/{market}" in paths


def _source_openapi_path():
    """Return the source OpenAPI path."""
    return Path("data_layer/data-layer-rest.openapi.yaml")


def _lambda_invoke_uri() -> str:
    """Return a fake Lambda invoke URI."""
    return (
        "arn:aws:apigateway:ap-south-2:lambda:path/2015-03-31/functions/"
        "arn:aws:lambda:ap-south-2:123456789012:function:test/invocations"
    )


def _does_not_contain_marker(value, marker: str) -> bool:
    """Return whether a nested YAML value contains a marker."""
    if isinstance(value, dict):
        return all(
            key != marker and _does_not_contain_marker(child, marker)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return all(_does_not_contain_marker(child, marker) for child in value)
    if isinstance(value, str):
        return marker not in value
    return True
