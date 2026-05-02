from __future__ import annotations

import json
from uuid import uuid4

from .http_core import handle_http_request


def lambda_handler(event: dict, context: object | None = None) -> dict:
    request_id = (
        event.get("headers", {}).get("x-request-id")
        or event.get("requestContext", {}).get("requestId")
        or str(uuid4())
    )
    path = event.get("rawPath") or event.get("path") or "/"
    method = (
        event.get("requestContext", {}).get("http", {}).get("method")
        or event.get("httpMethod")
        or "GET"
    )
    query = event.get("queryStringParameters") or {}
    status_code, payload = handle_http_request(
        path=path,
        method=method,
        query=query,
        request_id=request_id,
    )
    return _response(status_code, payload)


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
