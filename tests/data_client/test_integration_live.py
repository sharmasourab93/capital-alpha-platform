"""Opt-in live integration tests for the data-layer client.

These tests mirror ``data_client/example_usage.py`` but run through pytest.
They intentionally skip by default because they call the deployed API Gateway,
use IAM/SigV4 credentials, and may reach broker-backed data-layer services.

Run explicitly after setting:
    DATA_LAYER_RUN_INTEGRATION=1
    DATA_LAYER_API_BASE_URL
        or DATA_LAYER_API_ID, DATA_LAYER_AWS_REGION, DATA_LAYER_STAGE
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY
    AWS_SESSION_TOKEN, if using temporary credentials

Optional market overrides:
    DATA_LAYER_TEST_BROKER, default angelone
    DATA_LAYER_TEST_EXCHANGE, default NSE
    DATA_LAYER_TEST_SYMBOL, default SBIN
    DATA_LAYER_TEST_SYMBOLS, default SBIN,RELIANCE
    DATA_LAYER_TEST_INTERVAL, default ONE_MINUTE
    DATA_LAYER_TEST_FROM_TIME, default 2026-06-25 09:15
    DATA_LAYER_TEST_TO_TIME, default 2026-06-25 09:30
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import pytest

from data_client import DataLayerClient

RUN_INTEGRATION_ENV = "DATA_LAYER_RUN_INTEGRATION"


def test_live_health_endpoint_is_public() -> None:
    """Verify the deployed public health endpoint responds."""
    _skip_unless_live_enabled()
    _skip_unless_api_configured()
    client = DataLayerClient.from_env(require_aws_credentials=False)

    payload = client.health()

    assert payload is not None


def test_live_example_usage_discovery_calls() -> None:
    """Verify broker and market discovery calls from example_usage.py."""
    _skip_unless_live_enabled()
    _skip_unless_api_configured()
    _skip_unless_aws_credentials_configured()
    client = DataLayerClient.from_env()
    market = _market_settings()

    brokers = client.brokers()
    market_brokers = client.market.brokers()
    intervals = client.market.intervals(
        broker=market.broker,
        exchange=market.exchange,
    )
    scrips = client.market.scrips(
        broker=market.broker,
        exchange=market.exchange,
    )

    assert _has_payload(brokers)
    assert _has_payload(market_brokers)
    assert _has_payload(intervals)
    assert _has_payload(scrips)


def test_live_example_usage_market_data_calls() -> None:
    """Verify LTP, quotes, and candle calls from example_usage.py."""
    _skip_unless_live_enabled()
    _skip_unless_api_configured()
    _skip_unless_aws_credentials_configured()
    client = DataLayerClient.from_env()
    market = _market_settings()

    ltp = client.market.ltp(
        broker=market.broker,
        exchange=market.exchange,
        symbol=market.symbol,
    )
    multi_ltp = client.market.ltp(
        broker=market.broker,
        exchange=market.exchange,
        symbol=market.symbols,
    )
    quotes = client.market.quotes(
        broker=market.broker,
        exchange=market.exchange,
        symbols=market.symbols,
        mode="LTP",
    )
    candles = client.market.candles(
        broker=market.broker,
        exchange=market.exchange,
        symbol=market.symbol,
        interval=market.interval,
        from_time=market.from_time,
        to_time=market.to_time,
    )
    candle_frame = client.market.candles(
        broker=market.broker,
        exchange=market.exchange,
        symbol=market.symbol,
        interval=market.interval,
        from_time=market.from_time,
        to_time=market.to_time,
        as_dataframe=True,
    )

    assert _has_payload(ltp)
    assert _has_payload(multi_ltp)
    assert _has_payload(quotes)
    assert candles is not None
    assert list(candle_frame.columns) == [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]


@dataclass(frozen=True)
class _MarketSettings:
    """Market inputs used by the live smoke tests."""

    broker: str
    exchange: str
    symbol: str
    symbols: list[str]
    interval: str
    from_time: str
    to_time: str


def _market_settings() -> _MarketSettings:
    """Return market inputs with environment overrides."""
    symbols = [
        symbol.strip()
        for symbol in os.environ.get(
            "DATA_LAYER_TEST_SYMBOLS", "SBIN,RELIANCE"
        ).split(",")
        if symbol.strip()
    ]
    symbol = os.environ.get("DATA_LAYER_TEST_SYMBOL", symbols[0])
    return _MarketSettings(
        broker=os.environ.get("DATA_LAYER_TEST_BROKER", "angelone"),
        exchange=os.environ.get("DATA_LAYER_TEST_EXCHANGE", "NSE"),
        symbol=symbol,
        symbols=symbols,
        interval=os.environ.get("DATA_LAYER_TEST_INTERVAL", "ONE_MINUTE"),
        from_time=os.environ.get(
            "DATA_LAYER_TEST_FROM_TIME", "2026-06-25 09:15"
        ),
        to_time=os.environ.get("DATA_LAYER_TEST_TO_TIME", "2026-06-25 09:30"),
    )


def _skip_unless_live_enabled() -> None:
    """Skip unless the caller explicitly requested live API tests."""
    enabled = os.environ.get(RUN_INTEGRATION_ENV, "").strip().lower()
    if enabled not in {"1", "true", "yes"}:
        pytest.skip(
            f"set {RUN_INTEGRATION_ENV}=1 to run live data-layer tests"
        )


def _skip_unless_api_configured() -> None:
    """Skip when the API Gateway target is not configured."""
    if os.environ.get("DATA_LAYER_API_BASE_URL"):
        return
    if os.environ.get("DATA_LAYER_API_ID"):
        return
    pytest.skip("set DATA_LAYER_API_BASE_URL or DATA_LAYER_API_ID")


def _skip_unless_aws_credentials_configured() -> None:
    """Skip signed endpoint tests when AWS credentials are absent."""
    required = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        pytest.skip(f"missing AWS credential env vars: {', '.join(missing)}")


def _has_payload(payload: Any) -> bool:
    """Return whether a live endpoint returned a non-empty payload."""
    if payload is None:
        return False
    if isinstance(payload, (list, dict, str, tuple, set)):
        return bool(payload)
    return True
