from __future__ import annotations

import importlib
import sys
import types
from unittest.mock import Mock

import pytest

from data_layer.brokers.angelone.rest.instrument_master import (
    AngelInstrumentMaster,
)


@pytest.fixture
def sample_equity_rows() -> list[dict]:
    return [
        {
            "token": "3045",
            "symbol": "SBIN-EQ",
            "name": "STATE BANK OF INDIA",
            "exch_seg": "NSE",
            "instrumenttype": "EQ",
            "expiry": "",
            "strike": "",
            "lotsize": "1",
        },
        {
            "token": "2885",
            "symbol": "RELIANCE-EQ",
            "name": "RELIANCE INDUSTRIES",
            "exch_seg": "NSE",
            "instrumenttype": "EQ",
            "expiry": "",
            "strike": "",
            "lotsize": "1",
        },
        {
            "token": "16713",
            "symbol": "UBL-EQ",
            "name": "UNITED BREWERIES",
            "exch_seg": "NSE",
            "instrumenttype": "EQ",
            "expiry": "",
            "strike": "",
            "lotsize": "1",
        },
    ]


@pytest.fixture
def sample_equity_rows_with_ambiguity(
    sample_equity_rows: list[dict],
) -> list[dict]:
    return sample_equity_rows + [
        {
            "token": "93045",
            "symbol": "SBIN",
            "name": "STATE BANK OF INDIA",
            "exch_seg": "NSE",
            "instrumenttype": "EQ",
            "expiry": "",
            "strike": "",
            "lotsize": "1",
        },
        {
            "token": "93046",
            "symbol": "SBIN",
            "name": "STATE BANK OF INDIA",
            "exch_seg": "NSE",
            "instrumenttype": "EQ",
            "expiry": "",
            "strike": "",
            "lotsize": "1",
        },
    ]


@pytest.fixture
def sample_derivative_rows() -> list[dict]:
    return [
        {
            "token": "50001",
            "symbol": "BANKNIFTY29MAY2025FUT",
            "name": "BANKNIFTY",
            "exch_seg": "NFO",
            "instrumenttype": "FUTIDX",
            "expiry": "29MAY2025",
            "strike": "",
            "lotsize": "15",
        },
        {
            "token": "50002",
            "symbol": "BANKNIFTY29MAY202550000CE",
            "name": "BANKNIFTY",
            "exch_seg": "NFO",
            "instrumenttype": "OPTIDX",
            "expiry": "29MAY2025",
            "strike": "5000000",
            "lotsize": "15",
        },
        {
            "token": "50003",
            "symbol": "BANKNIFTY29MAY202550000PE",
            "name": "BANKNIFTY",
            "exch_seg": "NFO",
            "instrumenttype": "OPTIDX",
            "expiry": "29MAY2025",
            "strike": "5000000",
            "lotsize": "15",
        },
        {
            "token": "50004",
            "symbol": "BANKNIFTY26JUN202550000CE",
            "name": "BANKNIFTY",
            "exch_seg": "NFO",
            "instrumenttype": "OPTIDX",
            "expiry": "26JUN2025",
            "strike": "5000000",
            "lotsize": "15",
        },
        {
            "token": "50005",
            "symbol": "BANKNIFTY29MAY202551000CE",
            "name": "BANKNIFTY",
            "exch_seg": "NFO",
            "instrumenttype": "OPTIDX",
            "expiry": "29MAY2025",
            "strike": "5100000",
            "lotsize": "15",
        },
        {
            "token": "60001",
            "symbol": "RELIANCE29MAY2025FUT",
            "name": "RELIANCE",
            "exch_seg": "NFO",
            "instrumenttype": "FUTSTK",
            "expiry": "29MAY2025",
            "strike": "",
            "lotsize": "250",
        },
        {
            "token": "60002",
            "symbol": "RELIANCE29MAY20251400CE",
            "name": "RELIANCE",
            "exch_seg": "NFO",
            "instrumenttype": "OPTSTK",
            "expiry": "29MAY2025",
            "strike": "140000",
            "lotsize": "250",
        },
    ]


@pytest.fixture
def sample_scrip_master_rows(
    sample_equity_rows: list[dict],
    sample_derivative_rows: list[dict],
) -> list[dict]:
    return sample_equity_rows + sample_derivative_rows


@pytest.fixture
def instrument_master(
    sample_scrip_master_rows: list[dict],
) -> AngelInstrumentMaster:
    return AngelInstrumentMaster.from_rows(sample_scrip_master_rows)


@pytest.fixture
def authenticated_session_payload() -> dict:
    return {
        "status": True,
        "data": {
            "jwtToken": "jwt-token",
            "refreshToken": "refresh-token",
        },
    }


@pytest.fixture
def ltp_market_data_response() -> dict:
    return {
        "status": True,
        "message": "SUCCESS",
        "errorcode": "",
        "data": [
            {
                "exchange": "NSE",
                "tradingSymbol": "SBIN-EQ",
                "symbolToken": "3045",
                "ltp": 812.35,
            }
        ],
    }


@pytest.fixture
def fake_runtime_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    pyotp_module = types.ModuleType("pyotp")

    class FakeTOTP:
        def __init__(self, secret: str) -> None:
            self.secret = secret

        def now(self) -> str:
            return "123456"

    pyotp_module.TOTP = FakeTOTP

    smartapi_module = types.ModuleType("SmartApi")

    class FakeSmartConnect:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

    smartapi_module.SmartConnect = FakeSmartConnect

    monkeypatch.setitem(sys.modules, "pyotp", pyotp_module)
    monkeypatch.setitem(sys.modules, "SmartApi", smartapi_module)


@pytest.fixture
def broker_module(
    fake_runtime_modules: None,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("ANGELONE_API_KEY", "test-api-key")
    monkeypatch.setenv("ANGELONE_CLIENTCODE", "test-client")
    monkeypatch.setenv("ANGELONE_PASSWORD", "test-password")
    monkeypatch.setenv("ANGELONE_TOTP_SECRET", "test-totp-secret")

    module_name = "data_layer.brokers.angelone.rest.smartapi_rest_broker"
    if module_name in sys.modules:
        del sys.modules[module_name]

    return importlib.import_module(module_name)


@pytest.fixture
def mock_client(authenticated_session_payload: dict) -> Mock:
    client = Mock()
    client.generateSession.return_value = authenticated_session_payload
    client.terminateSession.return_value = {"status": True}
    return client
