"""Tests for AngelOne SmartAPI session management."""

import pytest

from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
)
from data_layer.brokers.angelone.rest.smartapi.session import (
    AngelOneSessionManager,
    SmartApiCredentials,
)


def test_authenticate_generates_totp_and_stores_session() -> None:
    """Verify authentication generates TOTP and stores the session."""
    client = _SessionClient()
    manager = AngelOneSessionManager(
        client,
        _credentials(),
        totp_provider=lambda secret: "123456",
    )

    session = manager.authenticate()

    assert session == {"status": True, "data": {"jwtToken": "token"}}
    assert manager.session is session
    assert client.calls == [
        ("generate_session", "client", "password", "123456")
    ]


def test_ensure_authenticated_only_authenticates_when_missing() -> None:
    """Verify ensure_authenticated reuses an existing session."""
    client = _SessionClient()
    manager = AngelOneSessionManager(
        client,
        _credentials(),
        totp_provider=lambda secret: "123456",
    )

    manager.ensure_authenticated()
    manager.ensure_authenticated()

    assert [call[0] for call in client.calls] == ["generate_session"]


def test_refresh_clears_and_regenerates_session() -> None:
    """Verify refresh clears and recreates the session."""
    client = _SessionClient()
    manager = AngelOneSessionManager(
        client,
        _credentials(),
        totp_provider=lambda secret: "123456",
    )

    first = manager.authenticate()
    second = manager.refresh()

    assert first is not second
    assert [call[0] for call in client.calls] == [
        "generate_session",
        "generate_session",
    ]


def test_terminate_clears_session_state() -> None:
    """Verify terminate clears local session state."""
    client = _SessionClient()
    manager = AngelOneSessionManager(
        client,
        _credentials(),
        totp_provider=lambda secret: "123456",
    )
    manager.authenticate()

    response = manager.terminate()

    assert response == {"status": True, "data": {}}
    assert manager.session is None
    assert client.calls[-1] == ("terminate_session", "client")


def test_authenticate_rejects_missing_session_data() -> None:
    """Verify missing session data is rejected."""
    client = _SessionClient(session_response={"status": True})
    manager = AngelOneSessionManager(
        client,
        _credentials(),
        totp_provider=lambda secret: "123456",
    )

    with pytest.raises(AngelOneSmartApiRestBrokerError):
        manager.authenticate()


def _credentials() -> SmartApiCredentials:
    """Return deterministic SmartAPI credentials for session tests."""
    return SmartApiCredentials(
        api_key="api-key",
        client_code="client",
        password="password",
        totp_secret="secret",
    )


class _SessionClient:
    """Fake SmartAPI session client."""

    def __init__(self, session_response=None) -> None:
        self.calls = []
        self._session_response = session_response

    def generate_session(
        self, client_code: str, password: str, totp: str
    ) -> dict:
        self.calls.append(("generate_session", client_code, password, totp))
        return self._session_response or {
            "status": True,
            "data": {"jwtToken": "token"},
        }

    def terminate_session(self, client_code: str) -> dict:
        self.calls.append(("terminate_session", client_code))
        return {"status": True, "data": {}}
