"""HTTP transport for the data-layer client.

The transport deliberately uses the Python standard library. That keeps the
client lightweight for downstream applications and avoids coupling the package
to a long-lived HTTP session or a third-party dependency.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from data_client.auth import SigV4Signer
from data_client.exceptions import DataLayerHttpError


class HttpTransport:
    """Small stateless JSON transport.

    Each call builds and sends one request. The class stores only timeout
    configuration, so it is cheap to create and safe to share between endpoint
    wrappers without retaining request-specific state.
    """

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        """Create a transport with a per-request timeout."""
        self._timeout_seconds = timeout_seconds

    def request_json(
        self,
        method: str,
        url: str,
        *,
        json_body: dict[str, Any] | None = None,
        signer: SigV4Signer | None = None,
    ) -> Any:
        """Send a JSON request and return the parsed JSON response.

        Args:
            method: HTTP method.
            url: Fully resolved request URL.
            json_body: Optional JSON object to serialize as the request body.
            signer: Optional SigV4 signer for IAM-protected routes.

        Raises:
            DataLayerHttpError: For HTTP error responses and network failures.
        """
        body = _encode_body(json_body)
        headers = {"Accept": "application/json"}
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        if signer is not None:
            # Sign after the JSON body is encoded so the payload hash always
            # matches the bytes sent over the wire.
            headers = signer.sign(method, url, body=body, headers=headers)

        request = Request(
            url, data=body or None, headers=headers, method=method
        )
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                payload = _decode_body(response.read())
                if response.status >= 400:
                    raise DataLayerHttpError(response.status, payload)
                return payload
        except HTTPError as exc:
            raise DataLayerHttpError(
                exc.code, _decode_body(exc.read())
            ) from exc
        except URLError as exc:
            raise DataLayerHttpError(0, {"reason": str(exc.reason)}) from exc


def _encode_body(json_body: dict[str, Any] | None) -> bytes:
    """Serialize a request body with stable compact JSON formatting."""
    if json_body is None:
        return b""
    return json.dumps(json_body, separators=(",", ":")).encode("utf-8")


def _decode_body(body: bytes) -> Any:
    """Decode a response body as JSON, falling back to text."""
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return body.decode("utf-8", errors="replace")
