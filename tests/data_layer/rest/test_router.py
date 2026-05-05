from __future__ import annotations

from data_layer.abs import BrokerResponse
from data_layer.data_modes.rest.router import RestRouter


class _FakeBroker:
    broker_name = "angelone"

    def __init__(self) -> None:
        self.captured_candle_request = None

    def resolve_derivative_instruments(self, requests, context=None):
        return BrokerResponse(
            broker_name="angelone",
            operation="resolve_derivative_instruments",
            payload=[
                {
                    "token": "50002",
                    "symbol": "BANKNIFTY29MAY202550000CE",
                    "exchange": "NFO",
                }
            ],
        )

    def fetch_candles(self, request, context=None):
        self.captured_candle_request = request
        return BrokerResponse(
            broker_name="angelone",
            operation="fetch_candles",
            payload={"status": True, "data": []},
            response_meta={
                "exchange": request.exchange,
                "interval": request.interval,
                "instrument_token": request.instrument_token,
                "symbol": request.symbol,
            },
        )


def test_router_derivative_history_resolves_contract_then_fetches_candles():
    router = RestRouter()
    fake_broker = _FakeBroker()
    router._resolve_broker = lambda name: fake_broker  # type: ignore[method-assign]

    status_code, payload = router.handle(
        path="/market/derivatives/history",
        method="POST",
        query={},
        body={
            "provider": "angelone",
            "exchange": "NFO",
            "underlying": "BANKNIFTY",
            "instrument_type": "OPTIDX",
            "expiry": "29MAY2025",
            "strike": 50000,
            "option_type": "CE",
            "interval": "1d",
            "from": "2025-05-01 09:15",
            "to": "2025-05-10 15:30",
        },
        request_id="req-1",
    )

    assert status_code == 200
    assert payload["data"] == {"status": True, "data": []}
    assert payload["meta"]["response_meta"]["router_elapsed_ms"] >= 0
    assert fake_broker.captured_candle_request is not None
    assert fake_broker.captured_candle_request.instrument_token == "50002"
    assert (
        fake_broker.captured_candle_request.symbol
        == "BANKNIFTY29MAY202550000CE"
    )


def test_router_removed_derivative_tokens_route_returns_not_found():
    router = RestRouter()

    status_code, payload = router.handle(
        path="/market/derivatives/tokens",
        method="POST",
        query={},
        body={"provider": "angelone"},
        request_id="req-2",
    )

    assert status_code == 404
    assert payload["error"]["type"] == "NOT_FOUND"


def test_router_derivative_strikes_forwards_expected_query_params():
    class _DerivativeStrikesBroker:
        broker_name = "angelone"

        def fetch_derivative_strikes(self, **kwargs):
            assert kwargs["exchange"] == "NFO"
            assert kwargs["underlying"] == "BANKNIFTY"
            assert kwargs["instrument_type"] == "OPTIDX"
            assert kwargs["expiry"] == "29MAY2025"
            assert kwargs["option_type"] == "CE"
            return BrokerResponse(
                broker_name="angelone",
                operation="fetch_derivative_strikes",
                payload=(50000.0, 51000.0),
                response_meta={"strike_count": 2},
            )

    router = RestRouter()
    router._resolve_broker = lambda name: _DerivativeStrikesBroker()  # type: ignore[method-assign]

    status_code, payload = router.handle(
        path="/market/derivative-strikes",
        method="GET",
        query={
            "provider": "angelone",
            "exchange": "NFO",
            "underlying": "BANKNIFTY",
            "instrument_type": "OPTIDX",
            "expiry": "29MAY2025",
            "option_type": "CE",
        },
        body={},
        request_id="req-3",
    )

    assert status_code == 200
    assert payload["data"] == (50000.0, 51000.0)
    assert payload["meta"]["operation"] == "fetch_derivative_strikes"
