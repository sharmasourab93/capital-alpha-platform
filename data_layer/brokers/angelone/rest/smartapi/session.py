from __future__ import annotations

from dataclasses import dataclass

import pyotp
from SmartApi import SmartConnect

from ..errors import AngelOneSmartApiRestBrokerError


@dataclass(frozen=True)
class SmartApiCredentials:
    api_key: str
    client_code: str
    password: str
    totp_secret: str


class SmartApiSessionManager:
    def __init__(
        self,
        client: SmartConnect,
        credentials: SmartApiCredentials,
    ) -> None:
        self._client = client
        self._credentials = credentials
        self._session: dict | None = None

    @property
    def client(self) -> SmartConnect:
        return self._client

    @property
    def session(self) -> dict | None:
        return self._session

    def authenticate(self) -> dict:
        totp = pyotp.TOTP(self._credentials.totp_secret).now()
        session = self._client.generateSession(
            self._credentials.client_code,
            self._credentials.password,
            totp,
        )
        if not session or "data" not in session:
            raise AngelOneSmartApiRestBrokerError(
                "Angel One authentication returned invalid session",
                {"session": session},
            )
        self._session = session
        return session

    def ensure_authenticated(self) -> None:
        if self._session is None:
            self.authenticate()

    def terminate(self) -> dict | None:
        try:
            return self._client.terminateSession(self._credentials.client_code)
        except Exception:  # noqa: BLE001
            return None


__all__ = [
    "SmartApiCredentials",
    "SmartApiSessionManager",
]
