"""Tests for data-layer client configuration."""

from __future__ import annotations

import pytest

from data_client.config import DataLayerClientConfig
from data_client.exceptions import DataLayerClientConfigError


def test_config_from_env_prefers_explicit_base_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify explicit base URL wins over API Gateway parts from env."""
    monkeypatch.setenv("DATA_LAYER_API_BASE_URL", "https://api.test/dev/")
    monkeypatch.setenv("DATA_LAYER_API_ID", "ignored")
    monkeypatch.setenv("DATA_LAYER_AWS_REGION", "ap-south-2")
    monkeypatch.setenv("DATA_LAYER_STAGE", "dev")
    monkeypatch.setenv("DATA_LAYER_TIMEOUT_SECONDS", "2.5")

    config = DataLayerClientConfig.from_env()

    assert config.resolved_base_url == "https://api.test/dev"
    assert config.timeout_seconds == 2.5


def test_config_from_env_uses_aws_region_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify AWS_REGION is accepted when client-specific region is absent."""
    monkeypatch.delenv("DATA_LAYER_API_BASE_URL", raising=False)
    monkeypatch.delenv("DATA_LAYER_AWS_REGION", raising=False)
    monkeypatch.setenv("DATA_LAYER_API_ID", "abc123")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("DATA_LAYER_STAGE", "prod")

    config = DataLayerClientConfig.from_env()

    assert (
        config.resolved_base_url
        == "https://abc123.execute-api.us-east-1.amazonaws.com/prod"
    )


def test_url_for_normalizes_paths_and_encodes_query() -> None:
    """Verify endpoint URL construction is stable for paths and query params."""
    config = DataLayerClientConfig(base_url="https://api.test/dev")

    assert (
        config.url_for("market/angelone/NSE/ltp", {"symbol": "SBIN,RELIANCE"})
        == "https://api.test/dev/market/angelone/NSE/ltp?symbol=SBIN%2CRELIANCE"
    )


def test_config_raises_without_base_url_or_api_id() -> None:
    """Verify invalid connection configuration fails before network calls."""
    config = DataLayerClientConfig()

    with pytest.raises(DataLayerClientConfigError, match="DATA_LAYER_API_ID"):
        _ = config.resolved_base_url
