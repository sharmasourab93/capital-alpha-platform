from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AngelOneClientError(Exception):
    def __init__(
        self, message: str, details: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.details = details or {}


@dataclass(frozen=True)
class AngelOneCredentials:
    api_key: str
    jwt_token: str
    client_local_ip: str
    client_public_ip: str
    mac_address: str
    user_type: str = "USER"
    source_id: str = "WEB"


class AngelOneHttpClient:
    def __init__(
        self,
        credentials: AngelOneCredentials,
        base_url: str = "https://apiconnect.angelone.in",
        timeout_seconds: float = 10.0,
    ) -> None:
        self.credentials = credentials
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = "{0}{1}".format(self.base_url, path)
        request = Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise AngelOneClientError(
                "Angel One HTTP error",
                {"status_code": exc.code, "body": error_body[:500]},
            ) from exc
        except URLError as exc:
            raise AngelOneClientError(
                "Angel One connection error", {"reason": str(exc)}
            ) from exc

        try:
            parsed = json.loads(body) if body else {}
        except json.JSONDecodeError as exc:
            raise AngelOneClientError(
                "Angel One returned non-JSON payload", {"body": body[:500]}
            ) from exc

        if parsed.get("status") is False:
            raise AngelOneClientError(
                "Angel One returned an application error",
                {
                    "message": parsed.get("message"),
                    "errorcode": parsed.get("errorcode"),
                    "data": parsed.get("data"),
                },
            )

        return parsed

    def _headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer {0}".format(self.credentials.jwt_token),
            "X-PrivateKey": self.credentials.api_key,
            "X-UserType": self.credentials.user_type,
            "X-SourceID": self.credentials.source_id,
            "X-ClientLocalIP": self.credentials.client_local_ip,
            "X-ClientPublicIP": self.credentials.client_public_ip,
            "X-MACAddress": self.credentials.mac_address,
        }
