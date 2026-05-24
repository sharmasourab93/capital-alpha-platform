"""Tests for AngelOne SmartAPI error handling."""

import pytest

from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
    RetryConfig,
    call_smart_api,
    smart_api_error_handler,
    validate_smart_api_response,
)


def test_validate_response_rejects_non_dict_response() -> None:
    """Verify non-dict SmartAPI responses are rejected."""
    with pytest.raises(AngelOneSmartApiRestBrokerError) as exc_info:
        validate_smart_api_response([], "bad response")

    assert exc_info.value.details == {"response": []}


def test_validate_response_rejects_failed_status() -> None:
    """Verify failed SmartAPI status raises a broker error."""
    response = {"status": False, "message": "invalid token"}

    with pytest.raises(AngelOneSmartApiRestBrokerError) as exc_info:
        validate_smart_api_response(response, "failed response")

    assert exc_info.value.details == {"response": response}
    assert exc_info.value.is_auth_failure is True


def test_validate_response_can_skip_status_validation() -> None:
    """Verify callers can skip status checks for logout."""
    validate_smart_api_response(
        {"status": False, "message": "logout failed upstream"},
        "logout",
        validate_status=False,
    )


def test_call_smart_api_retries_transient_response(monkeypatch) -> None:
    """Verify transient responses are retried with backoff."""
    sleeps = []
    attempts = []

    monkeypatch.setattr(
        "data_layer.brokers.angelone.rest.smartapi.errors.time.sleep",
        lambda delay: sleeps.append(delay),
    )

    def operation():
        attempts.append("attempt")
        if len(attempts) < 3:
            return {
                "status": False,
                "status_code": 503,
                "message": "temporarily unavailable",
            }
        return {"status": True, "data": []}

    response = call_smart_api(
        "transient",
        operation,
        retry_config=RetryConfig(
            max_attempts=3,
            initial_delay_seconds=0.1,
            backoff_multiplier=2,
        ),
    )

    assert response == {"status": True, "data": []}
    assert attempts == ["attempt", "attempt", "attempt"]
    assert sleeps == [0.1, 0.2]


def test_call_smart_api_does_not_retry_auth_failure(monkeypatch) -> None:
    """Verify auth failures are not retried by generic retry logic."""
    sleeps = []
    attempts = []
    monkeypatch.setattr(
        "data_layer.brokers.angelone.rest.smartapi.errors.time.sleep",
        lambda delay: sleeps.append(delay),
    )

    def operation():
        attempts.append("attempt")
        return {"status": False, "message": "jwt token expired"}

    with pytest.raises(AngelOneSmartApiRestBrokerError):
        call_smart_api(
            "auth",
            operation,
            retry_config=RetryConfig(max_attempts=3),
        )

    assert attempts == ["attempt"]
    assert sleeps == []


def test_decorator_wraps_exception_and_preserves_function_metadata() -> None:
    """Verify the decorator normalizes exceptions and preserves names."""

    @smart_api_error_handler("decorated failure")
    def operation():
        raise RuntimeError("socket reset")

    with pytest.raises(AngelOneSmartApiRestBrokerError) as exc_info:
        operation()

    assert operation.__name__ == "operation"
    assert exc_info.value.details["reason"] == "socket reset"
