"""Broker adapter registry."""

from __future__ import annotations

from data_layer.brokers.canonical.errors import (
    BrokerNotRegisteredError,
    BrokerRegistrationError,
)
from data_layer.brokers.canonical.ports import RestBrokerPort


class BrokerRegistry:
    """Register and resolve canonical REST broker adapters."""

    def __init__(self) -> None:
        """Create an empty broker registry."""
        self._adapters: dict[str, RestBrokerPort] = {}

    @property
    def broker_names(self) -> list[str]:
        """Return registered broker names."""
        return sorted(self._adapters)

    def register(self, adapter: RestBrokerPort) -> None:
        """Register one broker adapter."""
        broker_name = _normalize_broker_name(
            getattr(adapter, "broker_name", None)
        )
        if broker_name in self._adapters:
            raise BrokerRegistrationError(
                "Broker is already registered",
                {"broker": broker_name},
            )
        self._adapters[broker_name] = adapter

    def get(self, broker: str) -> RestBrokerPort:
        """Return a broker adapter by name."""
        broker_name = _normalize_broker_name(broker)
        try:
            return self._adapters[broker_name]
        except KeyError as exc:
            raise BrokerNotRegisteredError(
                broker_name,
                self.broker_names,
            ) from exc


def _normalize_broker_name(value: object) -> str:
    """Normalize and validate a broker name."""
    if not isinstance(value, str):
        raise BrokerRegistrationError(
            "Broker name must be a string",
            {"broker": value},
        )
    broker_name = value.strip().lower()
    if not broker_name:
        raise BrokerRegistrationError(
            "Broker name is required",
            {"broker": value},
        )
    return broker_name
