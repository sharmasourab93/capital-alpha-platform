"""Tests for canonical broker registry."""

import pytest

from data_layer.brokers.canonical.errors import (
    BrokerNotRegisteredError,
    BrokerRegistrationError,
)
from data_layer.brokers.canonical.registry import BrokerRegistry


def test_registry_registers_and_resolves_adapter_case_insensitively() -> None:
    """Verify broker registration and lookup normalize names."""
    registry = BrokerRegistry()
    adapter = _Adapter("AngelOne")

    registry.register(adapter)

    assert registry.get(" angelone ") is adapter
    assert registry.broker_names == ["angelone"]


def test_registry_rejects_duplicate_registration() -> None:
    """Verify duplicate brokers are rejected."""
    registry = BrokerRegistry()
    registry.register(_Adapter("angelone"))

    with pytest.raises(BrokerRegistrationError) as exc_info:
        registry.register(_Adapter("ANGELONE"))

    assert exc_info.value.details == {"broker": "angelone"}


def test_registry_raises_for_missing_broker() -> None:
    """Verify missing brokers raise a lookup error."""
    registry = BrokerRegistry()
    registry.register(_Adapter("angelone"))

    with pytest.raises(BrokerNotRegisteredError) as exc_info:
        registry.get("zerodha")

    assert exc_info.value.details == {
        "broker": "zerodha",
        "available_brokers": ["angelone"],
    }


def test_registry_rejects_blank_broker_name() -> None:
    """Verify blank broker names cannot be registered."""
    registry = BrokerRegistry()

    with pytest.raises(BrokerRegistrationError):
        registry.register(_Adapter(" "))


def test_registry_rejects_adapter_without_broker_name() -> None:
    """Verify adapters must expose a broker name."""
    registry = BrokerRegistry()

    with pytest.raises(BrokerRegistrationError) as exc_info:
        registry.register(object())

    assert exc_info.value.details == {"broker": None}


def test_registry_rejects_non_string_lookup_name() -> None:
    """Verify registry lookups require broker names as strings."""
    registry = BrokerRegistry()

    with pytest.raises(BrokerRegistrationError) as exc_info:
        registry.get(None)

    assert exc_info.value.details == {"broker": None}


def test_registry_returns_sorted_broker_names() -> None:
    """Verify registered broker names are returned sorted."""
    registry = BrokerRegistry()
    registry.register(_Adapter("zerodha"))
    registry.register(_Adapter("angelone"))

    assert registry.broker_names == ["angelone", "zerodha"]


class _Adapter:
    """Minimal adapter with only broker identity."""

    def __init__(self, broker_name: str) -> None:
        """Store the broker name."""
        self.broker_name = broker_name
