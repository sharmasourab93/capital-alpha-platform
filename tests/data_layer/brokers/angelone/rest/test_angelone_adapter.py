"""Tests for the AngelOne canonical REST adapter."""

import pytest
from data_layer.abstractions.instruments import BaseScripData

from data_layer.brokers.angelone.rest.angelone_adapter import (
    AngelOneRestAdapter,
)
from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
)
from data_layer.brokers.canonical.errors import BrokerOperationError
from data_layer.brokers.canonical.models import (
    AccountRequest,
    CandleRequest,
    LtpRequest,
    QuoteRequest,
    ScripListRequest,
    ScripRequest,
)


def test_adapter_maps_ltp_request_to_angelone_broker() -> None:
    """Verify LTP requests are translated to AngelRestBroker calls."""
    broker = _AngelBroker()
    adapter = AngelOneRestAdapter(broker)

    response = adapter.get_ltp(
        LtpRequest(broker="angelone", exchange="NSE", symbol="SBIN")
    )

    assert response.success is True
    assert response.data == {"ltp": 100}
    assert broker.calls == [("get_ltp", "NSE", "SBIN")]


def test_adapter_maps_quote_and_candle_requests() -> None:
    """Verify quote and candle requests preserve canonical fields."""
    broker = _AngelBroker()
    adapter = AngelOneRestAdapter(broker)

    quote = adapter.get_quote(
        QuoteRequest(
            broker="angelone",
            exchange="NSE",
            symbols=["SBIN", "RELIANCE"],
            mode="ltp",
        )
    )
    candles = adapter.get_candles(
        CandleRequest(
            broker="angelone",
            exchange="NSE",
            symbol="SBIN",
            interval="one_minute",
            from_time="2026-05-22 09:15",
            to_time="2026-05-22 09:20",
        )
    )

    assert quote.data == {"mode": "LTP"}
    assert candles.data == []
    assert broker.calls == [
        ("get_quote", "NSE", ["SBIN", "RELIANCE"], "LTP"),
        (
            "get_candles",
            "NSE",
            "SBIN",
            "ONE_MINUTE",
            "2026-05-22 09:15",
            "2026-05-22 09:20",
        ),
    ]


def test_adapter_maps_account_requests() -> None:
    """Verify account requests are translated to AngelRestBroker calls."""
    broker = _AngelBroker()
    adapter = AngelOneRestAdapter(broker)

    profile = adapter.get_profile(AccountRequest(broker="angelone"))
    funds = adapter.get_funds(AccountRequest(broker="angelone"))

    assert profile.data == {"name": "demo"}
    assert funds.data == {"cash": 100}
    assert broker.calls == [("get_profile",), ("get_funds",)]


def test_adapter_maps_scrip_requests() -> None:
    """Verify scrip lookup responses are canonicalized."""
    broker = _AngelBroker()
    adapter = AngelOneRestAdapter(broker)

    scrip = adapter.get_scrip(
        ScripRequest(broker="angelone", exchange="NSE", symbol="SBIN")
    )
    scrips = adapter.get_all_scrips(
        ScripListRequest(broker="angelone", exchange="NSE")
    )

    assert scrip.success is True
    assert scrip.data["symbol"] == "SBIN-EQ"
    assert scrips.data == ["NSE: SBIN"]


def test_adapter_returns_unsuccessful_response_for_missing_scrip() -> None:
    """Verify missing scrips return canonical not-found responses."""
    broker = _AngelBroker(missing_scrip=True)
    adapter = AngelOneRestAdapter(broker)

    response = adapter.get_scrip(
        ScripRequest(broker="angelone", exchange="NSE", symbol="MISSING")
    )

    assert response.success is False
    assert response.error_code == "SCRIP_NOT_FOUND"


def test_adapter_converts_angelone_errors_to_canonical_errors() -> None:
    """Verify AngelOne errors do not leak through the adapter."""
    broker = _AngelBroker(raise_error=True)
    adapter = AngelOneRestAdapter(broker)

    with pytest.raises(BrokerOperationError) as exc_info:
        adapter.get_ltp(
            LtpRequest(broker="angelone", exchange="NSE", symbol="SBIN")
        )

    assert exc_info.value.details["broker"] == "angelone"
    assert exc_info.value.details["operation"] == "get_ltp"


class _Scrip(BaseScripData):
    """Minimal scrip model for adapter tests."""

    @classmethod
    def from_row(cls, row):
        """Block row parsing in adapter tests."""
        raise NotImplementedError


class _AngelBroker:
    """Fake AngelRestBroker with the methods used by the adapter."""

    def __init__(
        self,
        *,
        missing_scrip: bool = False,
        raise_error: bool = False,
    ) -> None:
        """Store fake broker behavior."""
        self.calls = []
        self.missing_scrip = missing_scrip
        self.raise_error = raise_error

    def get_ltp(self, exchange: str, key: str) -> dict:
        """Return fake LTP data."""
        self._raise_if_needed()
        self.calls.append(("get_ltp", exchange, key))
        return {"status": True, "data": {"ltp": 100}}

    def get_quote(self, exchange: str, key: list[str], mode: str) -> dict:
        """Return fake quote data."""
        self.calls.append(("get_quote", exchange, key, mode))
        return {"status": True, "data": {"mode": mode}}

    def get_candles(
        self,
        exchange: str,
        key: str,
        interval: str,
        fromdate: str,
        todate: str,
    ) -> dict:
        """Return fake candle data."""
        self.calls.append(
            ("get_candles", exchange, key, interval, fromdate, todate)
        )
        return {"status": True, "data": []}

    def get_profile(self) -> dict:
        """Return fake profile data."""
        self.calls.append(("get_profile",))
        return {"status": True, "data": {"name": "demo"}}

    def get_funds(self) -> dict:
        """Return fake funds data."""
        self.calls.append(("get_funds",))
        return {"status": True, "data": {"cash": 100}}

    def get_holdings(self) -> dict:
        """Return fake holdings data."""
        self.calls.append(("get_holdings",))
        return {"status": True, "data": []}

    def get_positions(self) -> dict:
        """Return fake positions data."""
        self.calls.append(("get_positions",))
        return {"status": True, "data": []}

    def get_order_book(self) -> dict:
        """Return fake order book data."""
        self.calls.append(("get_order_book",))
        return {"status": True, "data": []}

    def get_trade_book(self) -> dict:
        """Return fake trade book data."""
        self.calls.append(("get_trade_book",))
        return {"status": True, "data": []}

    def get_scrip(self, exchange: str, key: str):
        """Return fake scrip data."""
        self.calls.append(("get_scrip", exchange, key))
        if self.missing_scrip:
            return None
        return _Scrip(
            exchange=exchange,
            token=3045,
            symbol="SBIN-EQ",
            name=key,
        )

    def get_all_scrips(self, exchange: str) -> list[str]:
        """Return fake scrip labels."""
        self.calls.append(("get_all_scrips", exchange))
        return [f"{exchange}: SBIN"]

    def _raise_if_needed(self) -> None:
        """Raise a fake AngelOne error when configured."""
        if self.raise_error:
            raise AngelOneSmartApiRestBrokerError(
                "AngelOne failed",
                {"response": {"status": False, "message": "bad token"}},
            )
