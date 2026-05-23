"""Tests for the AngelOne REST broker facade."""

import pytest

from data_layer.brokers.angelone.rest.angel_instrument import AngelOneBroker
from data_layer.brokers.angelone.rest.angel_rest_broker import (
    AngelRestBroker,
    SmartAPICredentials,
    SmartApiCredentials,
)
from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
    RetryConfig,
    call_smart_api,
)
from data_layer.brokers.angelone.rest.smartapi.transport import (
    SmartConnectAdapter,
    default_smart_api_client_factory,
)


def test_public_imports_and_aliases_are_stable() -> None:
    """Verify public SmartAPI imports and aliases remain stable."""
    from data_layer.brokers.angelone.rest.smartapi import (
        SmartApiCredentials as PackageCredentials,
    )

    assert SmartAPICredentials is SmartApiCredentials
    assert PackageCredentials is SmartApiCredentials
    assert callable(default_smart_api_client_factory)


def test_broker_construction_does_not_load_instruments_from_network(
    monkeypatch,
) -> None:
    """Ensure broker construction does not fetch instruments eagerly."""

    def fail_from_url():
        raise AssertionError("from_url should be lazy")

    monkeypatch.setattr(AngelOneBroker, "from_url", fail_from_url)

    broker = AngelRestBroker(
        credentials=_credentials(),
        client=_SmartApiClientStub(),
        totp_provider=lambda secret: "123456",
    )

    assert broker.session is None


def test_broker_lazily_loads_instruments_when_needed(monkeypatch) -> None:
    """Ensure instrument data is loaded only on first lookup."""
    instruments = AngelOneBroker.from_scrip_master_rows(
        [_row(token="3045", symbol="SBIN-EQ", name="SBIN")]
    )
    calls = []

    def load_from_url():
        calls.append("from_url")
        return instruments

    monkeypatch.setattr(AngelOneBroker, "from_url", load_from_url)
    broker = AngelRestBroker(
        credentials=_credentials(),
        client=_SmartApiClientStub(),
        totp_provider=lambda secret: "123456",
    )

    scrip = broker.get_scrip("NSE", "SBIN")

    assert calls == ["from_url"]
    assert scrip is not None
    assert scrip.token == 3045


def test_market_data_call_authenticates_once_and_reuses_session() -> None:
    """Verify market-data calls reuse one authenticated session."""
    client = _SmartApiClientStub()
    broker = _broker(client)

    ltp = broker.get_ltp("NSE", "SBIN")
    quote = broker.get_quote("NSE", ["SBIN"], mode="ltp")
    candles = broker.get_candles(
        "NSE",
        "SBIN",
        "ONE_MINUTE",
        "2026-05-22 09:15",
        "2026-05-22 09:20",
    )

    assert ltp["data"]["ltp"] == 1
    assert quote["status"] is True
    assert candles["status"] is True
    assert client.calls[0] == (
        "generate_session",
        "client",
        "password",
        "123456",
    )
    assert [call[0] for call in client.calls].count("generate_session") == 1
    assert ("ltp_data", "NSE", "SBIN-EQ", "3045") in client.calls
    assert ("get_market_data", "LTP", {"NSE": ["3045"]}) in client.calls


def test_account_call_authenticates_and_delegates_to_account_service() -> None:
    """Verify account calls authenticate once and delegate correctly."""
    client = _SmartApiClientStub()
    broker = _broker(client)

    profile = broker.get_profile()
    funds = broker.get_funds()
    holdings = broker.get_holdings()
    positions = broker.get_positions()
    order_book = broker.get_order_book()
    trade_book = broker.get_trade_book()

    assert profile["data"]["name"] == "demo"
    assert funds["data"]["cash"] == 1
    assert holdings["data"] == []
    assert positions["data"] == []
    assert order_book["data"] == []
    assert trade_book["data"] == []
    assert [call[0] for call in client.calls] == [
        "generate_session",
        "get_profile",
        "rms_limit",
        "holdings",
        "position",
        "order_book",
        "trade_book",
    ]


