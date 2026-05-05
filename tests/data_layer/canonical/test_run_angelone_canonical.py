from __future__ import annotations

from argparse import Namespace

from data_layer.abs import BrokerResponse
from data_layer.canonical.run_angelone_canonical import (
    _run_command,
    build_derivative_request,
    normalize_response,
)


def test_normalize_response_maps_derivative_contracts_to_canonical_rows():
    response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_derivative_contracts",
        payload=[
            {
                "symbol": "BANKNIFTY29MAY202550000CE",
                "exchange": "NFO",
                "exchange_segment": "NFO",
                "instrument_type": "OPTIDX",
                "underlying": "BANKNIFTY",
                "expiry": "29MAY2025",
                "strike": 50000,
                "lot_size": 15,
                "option_type": "CE",
            }
        ],
        response_meta={},
    )

    normalized = normalize_response(response)

    assert normalized == [
        {
            "provider": "angelone",
            "exchange": "NFO",
            "symbol": "BANKNIFTY29MAY202550000CE",
            "broker_symbol": "BANKNIFTY29MAY202550000CE",
            "token": None,
            "name": "BANKNIFTY",
            "instrument_type": "OPTIDX",
            "underlying": "BANKNIFTY",
            "expiry": "29MAY2025",
            "strike": 50000.0,
            "option_type": "CE",
            "lot_size": 15,
            "exchange_segment": "NFO",
            "raw": {
                "symbol": "BANKNIFTY29MAY202550000CE",
                "exchange": "NFO",
                "exchange_segment": "NFO",
                "instrument_type": "OPTIDX",
                "underlying": "BANKNIFTY",
                "expiry": "29MAY2025",
                "strike": 50000,
                "lot_size": 15,
                "option_type": "CE",
            },
        }
    ]


def test_build_derivative_request_preserves_resolve_fields():
    args = Namespace(
        exchange="NFO",
        underlying="BANKNIFTY",
        instrument_type="OPTIDX",
        expiry="29MAY2025",
        strike=50000.0,
        option_type="CE",
    )

    requests = build_derivative_request(args)

    assert len(requests) == 1
    assert requests[0].exchange == "NFO"
    assert requests[0].underlying == "BANKNIFTY"
    assert requests[0].strike == 50000.0
    assert requests[0].option_type == "CE"


def test_run_command_derivative_history_resolves_then_fetches_candles():
    class _FakeBroker:
        def __init__(self) -> None:
            self.captured_candle_request = None

        def resolve_derivative_instruments(self, requests):
            return BrokerResponse(
                broker_name="angelone",
                operation="resolve_derivative_instruments",
                payload=[
                    {
                        "token": "50002",
                        "symbol": "BANKNIFTY29MAY202550000CE",
                    }
                ],
            )

        def fetch_candles(self, request):
            self.captured_candle_request = request
            return BrokerResponse(
                broker_name="angelone",
                operation="fetch_candles",
                payload={"status": True, "data": []},
                response_meta={"symbol": request.symbol},
            )

    broker = _FakeBroker()
    args = Namespace(
        command="derivative-history",
        exchange="NFO",
        underlying="BANKNIFTY",
        instrument_type="OPTIDX",
        expiry="29MAY2025",
        strike=50000.0,
        option_type="CE",
        interval="1d",
        from_date="2025-05-01 09:15",
        to_date="2025-05-10 15:30",
    )

    response = _run_command(broker, args)

    assert response.operation == "fetch_candles"
    assert broker.captured_candle_request is not None
    assert broker.captured_candle_request.instrument_token == "50002"
    assert broker.captured_candle_request.symbol == "BANKNIFTY29MAY202550000CE"


def test_normalize_response_output_can_be_timed_without_shape_changes():
    response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_derivative_expiries",
        payload=["29MAY2025"],
        response_meta={
            "exchange": "NFO",
            "underlying": "BANKNIFTY",
            "instrument_type": "OPTIDX",
        },
    )

    normalized = normalize_response(response)

    assert normalized[0]["expiry"] == "29MAY2025"
    assert normalized[0]["underlying"] == "BANKNIFTY"
