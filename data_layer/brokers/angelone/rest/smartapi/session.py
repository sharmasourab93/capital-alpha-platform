"""AngelOne SmartAPI session management."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import pyotp

from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
    smart_api_error_handler,
    validate_smart_api_response,
)


class SmartApiSessionClient(Protocol):
    """SmartAPI session methods used by AngelOneSessionManager."""

    def generate_session(
        self, client_code: str, password: str, totp: str
    ) -> dict[str, Any]:
        """Create a SmartAPI session."""
        ...

    def terminate_session(self, client_code: str) -> dict[str, Any]:
        """Terminate a SmartAPI session."""
        ...


TotpProvider = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class SmartApiCredentials:
    """Credentials required for AngelOne SmartAPI authentication."""

    api_key: str
    client_code: str
    password: str
    totp_secret: str


def default_totp_provider(secret: str) -> str:
    """Return the current TOTP for the provided secret."""
    return pyotp.TOTP(secret).now()


class AngelOneSessionManager:
    """Own the lifecycle of one AngelOne SmartAPI session."""

    def __init__(
        self,
        client: SmartApiSessionClient,
        credentials: SmartApiCredentials,
        totp_provider: TotpProvider = default_totp_provider,
    ) -> None:
        """Create a session manager around a SmartAPI client."""
        self._client = client
        self._credentials = credentials
        self._totp_provider = totp_provider
        self._session: dict[str, Any] | None = None

    @property
    def session(self) -> dict[str, Any] | None:
        """Return the current session payload, if authenticated."""
        return self._session

    def authenticate(self) -> dict[str, Any]:
        """Create, validate, and store a new SmartAPI session."""
        session = self._generate_session()
        self._validate_session(session)
        self._session = session
        return session

    def refresh(self) -> dict[str, Any]:
        """Clear the current session and authenticate again."""
        self._session = None
        return self.authenticate()

    def ensure_authenticated(self) -> None:
        """Authenticate only when there is no stored session."""
        if self._session is None:
            self.authenticate()

    def terminate(self) -> dict[str, Any]:
        """Terminate the session and clear local session state."""
        response = self._terminate_session()
        self._session = None
        return response

    @smart_api_error_handler("Angel One authentication failed")
    def _generate_session(self) -> dict[str, Any]:
        """Call SmartAPI to generate a session."""
        return self._client.generate_session(
            self._credentials.client_code,
            self._credentials.password,
            self._totp_provider(self._credentials.totp_secret),
        )

    @smart_api_error_handler(
        "Angel One session termination failed",
        validate_status=False,
    )
    def _terminate_session(self) -> dict[str, Any]:
        """Call SmartAPI to terminate a session."""
        return self._client.terminate_session(self._credentials.client_code)

    def _validate_session(self, session: dict[str, Any] | None) -> None:
        """Validate that SmartAPI returned usable session data."""
        validate_smart_api_response(
            session, "Angel One session was not authenticated"
        )
        if not session.get("data"):
            raise AngelOneSmartApiRestBrokerError(
                "Angel One session was not authenticated",
                {"session": session},
            )


__all__ = [
    "AngelOneSessionManager",
    "SmartApiCredentials",
    "SmartApiSessionClient",
    "TotpProvider",
    "default_totp_provider",
]
