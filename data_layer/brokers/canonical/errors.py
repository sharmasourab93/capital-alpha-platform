"""Canonical broker errors."""

from __future__ import annotations

from typing import Any


class CanonicalBrokerError(Exception):
    """Base error raised by the canonical broker layer."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Create a canonical broker error."""
        super().__init__(message)
        self.code = code
        self.details = details or {}


class BrokerValidationError(CanonicalBrokerError):
    """Raised when canonical input is invalid."""

    def __init__(self, message: str, details: dict[str, Any]) -> None:
        """Create an input validation error."""
        super().__init__(
            message,
            code="BROKER_VALIDATION_ERROR",
            details=details,
        )


class BrokerRegistrationError(CanonicalBrokerError):
    """Raised when broker registration is invalid."""

    def __init__(self, message: str, details: dict[str, Any]) -> None:
        """Create a broker registration error."""
        super().__init__(
            message,
            code="BROKER_REGISTRATION_ERROR",
            details=details,
        )


class BrokerNotRegisteredError(CanonicalBrokerError):
    """Raised when a requested broker is not registered."""

    def __init__(self, broker: str, available_brokers: list[str]) -> None:
        """Create a broker lookup error."""
        super().__init__(
            "Broker is not registered",
            code="BROKER_NOT_REGISTERED",
            details={
                "broker": broker,
                "available_brokers": available_brokers,
            },
        )


class BrokerOperationError(CanonicalBrokerError):
    """Raised when a registered broker cannot complete an operation."""

    def __init__(
        self,
        message: str,
        *,
        broker: str,
        operation: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Create a broker operation error."""
        error_details = {"broker": broker, "operation": operation}
        if details:
            error_details.update(details)
        super().__init__(
            message,
            code="BROKER_OPERATION_ERROR",
            details=error_details,
        )
