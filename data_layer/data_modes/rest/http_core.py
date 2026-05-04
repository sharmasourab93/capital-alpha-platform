from __future__ import annotations

from time import perf_counter
from uuid import uuid4

try:
    from .router import RestRouter
except ImportError:  # pragma: no cover
    from router import RestRouter


_ROUTER = RestRouter()


def handle_http_request(
    *,
    path: str,
    method: str,
    query: dict[str, str] | None = None,
    body: dict | None = None,
    request_id: str | None = None,
) -> tuple[int, dict]:
    resolved_request_id = request_id or str(uuid4())
    started_at = perf_counter()

    try:
        status_code, payload = _ROUTER.handle(
            path=path,
            method=method,
            query=query or {},
            body=body or {},
            request_id=resolved_request_id,
        )
    except Exception as exc:  # noqa: BLE001
        status_code = 500
        details = getattr(exc, "details", [])
        if isinstance(details, dict):
            details = [details]
        payload = {
            "error": {
                "type": "REST_HANDLER_ERROR",
                "message": str(exc),
                "details": details,
            },
            "meta": {},
        }

    payload.setdefault("meta", {})
    payload["meta"]["request_id"] = resolved_request_id
    payload["meta"]["latency_ms"] = int((perf_counter() - started_at) * 1000)
    return status_code, payload