def test_auth_failure_refreshes_session_once_then_retries_operation() -> None:
    """Verify auth failures trigger one refresh and one retry."""
    client = _SmartApiClientStub()
    client.ltp_auth_failure_once = True
    broker = _broker(client)

    ltp = broker.get_ltp("NSE", "SBIN")

    assert ltp["data"]["ltp"] == 1
    assert [call[0] for call in client.calls] == [
        "generate_session",
        "ltp_data",
        "generate_session",
        "ltp_data",
    ]


def test_non_auth_failure_does_not_refresh_session() -> None:
    """Ensure non-auth failures do not refresh the session."""
    client = _SmartApiClientStub()
    client.ltp_failure_response = {
        "status": False,
        "status_code": 400,
        "message": "invalid request",
    }
    broker = _broker(client)

    with pytest.raises(AngelOneSmartApiRestBrokerError):
        broker.get_ltp("NSE", "SBIN")

    assert [call[0] for call in client.calls] == [
        "generate_session",
        "ltp_data",
    ]


def test_retry_handles_transient_failed_response_without_sleep() -> None:
    """Verify transient SmartAPI responses are retried."""
    calls = []

    def transient_operation():
        calls.append("attempt")
        if len(calls) == 1:
            return {
                "status": False,
                "status_code": 503,
                "message": "temporarily unavailable",
            }
        return {"status": True, "data": []}

    response = call_smart_api(
        "transient failure",
        transient_operation,
        retry_config=RetryConfig(max_attempts=2, initial_delay_seconds=0),
    )

    assert response == {"status": True, "data": []}
    assert calls == ["attempt", "attempt"]


def test_retry_does_not_retry_auth_failures() -> None:
    """Verify auth failures are not retried by generic retry logic."""
    calls = []

    def auth_failure():
        calls.append("attempt")
        return {"status": False, "message": "jwt token expired"}

    with pytest.raises(AngelOneSmartApiRestBrokerError):
        call_smart_api(
            "auth failure",
            auth_failure,
            retry_config=RetryConfig(max_attempts=3, initial_delay_seconds=0),
        )

    assert calls == ["attempt"]


def test_smart_connect_adapter_maps_snake_case_to_sdk_camel_case() -> None:
    """Verify the SmartConnect adapter maps SDK method names."""
    raw_client = _RawSmartConnectStub()
    adapter = SmartConnectAdapter(raw_client)

    adapter.generate_session("client", "password", "123456")
    adapter.terminate_session("client")
    adapter.get_candle_data({"exchange": "NSE"})
    adapter.get_market_data("LTP", {"NSE": ["3045"]})
    adapter.ltp_data("NSE", "SBIN-EQ", "3045")
    adapter.get_profile()
    adapter.rms_limit()
    adapter.holdings()
    adapter.position()
    adapter.order_book()
    adapter.trade_book()

    assert raw_client.calls == [
        ("generateSession", "client", "password", "123456"),
        ("terminateSession", "client"),
        ("getCandleData", {"exchange": "NSE"}),
        ("getMarketData", "LTP", {"NSE": ["3045"]}),
        ("ltpData", "NSE", "SBIN-EQ", "3045"),
        ("getProfile",),
        ("rmsLimit",),
        ("holding",),
        ("position",),
        ("orderBook",),
        ("tradeBook",),
    ]


def test_logout_clears_session_state() -> None:
    """Verify logout clears the stored SmartAPI session."""
    client = _SmartApiClientStub()
    broker = _broker(client)

    broker.login()
    assert broker.session is not None

    response = broker.logout()

    assert response["status"] is True
    assert broker.session is None
    assert client.calls[-1] == ("terminate_session", "client")


def _broker(client: "_SmartApiClientStub") -> AngelRestBroker:
    """Create a broker with deterministic fake dependencies."""
    return AngelRestBroker(
        credentials=_credentials(),
        client=client,
        instruments=AngelOneBroker.from_scrip_master_rows(
            [_row(token="3045", symbol="SBIN-EQ", name="SBIN")]
        ),
        totp_provider=lambda secret: "123456",
    )


def _credentials() -> SmartApiCredentials:
    """Return deterministic SmartAPI credentials for tests."""
    return SmartApiCredentials(
        api_key="api-key",
        client_code="client",
        password="password",
        totp_secret="secret",
    )


