import pytest

from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
)
from data_layer.brokers.angelone.rest.smartapi.payloads import (
    CandleRequest,
    LtpRequest,
    QuoteRequest,
)
from data_layer.brokers.angelone.rest.smartapi.transport import (
    SmartApiTransport,
    SmartConnectAdapter,
)


def test_transport_delegates_market_data_calls() -> None:
    client = _Client()
    transport = SmartApiTransport(client)

    candle = transport.get_candles(
        CandleRequest("NSE", "3045", "ONE_MINUTE", "from", "to")
    )
    ltp = transport.get_ltp(LtpRequest("NSE", "SBIN-EQ", "3045"))
    quote = transport.get_quote(QuoteRequest("LTP", {"NSE": ["3045"]}))

    assert candle["status"] is True
    assert ltp["data"]["ltp"] == 1
    assert quote["status"] is True
    assert client.calls == [
        (
            "get_candle_data",
            {
                "exchange": "NSE",
                "symboltoken": "3045",
                "interval": "ONE_MINUTE",
                "fromdate": "from",
                "todate": "to",
            },
        ),
        ("ltp_data", "NSE", "SBIN-EQ", "3045"),
        ("get_market_data", "LTP", {"NSE": ["3045"]}),
    ]


def test_transport_rejects_failed_smartapi_response() -> None:
    client = _Client(ltp_response={"status": False, "message": "bad token"})
    transport = SmartApiTransport(client)

    with pytest.raises(AngelOneSmartApiRestBrokerError) as exc_info:
        transport.get_ltp(LtpRequest("NSE", "SBIN-EQ", "3045"))

    assert exc_info.value.is_auth_failure is True


def test_smart_connect_adapter_maps_camel_case_sdk_methods() -> None:
    raw_client = _RawClient()
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


class _Client:
    def __init__(self, ltp_response=None) -> None:
        self.calls = []
        self._ltp_response = ltp_response

    def get_candle_data(self, payload: dict) -> dict:
        self.calls.append(("get_candle_data", payload))
        return {"status": True, "data": []}

    def ltp_data(self, exchange: str, symbol: str, token: str) -> dict:
        self.calls.append(("ltp_data", exchange, symbol, token))
        return self._ltp_response or {"status": True, "data": {"ltp": 1}}

    def get_market_data(self, mode: str, tokens: dict) -> dict:
        self.calls.append(("get_market_data", mode, tokens))
        return {"status": True, "data": {}}


class _RawClient:
    def __init__(self) -> None:
        self.calls = []

    def generateSession(self, client_code: str, password: str, totp: str):
        self.calls.append(("generateSession", client_code, password, totp))
        return {"status": True, "data": {}}

    def terminateSession(self, client_code: str):
        self.calls.append(("terminateSession", client_code))
        return {"status": True, "data": {}}

    def getCandleData(self, payload: dict):
        self.calls.append(("getCandleData", payload))
        return {"status": True, "data": []}

    def getMarketData(self, mode: str, tokens: dict):
        self.calls.append(("getMarketData", mode, tokens))
        return {"status": True, "data": []}

    def ltpData(self, exchange: str, symbol: str, token: str):
        self.calls.append(("ltpData", exchange, symbol, token))
        return {"status": True, "data": {}}

    def getProfile(self):
        self.calls.append(("getProfile",))
        return {"status": True, "data": {}}

    def rmsLimit(self):
        self.calls.append(("rmsLimit",))
        return {"status": True, "data": {}}

    def holding(self):
        self.calls.append(("holding",))
        return {"status": True, "data": []}

    def position(self):
        self.calls.append(("position",))
        return {"status": True, "data": []}

    def orderBook(self):
        self.calls.append(("orderBook",))
        return {"status": True, "data": []}

    def tradeBook(self):
        self.calls.append(("tradeBook",))
        return {"status": True, "data": []}
