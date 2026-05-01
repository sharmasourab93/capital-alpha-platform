from __future__ import annotations

import json
from time import perf_counter
from uuid import uuid4

from .router import RestRouter


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
    started_at = perf_counter()

    try:
        status_code, payload = RestRouter().handle(
            path=path, method=method, query=query, request_id=request_id
        )
        payload.setdefault("meta", {})
        payload["meta"]["request_id"] = request_id
        payload["meta"]["latency_ms"] = int(
            (perf_counter() - started_at) * 1000
        )
        return _response(status_code, payload)
    except Exception as exc:  # noqa: BLE001
        return _response(
            500,
            {
                "error": {
                    "type": "REST_HANDLER_ERROR",
                    "message": str(exc),
                    "details": [],
                },
                "meta": {"request_id": request_id},
            },
        )


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
