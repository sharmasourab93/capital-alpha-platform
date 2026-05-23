"""Tests for AngelOne SmartAPI account operations."""

import pytest

from data_layer.brokers.angelone.rest.smartapi.account import (
    AngelOneAccountService,
)
from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
)


def test_account_service_delegates_all_account_operations() -> None:
    """Verify account service delegates every supported operation."""
    client = _AccountClient()
    service = AngelOneAccountService(client)

    assert service.get_profile()["data"]["clientcode"] == "client"
    assert service.get_funds()["data"]["net"] == "1000"
    assert service.get_holdings()["data"] == []
    assert service.get_positions()["data"] == []
    assert service.get_order_book()["data"] == []
    assert service.get_trade_book()["data"] == []

    assert client.calls == [
        "get_profile",
        "rms_limit",
        "holdings",
        "position",
        "order_book",
        "trade_book",
    ]


def test_account_service_rejects_failed_smartapi_response() -> None:
    """Verify failed SmartAPI responses raise broker errors."""
    client = _AccountClient(
        profile_response={"status": False, "message": "bad"}
    )
    service = AngelOneAccountService(client)

    with pytest.raises(AngelOneSmartApiRestBrokerError) as exc_info:
        service.get_profile()

    assert exc_info.value.details == {
        "response": {"status": False, "message": "bad"}
    }


def test_account_service_wraps_transport_exceptions() -> None:
    """Verify transport exceptions are normalized."""
    client = _AccountClient(profile_error=TimeoutError("request timed out"))
    service = AngelOneAccountService(client)

    with pytest.raises(AngelOneSmartApiRestBrokerError) as exc_info:
        service.get_profile()

    assert exc_info.value.details["reason"] == "request timed out"


class _AccountClient:
    """Fake SmartAPI account client."""

    def __init__(self, profile_response=None, profile_error=None) -> None:
        self.calls = []
        self._profile_response = profile_response
        self._profile_error = profile_error

    def get_profile(self) -> dict:
        self.calls.append("get_profile")
        if self._profile_error is not None:
            raise self._profile_error
        return self._profile_response or {
            "status": True,
            "data": {"clientcode": "client"},
        }

    def rms_limit(self) -> dict:
        self.calls.append("rms_limit")
        return {"status": True, "data": {"net": "1000"}}

    def holdings(self) -> dict:
        self.calls.append("holdings")
        return {"status": True, "data": []}

    def position(self) -> dict:
        self.calls.append("position")
        return {"status": True, "data": []}

    def order_book(self) -> dict:
        self.calls.append("order_book")
        return {"status": True, "data": []}

    def trade_book(self) -> dict:
        self.calls.append("trade_book")
        return {"status": True, "data": []}
