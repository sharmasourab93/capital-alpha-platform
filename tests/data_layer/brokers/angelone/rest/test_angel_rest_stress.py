from data_layer.brokers.angelone.rest.angel_instrument import AngelOneBroker
from data_layer.brokers.angelone.rest.angel_rest_broker import (
    AngelRestBroker,
    SmartApiCredentials,
)


def test_broker_handles_repeated_market_and_account_calls_with_one_session() -> (
    None
):
    client = _StressSmartApiClient()
    broker = _broker(client)

    for iteration in range(250):
        ltp = broker.get_ltp("NSE", "SBIN")
        assert ltp["data"]["ltp"] == 100

        if iteration % 5 == 0:
            quote = broker.get_quote("NSE", ["SBIN", "RELIANCE"], mode="ltp")
            assert quote["status"] is True

        if iteration % 10 == 0:
            candles = broker.get_candles(
                "NSE",
                "SBIN",
                "ONE_MINUTE",
                "2026-05-22 09:15",
                "2026-05-22 09:20",
            )
            assert candles["status"] is True

        if iteration % 25 == 0:
            profile = broker.get_profile()
            assert profile["data"]["name"] == "stress"

    assert client.call_count("generate_session") == 1
    assert client.call_count("ltp_data") == 250
    assert client.call_count("get_market_data") == 50
    assert client.call_count("get_candle_data") == 25
    assert client.call_count("get_profile") == 10


def test_broker_recovers_from_repeated_auth_failures_during_stress() -> None:
    client = _StressSmartApiClient(auth_failure_ltp_calls={1, 50, 100})
    broker = _broker(client)

    for _ in range(120):
        ltp = broker.get_ltp("NSE", "SBIN")
        assert ltp["data"]["ltp"] == 100

    assert client.call_count("generate_session") == 4
    assert client.call_count("ltp_data") == 123


def test_broker_lazily_loads_instruments_once_under_repeated_access(
    monkeypatch,
) -> None:
    client = _StressSmartApiClient()
    instruments = _instruments()
    load_calls = []

    def load_instruments() -> AngelOneBroker:
        load_calls.append("from_url")
        return instruments

    monkeypatch.setattr(AngelOneBroker, "from_url", load_instruments)
    broker = AngelRestBroker(
        credentials=_credentials(),
        client=client,
        totp_provider=lambda secret: "123456",
    )

    for _ in range(100):
        ltp = broker.get_ltp("NSE", "SBIN")
        assert ltp["data"]["ltp"] == 100

    assert load_calls == ["from_url"]
    assert client.call_count("generate_session") == 1
    assert client.call_count("ltp_data") == 100


def _broker(client: "_StressSmartApiClient") -> AngelRestBroker:
    return AngelRestBroker(
        credentials=_credentials(),
        client=client,
        instruments=_instruments(),
        totp_provider=lambda secret: "123456",
    )


def _credentials() -> SmartApiCredentials:
    return SmartApiCredentials(
        api_key="api-key",
        client_code="client",
        password="password",
        totp_secret="secret",
    )


def _instruments() -> AngelOneBroker:
    return AngelOneBroker.from_scrip_master_rows(
        [
            _row(token="3045", symbol="SBIN-EQ", name="SBIN"),
            _row(token="2885", symbol="RELIANCE-EQ", name="RELIANCE"),
        ]
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


class _StressSmartApiClient:
    def __init__(self, auth_failure_ltp_calls=None) -> None:
        self.calls = []
        self._ltp_calls = 0
        self._auth_failure_ltp_calls = set(auth_failure_ltp_calls or [])

    def call_count(self, method_name: str) -> int:
        return sum(call[0] == method_name for call in self.calls)

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
        return {"status": True, "data": {"mode": mode}}

    def ltp_data(
        self, exchange: str, tradingsymbol: str, symboltoken: str
    ) -> dict:
        self._ltp_calls += 1
        self.calls.append(("ltp_data", exchange, tradingsymbol, symboltoken))
        if self._ltp_calls in self._auth_failure_ltp_calls:
            return {"status": False, "message": "jwt token expired"}
        return {"status": True, "data": {"ltp": 100}}

    def get_profile(self) -> dict:
        self.calls.append(("get_profile",))
        return {"status": True, "data": {"name": "stress"}}

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
