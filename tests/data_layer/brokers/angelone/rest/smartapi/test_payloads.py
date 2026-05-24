"""Tests for SmartAPI payload builders."""

import pytest
from data_layer.abstractions.instruments import BaseScripData

from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
)
from data_layer.brokers.angelone.rest.smartapi.payloads import (
    CandleRequest,
    LtpRequest,
    QuoteRequest,
    validate_quote_mode,
)


def test_candle_request_builds_smartapi_payload() -> None:
    """Verify candle requests produce SmartAPI payload keys."""
    request = CandleRequest.from_scrip(
        _Scrip(exchange="NSE", token=3045, symbol="SBIN-EQ", name="SBIN"),
        "ONE_MINUTE",
        "2026-05-22 09:15",
        "2026-05-22 09:20",
    )

    assert request.to_payload() == {
        "exchange": "NSE",
        "symboltoken": "3045",
        "interval": "ONE_MINUTE",
        "fromdate": "2026-05-22 09:15",
        "todate": "2026-05-22 09:20",
    }


def test_ltp_request_uses_trading_symbol_and_token() -> None:
    """Verify LTP requests carry exchange, symbol, and token."""
    request = LtpRequest.from_scrip(
        _Scrip(exchange="NSE", token=3045, symbol="SBIN-EQ", name="SBIN")
    )

    assert request.exchange == "NSE"
    assert request.tradingsymbol == "SBIN-EQ"
    assert request.symboltoken == "3045"


def test_quote_request_uppercases_mode_and_groups_tokens() -> None:
    """Verify quote requests normalize mode and token grouping."""
    scrips = [
        _Scrip(exchange="NSE", token=3045, symbol="SBIN-EQ", name="SBIN"),
        _Scrip(
            exchange="NSE",
            token=2885,
            symbol="RELIANCE-EQ",
            name="RELIANCE",
        ),
    ]

    request = QuoteRequest.from_scrips("ltp", scrips)

    assert request.mode == "LTP"
    assert request.exchange_tokens == {"NSE": ["3045", "2885"]}


def test_invalid_quote_mode_raises_broker_error() -> None:
    """Verify unsupported quote modes raise broker errors."""
    with pytest.raises(AngelOneSmartApiRestBrokerError) as exc_info:
        validate_quote_mode("DEPTH")

    assert exc_info.value.details["mode"] == "DEPTH"


class _Scrip(BaseScripData):
    """Minimal scrip model for payload tests."""

    @classmethod
    def from_row(cls, row):
        """Block row parsing in payload-only tests."""
        raise NotImplementedError
