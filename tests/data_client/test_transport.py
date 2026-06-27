"""Tests for the stdlib HTTP transport."""

from __future__ import annotations

from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.request import Request

import pytest

from data_client.exceptions import DataLayerHttpError
from data_client.transport import HttpTransport


def test_transport_sends_compact_json_and_decodes_json_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify request body encoding, headers, timeout, and JSON decoding."""
    captured: dict[str, object] = {}

    def fake_urlopen(request: Request, timeout: float) -> _Response:
        captured["request"] = request
        captured["timeout"] = timeout
        return _Response(200, b'{"ok":true}')

    monkeypatch.setattr("data_client.transport.urlopen", fake_urlopen)

    payload = HttpTransport(timeout_seconds=3.5).request_json(
        "POST",
        "https://api.test/dev/market/angelone/NSE/quotes",
        json_body={"symbols": ["SBIN"], "mode": "LTP"},
    )

    request = captured["request"]
    assert isinstance(request, Request)
    assert captured["timeout"] == 3.5
    assert request.get_method() == "POST"
    assert request.data == b'{"symbols":["SBIN"],"mode":"LTP"}'
    assert request.get_header("Accept") == "application/json"
    assert request.get_header("Content-type") == "application/json"
    assert payload == {"ok": True}


def test_transport_signs_the_exact_encoded_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify SigV4 signing receives the bytes that will be sent."""
    signer = _Signer()

    def fake_urlopen(request: Request, timeout: float) -> _Response:
        return _Response(200, b"{}")

    monkeypatch.setattr("data_client.transport.urlopen", fake_urlopen)

    HttpTransport().request_json(
        "POST",
        "https://api.test/dev/market/angelone/NSE/quotes",
        json_body={"symbols": ["SBIN"], "mode": "LTP"},
        signer=signer,
    )

    assert signer.calls == [
        {
            "method": "POST",
            "url": "https://api.test/dev/market/angelone/NSE/quotes",
            "body": b'{"symbols":["SBIN"],"mode":"LTP"}',
            "headers": {
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        }
    ]


def test_transport_maps_http_error_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify API error responses retain status and parsed response body."""

    def fake_urlopen(request: Request, timeout: float) -> _Response:
        raise HTTPError(
            request.full_url,
            403,
            "Forbidden",
            hdrs=None,
            fp=BytesIO(b'{"detail":"forbidden"}'),
        )

    monkeypatch.setattr("data_client.transport.urlopen", fake_urlopen)

    with pytest.raises(DataLayerHttpError) as exc_info:
        HttpTransport().request_json(
            "GET", "https://api.test/dev/market/brokers"
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.payload == {"detail": "forbidden"}


def test_transport_maps_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify local network failures are surfaced as client HTTP errors."""

    def fake_urlopen(request: Request, timeout: float) -> _Response:
        raise URLError("timed out")

    monkeypatch.setattr("data_client.transport.urlopen", fake_urlopen)

    with pytest.raises(DataLayerHttpError) as exc_info:
        HttpTransport().request_json("GET", "https://api.test/dev/health")

    assert exc_info.value.status_code == 0
    assert exc_info.value.payload == {"reason": "timed out"}


class _Response:
    """Minimal urlopen response context manager for tests."""

    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self._body = body

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class _Signer:
    """Minimal signer spy used by transport tests."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def sign(
        self,
        method: str,
        url: str,
        *,
        body: bytes,
        headers: dict[str, str],
    ) -> dict[str, str]:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "body": body,
                "headers": headers,
            }
        )
        return {**headers, "Authorization": "signed"}