def _row(
    *,
    token: str,
    symbol: str,
    name: str,
    exchange: str = "NSE",
    instrument_type: str = "",
    tick_size: str = "5",
) -> dict[str, str]:
    """Return a minimal AngelOne scrip-master row."""
    return {
        "token": token,
        "symbol": symbol,
        "name": name,
        "expiry": "",
        "strike": "-1.000000",
        "lotsize": "1",
        "instrumenttype": instrument_type,
        "exch_seg": exchange,
        "tick_size": tick_size,
    }


class _SmartApiClientStub:
    """Fake SmartAPI client used by broker facade tests."""

    def __init__(self) -> None:
        self.calls = []
        self.ltp_auth_failure_once = False
        self.ltp_failure_response = None
        self._ltp_calls = 0

    def generate_session(
        self, client_code: str, password: str, totp: str
    ) -> dict:
        self.calls.append(("generate_session", client_code, password, totp))
        return {"status": True, "data": {"jwtToken": "token"}}

    def terminate_session(self, client_code: str) -> dict:
        self.calls.append(("terminate_session", client_code))
        return {"status": True, "data": {}}

    def get_candle_data(self, historic_data_params: dict) -> dict:
        self.calls.append(("get_candle_data", historic_data_params))
        return {"status": True, "data": []}

    def get_market_data(self, mode: str, exchange_tokens: dict) -> dict:
        self.calls.append(("get_market_data", mode, exchange_tokens))
        return {"status": True, "data": {}}

    def ltp_data(
        self, exchange: str, tradingsymbol: str, symboltoken: str
    ) -> dict:
        self._ltp_calls += 1
        self.calls.append(("ltp_data", exchange, tradingsymbol, symboltoken))
        if self.ltp_auth_failure_once and self._ltp_calls == 1:
            return {"status": False, "message": "jwt token expired"}
        if self.ltp_failure_response is not None:
            return self.ltp_failure_response
        return {"status": True, "data": {"ltp": 1}}

    def get_profile(self) -> dict:
        self.calls.append(("get_profile",))
        return {"status": True, "data": {"name": "demo"}}

    def rms_limit(self) -> dict:
        self.calls.append(("rms_limit",))
        return {"status": True, "data": {"cash": 1}}

    def holdings(self) -> dict:
        self.calls.append(("holdings",))
        return {"status": True, "data": []}

    def position(self) -> dict:
        self.calls.append(("position",))
        return {"status": True, "data": []}

    def order_book(self) -> dict:
        self.calls.append(("order_book",))
        return {"status": True, "data": []}

    def trade_book(self) -> dict:
        self.calls.append(("trade_book",))
        return {"status": True, "data": []}


class _RawSmartConnectStub:
    """Fake camelCase SmartConnect SDK client."""

    def __init__(self) -> None:
        self.calls = []

    def generateSession(
        self, client_code: str, password: str, totp: str
    ) -> dict:
        self.calls.append(("generateSession", client_code, password, totp))
        return {"status": True, "data": {}}

    def terminateSession(self, client_code: str) -> dict:
        self.calls.append(("terminateSession", client_code))
        return {"status": True, "data": {}}

    def getCandleData(self, payload: dict) -> dict:
        self.calls.append(("getCandleData", payload))
        return {"status": True, "data": []}

    def getMarketData(self, mode: str, tokens: dict) -> dict:
        self.calls.append(("getMarketData", mode, tokens))
        return {"status": True, "data": []}

    def ltpData(self, exchange: str, symbol: str, token: str) -> dict:
        self.calls.append(("ltpData", exchange, symbol, token))
        return {"status": True, "data": {}}

    def getProfile(self) -> dict:
        self.calls.append(("getProfile",))
        return {"status": True, "data": {}}

    def rmsLimit(self) -> dict:
        self.calls.append(("rmsLimit",))
        return {"status": True, "data": {}}

    def holding(self) -> dict:
        self.calls.append(("holding",))
        return {"status": True, "data": []}

    def position(self) -> dict:
        self.calls.append(("position",))
        return {"status": True, "data": []}

    def orderBook(self) -> dict:
        self.calls.append(("orderBook",))
        return {"status": True, "data": []}

    def tradeBook(self) -> dict:
        self.calls.append(("tradeBook",))
        return {"status": True, "data": []}
