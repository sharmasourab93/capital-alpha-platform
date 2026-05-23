from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import pyotp
from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
)


class SmartApiSessionClient(Protocol):
    def generate_session(
        self, client_code: str, password: str, totp: str
    ) -> dict[str, Any]: ...

    def terminate_session(self, client_code: str) -> dict[str, Any]: ...


TotpProvider = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class SmartApiCredentials:
    api_key: str
    client_code: str
    password: str
    totp_secret: str


def default_totp_provider(secret: str) -> str:
    return pyotp.TOTP(secret).now()


class AngelOneSessionManager:
    def __init__(
        self,
        client: SmartApiSessionClient,
        credentials: SmartApiCredentials,
        totp_provider: TotpProvider = default_totp_provider,
    ) -> None:
        self._client = client
        self._credentials = credentials
        self._totp_provider = totp_provider
        self._session: dict[str, Any] | None = None

    @property
    def session(self) -> dict[str, Any] | None:
        return self._session

    def authenticate(self) -> dict[str, Any]:
        session = self._client.generate_session(
            self._credentials.client_code,
            self._credentials.password,
            self._totp_provider(self._credentials.totp_secret),
        )
        self._validate_session(session)
        self._session = session
        return session

    def ensure_authenticated(self) -> None:
        if self._session is None:
            self.authenticate()

    def terminate(self) -> dict[str, Any]:
        try:
            response = self._client.terminate_session(
                self._credentials.client_code
            )
        except Exception as exc:
            raise AngelOneSmartApiRestBrokerError(
                "Angel One session termination failed",
                {"client_code": self._credentials.client_code},
            ) from exc

        self._session = None
        return response

    def _validate_session(self, session: dict[str, Any] | None) -> None:
        if not isinstance(session, dict) or not session.get("data"):
            raise AngelOneSmartApiRestBrokerError(
                "Angel One session was not authenticated",
                {"session": session},
            )

        if session.get("status") is False:
            raise AngelOneSmartApiRestBrokerError(
                "Angel One authentication failed",
                {"session": session},
            )


__all__ = [
    "AngelOneSessionManager",
    "SmartApiCredentials",
    "SmartApiSessionClient",
    "TotpProvider",
    "default_totp_provider",
]
