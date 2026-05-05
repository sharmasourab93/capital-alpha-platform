from __future__ import annotations

import base64
import json
from uuid import UUID

import pytest

from data_layer.data_modes.rest import handler


def test_lambda_handler_forwards_api_gateway_v2_event(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict = {}

    def fake_handle_http_request(**kwargs):
        captured.update(kwargs)
        return 200, {"data": {"status": "ok"}}

    monkeypatch.setattr(
        handler, "handle_http_request", fake_handle_http_request
    )

    event = {
        "headers": {"x-request-id": "header-request-id"},
        "rawPath": "/market/quotes",
        "requestContext": {
            "requestId": "context-request-id",
            "http": {"method": "POST"},
        },
        "queryStringParameters": {"provider": "angelone"},
        "body": json.dumps({"exchange": "NSE", "symbols": ["SBIN"]}),
    }

    response = handler.lambda_handler(event)

    assert captured == {
        "path": "/market/quotes",
        "method": "POST",
        "query": {"provider": "angelone"},
        "body": {"exchange": "NSE", "symbols": ["SBIN"]},
        "request_id": "header-request-id",
    }
    assert response["statusCode"] == 200
    assert response["headers"] == {"Content-Type": "application/json"}
    assert json.loads(response["body"]) == {"data": {"status": "ok"}}


def test_lambda_handler_falls_back_to_api_gateway_v1_fields(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict = {}

    def fake_handle_http_request(**kwargs):
        captured.update(kwargs)
        return 201, {"data": {"created": True}}

    monkeypatch.setattr(
        handler, "handle_http_request", fake_handle_http_request
    )

    event = {
        "path": "/market/candles",
        "httpMethod": "POST",
        "requestContext": {"requestId": "gateway-v1-request-id"},
        "queryStringParameters": None,
        "body": json.dumps({"exchange": "NSE", "symbol": "SBIN"}),
    }

    response = handler.lambda_handler(event)

    assert captured["path"] == "/market/candles"
    assert captured["method"] == "POST"
    assert captured["query"] == {}
    assert captured["body"] == {"exchange": "NSE", "symbol": "SBIN"}
    assert captured["request_id"] == "gateway-v1-request-id"
    assert response["statusCode"] == 201


def test_lambda_handler_generates_request_id_when_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict = {}

    def fake_handle_http_request(**kwargs):
        captured.update(kwargs)
        return 200, {"data": {"status": "ok"}}

    monkeypatch.setattr(
        handler, "handle_http_request", fake_handle_http_request
    )
    monkeypatch.setattr(
        handler, "uuid4", lambda: UUID("12345678-1234-5678-1234-567812345678")
    )

    response = handler.lambda_handler({"body": ""})

    assert captured["request_id"] == "12345678-1234-5678-1234-567812345678"
    assert captured["path"] == "/"
    assert captured["method"] == "GET"
    assert captured["query"] == {}
    assert captured["body"] == {}
    assert response["statusCode"] == 200


def test_lambda_handler_tolerates_none_headers_and_request_context(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict = {}

    def fake_handle_http_request(**kwargs):
        captured.update(kwargs)
        return 200, {"data": {"status": "ok"}}

    monkeypatch.setattr(
        handler, "handle_http_request", fake_handle_http_request
    )

    event = {
        "headers": None,
        "requestContext": None,
        "queryStringParameters": None,
        "body": None,
    }

    handler.lambda_handler(event)

    assert captured["path"] == "/"
    assert captured["method"] == "GET"
    assert captured["query"] == {}
    assert captured["body"] == {}


def test_lambda_handler_accepts_dict_body_without_json_decoding(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict = {}

    def fake_handle_http_request(**kwargs):
        captured.update(kwargs)
        return 200, {"data": {"status": "ok"}}

    monkeypatch.setattr(
        handler, "handle_http_request", fake_handle_http_request
    )

    event = {
        "body": {"exchange": "NSE", "symbols": ["SBIN"]},
    }

    handler.lambda_handler(event)

    assert captured["body"] == {"exchange": "NSE", "symbols": ["SBIN"]}


def test_lambda_handler_decodes_base64_encoded_json_body(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict = {}

    def fake_handle_http_request(**kwargs):
        captured.update(kwargs)
        return 200, {"data": {"status": "ok"}}

    monkeypatch.setattr(
        handler, "handle_http_request", fake_handle_http_request
    )

    event = {
        "isBase64Encoded": True,
        "body": base64.b64encode(
            json.dumps({"exchange": "NSE", "symbols": ["SBIN"]}).encode(
                "utf-8"
            )
        ).decode("utf-8"),
    }

    handler.lambda_handler(event)

    assert captured["body"] == {"exchange": "NSE", "symbols": ["SBIN"]}


def test_lambda_handler_treats_json_null_body_as_empty_dict(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict = {}

    def fake_handle_http_request(**kwargs):
        captured.update(kwargs)
        return 200, {"data": {"status": "ok"}}

    monkeypatch.setattr(
        handler, "handle_http_request", fake_handle_http_request
    )

    handler.lambda_handler({"body": "null"})

    assert captured["body"] == {}


def test_lambda_handler_rejects_non_object_json_body():
    with pytest.raises(ValueError, match="JSON object"):
        handler.lambda_handler({"body": json.dumps(["SBIN", "RELIANCE"])})
