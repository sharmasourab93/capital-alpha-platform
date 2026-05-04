from __future__ import annotations

import base64
import json
from uuid import uuid4

try:
    from .http_core import handle_http_request
except ImportError:  # pragma: no cover
    from http_core import handle_http_request


def lambda_handler(event: dict, context: object | None = None) -> dict:
    headers = _mapping_or_empty(event.get("headers"))
    request_context = _mapping_or_empty(event.get("requestContext"))
    request_context_http = _mapping_or_empty(request_context.get("http"))
    request_id = (
        headers.get("x-request-id")
        or request_context.get("requestId")
        or str(uuid4())
    )
    path = event.get("rawPath") or event.get("path") or "/"
    method = (
        request_context_http.get("method") or event.get("httpMethod") or "GET"
    )
    query = dict(event.get("queryStringParameters") or {})
    body = _decode_body(
        event.get("body"),
        is_base64_encoded=bool(event.get("isBase64Encoded")),
    )
    status_code, payload = handle_http_request(
        path=path,
        method=method,
        query=query,
        body=body,
        request_id=request_id,
    )
    return _response(status_code, payload)


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _mapping_or_empty(value) -> dict:
    return value if isinstance(value, dict) else {}


def _decode_body(raw_body, *, is_base64_encoded: bool) -> dict:
    if raw_body in (None, ""):
        return {}

    if isinstance(raw_body, dict):
        return raw_body

    if is_base64_encoded:
        raw_body = base64.b64decode(raw_body).decode("utf-8")

    parsed_body = json.loads(raw_body)
    if parsed_body is None:
        return {}
    if not isinstance(parsed_body, dict):
        raise ValueError("Lambda request body must decode to a JSON object")
    return parsed_body
