from __future__ import annotations

import json
from types import SimpleNamespace

from data_layer.data_modes.rest import fastapi_app


def test_market_instruments_uses_simple_public_query_params(
    monkeypatch,
) -> None:
    captured: dict = {}

    def fake_handle_http_request(**kwargs):
        captured.update(kwargs)
        return 200, {"data": []}

    monkeypatch.setattr(
        fastapi_app,
        "handle_http_request",
        fake_handle_http_request,
    )
    request = SimpleNamespace(headers={"x-request-id": "req-123"})

    response = fastapi_app.instruments(
        request=request,
        provider="angelone",
        market="NSE",
        query_value="SBIN",
    )

    assert response.status_code == 200
    assert json.loads(response.body) == {"data": []}
    assert captured["path"] == "/market/instruments"
    assert captured["method"] == "GET"
    assert captured["query"] == {
        "provider": "angelone",
        "market": "NSE",
        "query": "SBIN",
    }
    assert captured["request_id"] == "req-123"


def test_derivative_expiries_forwards_expected_query_params(
    monkeypatch,
) -> None:
    captured: dict = {}

    def fake_handle_http_request(**kwargs):
        captured.update(kwargs)
        return 200, {"data": ["29MAY2025", "26JUN2025"]}

    monkeypatch.setattr(
        fastapi_app,
        "handle_http_request",
        fake_handle_http_request,
    )
    request = SimpleNamespace(headers={"x-request-id": "req-456"})

    response = fastapi_app.derivative_expiries(
        request=request,
        provider="angelone",
        exchange="NFO",
        underlying="BANKNIFTY",
        instrument_type="OPTIDX",
    )

    assert response.status_code == 200
    assert captured["path"] == "/market/derivative-expiries"
    assert captured["method"] == "GET"
    assert captured["query"] == {
        "provider": "angelone",
        "exchange": "NFO",
        "underlying": "BANKNIFTY",
        "instrument_type": "OPTIDX",
    }


def test_derivative_underlyings_forwards_expected_query_params(
    monkeypatch,
) -> None:
    captured: dict = {}

    def fake_handle_http_request(**kwargs):
        captured.update(kwargs)
        return 200, {"data": {"NFO": {"OPTIDX": ["BANKNIFTY"]}}}

    monkeypatch.setattr(
        fastapi_app,
        "handle_http_request",
        fake_handle_http_request,
    )
    request = SimpleNamespace(headers={"x-request-id": "req-789"})

    response = fastapi_app.derivative_underlyings(
        request=request,
        provider="angelone",
        exchange="NFO",
        instrument_type="OPTIDX",
    )

    assert response.status_code == 200
    assert captured["path"] == "/market/derivative-underlyings"
    assert captured["method"] == "GET"
    assert captured["query"] == {
        "provider": "angelone",
        "exchange": "NFO",
        "instrument_type": "OPTIDX",
    }


def test_derivative_strikes_forwards_expected_query_params(
    monkeypatch,
) -> None:
    captured: dict = {}

    def fake_handle_http_request(**kwargs):
        captured.update(kwargs)
        return 200, {"data": [50000, 51000]}

    monkeypatch.setattr(
        fastapi_app,
        "handle_http_request",
        fake_handle_http_request,
    )
    request = SimpleNamespace(headers={"x-request-id": "req-790"})

    response = fastapi_app.derivative_strikes(
        request=request,
        provider="angelone",
        exchange="NFO",
        underlying="BANKNIFTY",
        instrument_type="OPTIDX",
        expiry="26MAY2026",
        option_type="CE",
    )

    assert response.status_code == 200
    assert captured["path"] == "/market/derivative-strikes"
    assert captured["method"] == "GET"
    assert captured["query"] == {
        "provider": "angelone",
        "exchange": "NFO",
        "underlying": "BANKNIFTY",
        "instrument_type": "OPTIDX",
        "expiry": "26MAY2026",
        "option_type": "CE",
    }


def test_derivative_contracts_forwards_expected_query_params(
    monkeypatch,
) -> None:
    captured: dict = {}

    def fake_handle_http_request(**kwargs):
        captured.update(kwargs)
        return 200, {"data": []}

    monkeypatch.setattr(
        fastapi_app,
        "handle_http_request",
        fake_handle_http_request,
    )
    request = SimpleNamespace(headers={"x-request-id": "req-901"})

    response = fastapi_app.derivative_contracts(
        request=request,
        provider="angelone",
        exchange="NFO",
        underlying="BANKNIFTY",
        instrument_type="OPTIDX",
        expiry="26MAY2026",
        option_type="CE",
    )

    assert response.status_code == 200
    assert captured["path"] == "/market/derivative-contracts"
    assert captured["query"] == {
        "provider": "angelone",
        "exchange": "NFO",
        "underlying": "BANKNIFTY",
        "instrument_type": "OPTIDX",
        "expiry": "26MAY2026",
        "option_type": "CE",
    }


def test_derivative_history_forwards_expected_body(
    monkeypatch,
) -> None:
    captured: dict = {}

    def fake_handle_http_request(**kwargs):
        captured.update(kwargs)
        return 200, {"data": []}

    monkeypatch.setattr(
        fastapi_app,
        "handle_http_request",
        fake_handle_http_request,
    )
    request = SimpleNamespace(headers={"x-request-id": "req-902"})

    response = fastapi_app.derivative_history(
        request=request,
        payload=fastapi_app.DerivativeHistoryRequest.model_validate(
            {
                "provider": "angelone",
                "exchange": "NFO",
                "underlying": "BANKNIFTY",
                "instrument_type": "OPTIDX",
                "expiry": "26MAY2026",
                "strike": 43000,
                "option_type": "CE",
                "interval": "1d",
                "from": "2026-05-01 09:15",
                "to": "2026-05-04 15:30",
            }
        ),
    )

    assert response.status_code == 200
    assert captured["path"] == "/market/derivatives/history"
    assert captured["method"] == "POST"
    assert captured["body"] == {
        "provider": "angelone",
        "exchange": "NFO",
        "underlying": "BANKNIFTY",
        "instrument_type": "OPTIDX",
        "expiry": "26MAY2026",
        "strike": 43000.0,
        "option_type": "CE",
        "interval": "1d",
        "from": "2026-05-01 09:15",
        "to": "2026-05-04 15:30",
    }
