"""Tests for the public data-layer client."""

from __future__ import annotations

from typing import Any

import pytest

from data_client import DataLayerClient, DataLayerClientConfig
from data_client.auth import AwsCredentials
from data_client.exceptions import DataLayerClientConfigError


def test_config_builds_stage_url_from_api_parts() -> None:
    """Verify API Gateway URL construction from ID, region, and stage."""
    config = DataLayerClientConfig(
        api_id="abc123",
        region="us-east-2",
        stage="dev",
    )

    assert (
        config.url_for("/health")
        == "https://abc123.execute-api.us-east-2.amazonaws.com/dev/health"
    )


def test_config_prefers_explicit_base_url() -> None:
    """Verify explicit base URL wins over derived API URL."""
    config = DataLayerClientConfig(
        api_id="ignored",
        region="ap-south-2",
        stage="dev",
        base_url="https://example.test/dev/",
    )

    assert config.url_for("health") == "https://example.test/dev/health"


def test_config_requires_api_id_without_base_url() -> None:
    """Verify missing API ID fails fast."""
    config = DataLayerClientConfig()

    with pytest.raises(DataLayerClientConfigError):
        config.url_for("/health")


def test_from_env_can_build_public_health_client_without_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify public-route clients do not require AWS credentials."""
    monkeypatch.setenv("DATA_LAYER_API_BASE_URL", "https://api.test/dev")
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

    client = DataLayerClient.from_env(require_aws_credentials=False)

    assert client.config.resolved_base_url == "https://api.test/dev"


def test_health_is_unsigned_and_market_calls_are_signed() -> None:
    """Verify public and IAM-protected endpoint behavior."""
    transport = _Transport(
        {
            ("GET", "https://api.test/dev/health"): {"status": "ok"},
            ("GET", "https://api.test/dev/market/brokers"): {
                "brokers": ["angelone"]
            },
        }
    )
    client = DataLayerClient(
        DataLayerClientConfig(base_url="https://api.test/dev"),
        credentials=AwsCredentials("access", "secret"),
        transport=transport,
    )

    assert client.health() == {"status": "ok"}
    assert client.market.brokers() == ["angelone"]
    assert transport.calls[0]["signer"] is None
    assert transport.calls[1]["signer"] is not None


def test_root_brokers_maps_compatibility_endpoint() -> None:
    """Verify the root brokers helper maps to /brokers."""
    transport = _Transport(
        {
            ("GET", "https://api.test/dev/brokers"): {
                "brokers": [{"name": "angelone"}]
            },
        }
    )
    client = DataLayerClient(
        DataLayerClientConfig(base_url="https://api.test/dev"),
        credentials=AwsCredentials("access", "secret"),
        transport=transport,
    )

    assert client.brokers() == [{"name": "angelone"}]
    assert transport.calls[0]["url"] == "https://api.test/dev/brokers"


def test_market_methods_map_to_expected_paths_and_payloads() -> None:
    """Verify one-function-per-endpoint market methods."""
    transport = _Transport(
        {
            (
                "GET",
                "https://api.test/dev/market/angelone/NSE/intervals",
            ): {"intervals": [{"label": "1m", "value": "ONE_MINUTE"}]},
            (
                "GET",
                "https://api.test/dev/market/angelone/NSE/scrips",
            ): {"data": ["NSE: SBIN"]},
            (
                "GET",
                "https://api.test/dev/market/angelone/NSE/ltp?symbol=SBIN",
            ): {"data": {"ltp": 1}},
            (
                "POST",
                "https://api.test/dev/market/angelone/NSE/quotes",
            ): {"data": [{"symbol": "SBIN"}]},
            (
                "POST",
                "https://api.test/dev/market/angelone/NSE/candles",
            ): {"data": [[1, 2, 3]]},
        }
    )
    client = DataLayerClient(
        DataLayerClientConfig(base_url="https://api.test/dev"),
        credentials=AwsCredentials("access", "secret"),
        transport=transport,
    )

    assert client.market.intervals(broker="angelone", exchange="NSE") == [
        {"label": "1m", "value": "ONE_MINUTE"}
    ]
    assert client.market.scrips(broker="angelone", exchange="NSE") == [
        "NSE: SBIN"
    ]
    assert client.market.ltp(
        broker="angelone", exchange="NSE", symbol="SBIN"
    ) == {"ltp": 1}
    assert client.market.quotes(
        broker="angelone",
        exchange="NSE",
        symbols=["SBIN"],
        mode="LTP",
    ) == [{"symbol": "SBIN"}]
    assert client.market.candles(
        broker="angelone",
        exchange="NSE",
        symbol="SBIN",
        interval="ONE_MINUTE",
        from_time="2026-06-27 09:15",
        to_time="2026-06-27 09:30",
    ) == [[1, 2, 3]]

    assert transport.calls[3]["json_body"] == {
        "symbols": ["SBIN"],
        "mode": "LTP",
    }
    assert transport.calls[4]["json_body"] == {
        "symbol": "SBIN",
        "interval": "ONE_MINUTE",
        "from_time": "2026-06-27 09:15",
        "to_time": "2026-06-27 09:30",
    }


def test_ltp_list_symbols_are_sent_as_encoded_comma_query() -> None:
    """Verify list symbols map to the documented comma-separated query value."""
    transport = _Transport(
        {
            (
                "GET",
                "https://api.test/dev/market/angelone/NSE/ltp?symbol=SBIN%2CRELIANCE",
            ): {"data": [{"symbol": "SBIN"}, {"symbol": "RELIANCE"}]},
        }
    )
    client = DataLayerClient(
        DataLayerClientConfig(base_url="https://api.test/dev"),
        credentials=AwsCredentials("access", "secret"),
        transport=transport,
    )

    assert client.market.ltp(
        broker="angelone",
        exchange="NSE",
        symbol=["SBIN", "RELIANCE"],
    ) == [{"symbol": "SBIN"}, {"symbol": "RELIANCE"}]


def test_dataframe_output_is_optional() -> None:
    """Verify DataFrame conversion is opt-in per call."""
    transport = _Transport(
        {
            ("GET", "https://api.test/dev/market/brokers"): {
                "brokers": ["angelone", "zerodha"]
            },
        }
    )
    client = DataLayerClient(
        DataLayerClientConfig(base_url="https://api.test/dev"),
        credentials=AwsCredentials("access", "secret"),
        transport=transport,
    )

    frame = client.market.brokers(as_dataframe=True)

    assert list(frame.columns) == [0]
    assert frame[0].tolist() == ["angelone", "zerodha"]


def test_candle_dataframe_uses_named_columns_and_date_index() -> None:
    """Verify candle arrays become market-data DataFrames."""
    transport = _Transport(
        {
            (
                "POST",
                "https://api.test/dev/market/angelone/NSE/candles",
            ): {
                "data": [
                    [
                        "2026-06-26T09:15:00+05:30",
                        100.0,
                        101.0,
                        99.0,
                        100.5,
                        1000,
                    ]
                ]
            },
        }
    )
    client = DataLayerClient(
        DataLayerClientConfig(base_url="https://api.test/dev"),
        credentials=AwsCredentials("access", "secret"),
        transport=transport,
    )

    frame = client.market.candles(
        broker="angelone",
        exchange="NSE",
        symbol="SBIN",
        interval="ONE_MINUTE",
        from_time="2026-06-26 09:15",
        to_time="2026-06-26 09:30",
        as_dataframe=True,
    )

    assert frame.index.name == "date"
    assert frame.index.tolist() == ["2026-06-26 09:15"]
    assert list(frame.columns) == ["open", "high", "low", "close", "volume"]
    assert frame.iloc[0].to_dict() == {
        "open": 100.0,
        "high": 101.0,
        "low": 99.0,
        "close": 100.5,
        "volume": 1000.0,
    }


class _Transport:
    """Fake transport returning canned JSON payloads."""

    def __init__(self, responses: dict[tuple[str, str], Any]) -> None:
        self._responses = responses
        self.calls: list[dict[str, Any]] = []

    def request_json(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        signer: object | None = None,
    ) -> Any:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "json_body": json_body,
                "signer": signer,
            }
        )
        return self._responses[(method, url)]
