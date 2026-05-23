"""Tests for canonical broker request and response models."""

from dataclasses import FrozenInstanceError

import pytest

from data_layer.brokers.canonical.errors import BrokerValidationError
from data_layer.brokers.canonical.models import (
    AccountRequest,
    BrokerResponse,
    CandleRequest,
    LtpRequest,
    QuoteRequest,
    ScripListRequest,
    ScripRequest,
)


def test_account_request_normalizes_broker() -> None:
    """Verify account requests normalize broker names."""
    request = AccountRequest(broker=" angelone ")

    assert request.broker == "angelone"


def test_account_request_rejects_blank_broker() -> None:
    """Verify account requests require broker names."""
    with pytest.raises(BrokerValidationError) as exc_info:
        AccountRequest(broker=" ")

    assert exc_info.value.details == {"field": "broker"}


def test_account_request_rejects_non_string_broker() -> None:
    """Verify account requests reject non-string broker names."""
    with pytest.raises(BrokerValidationError) as exc_info:
        AccountRequest(broker=123)

    assert exc_info.value.details == {"field": "broker", "value": 123}


def test_scrip_request_normalizes_exchange_and_symbol() -> None:
    """Verify scrip requests normalize exchange and symbol."""
    request = ScripRequest(
        broker="angelone",
        exchange=" nse ",
        symbol=" SBIN ",
    )

    assert request.exchange == "NSE"
    assert request.symbol == "SBIN"


def test_scrip_list_request_defaults_and_normalizes_exchange() -> None:
    """Verify scrip-list requests default and normalize exchange."""
    default_request = ScripListRequest(broker="angelone")
    explicit_request = ScripListRequest(broker="angelone", exchange=" bse ")

    assert default_request.exchange == "NSE"
    assert explicit_request.exchange == "BSE"


def test_ltp_request_is_immutable_after_validation() -> None:
    """Verify canonical requests are immutable."""
    request = LtpRequest(broker="angelone", exchange="NSE", symbol="SBIN")

    with pytest.raises(FrozenInstanceError):
        request.symbol = "RELIANCE"


def test_quote_request_normalizes_inputs() -> None:
    """Verify quote requests normalize broker, exchange, symbols, and mode."""
    request = QuoteRequest(
        broker=" AngelOne ",
        exchange=" nse ",
        symbols=[" SBIN ", "RELIANCE"],
        mode="ltp",
    )

    assert request.broker == "AngelOne"
    assert request.exchange == "NSE"
    assert request.symbols == ("SBIN", "RELIANCE")
    assert request.mode == "LTP"


def test_quote_request_rejects_empty_symbols() -> None:
    """Verify quote requests require at least one symbol."""
    with pytest.raises(BrokerValidationError) as exc_info:
        QuoteRequest(broker="angelone", exchange="NSE", symbols=[])

    assert exc_info.value.details == {"field": "symbols"}


def test_quote_request_rejects_blank_symbol_member() -> None:
    """Verify quote requests reject blank symbols."""
    with pytest.raises(BrokerValidationError) as exc_info:
        QuoteRequest(
            broker="angelone",
            exchange="NSE",
            symbols=["SBIN", " "],
        )

    assert exc_info.value.details == {"field": "symbols"}


def test_quote_request_rejects_non_string_mode() -> None:
    """Verify quote requests reject non-string modes."""
    with pytest.raises(BrokerValidationError) as exc_info:
        QuoteRequest(
            broker="angelone",
            exchange="NSE",
            symbols=["SBIN"],
            mode=123,
        )

    assert exc_info.value.details == {"field": "mode", "value": 123}


def test_quote_request_rejects_unsupported_mode() -> None:
    """Verify quote requests reject unsupported modes."""
    with pytest.raises(BrokerValidationError) as exc_info:
        QuoteRequest(
            broker="angelone",
            exchange="NSE",
            symbols=["SBIN"],
            mode="DEPTH",
        )

    assert exc_info.value.details["field"] == "mode"


def test_candle_request_rejects_blank_required_fields() -> None:
    """Verify candle requests reject blank fields."""
    with pytest.raises(BrokerValidationError) as exc_info:
        CandleRequest(
            broker="angelone",
            exchange="NSE",
            symbol=" ",
            interval="ONE_MINUTE",
            from_time="2026-05-22 09:15",
            to_time="2026-05-22 09:20",
        )

    assert exc_info.value.details == {"field": "symbol"}


def test_candle_request_normalizes_interval_and_dates() -> None:
    """Verify candle requests normalize interval and trim dates."""
    request = CandleRequest(
        broker="angelone",
        exchange="nse",
        symbol="SBIN",
        interval=" one_minute ",
        from_time=" 2026-05-22 09:15 ",
        to_time=" 2026-05-22 09:20 ",
    )

    assert request.exchange == "NSE"
    assert request.interval == "ONE_MINUTE"
    assert request.from_time == "2026-05-22 09:15"
    assert request.to_time == "2026-05-22 09:20"


def test_response_normalizes_metadata() -> None:
    """Verify canonical responses normalize broker and operation."""
    response = BrokerResponse(
        broker=" angelone ",
        operation=" get_ltp ",
        success=True,
        data={},
    )

    assert response.broker == "angelone"
    assert response.operation == "get_ltp"


def test_response_requires_boolean_success() -> None:
    """Verify canonical responses require boolean success."""
    with pytest.raises(BrokerValidationError) as exc_info:
        BrokerResponse(
            broker="angelone",
            operation="get_ltp",
            success="true",
            data={},
        )

    assert exc_info.value.details["field"] == "success"
