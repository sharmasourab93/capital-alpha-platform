"""Tests for broker-level REST registry factories."""

from data_layer.brokers.canonical.models import LtpRequest, LtpResponse
from data_layer.brokers.canonical.registry import BrokerRegistry
from data_layer.brokers.canonical.service import BrokerRestService
from data_layer.brokers.rest_registry import (
    create_angelone_rest_adapter,
    create_broker_rest_service,
    create_default_rest_registry,
    create_rest_registry,
    get_available_rest_brokers,
)


def test_create_rest_registry_registers_explicit_adapters() -> None:
    """Verify explicit adapters are registered."""
    adapter = _Adapter("demo")

    registry = create_rest_registry([adapter])

    assert registry.broker_names == ["demo"]
    assert registry.get("demo") is adapter


def test_available_rest_brokers_do_not_require_credentials() -> None:
    """Verify broker discovery does not instantiate live brokers."""
    assert get_available_rest_brokers() == ["angelone"]


def test_create_default_rest_registry_registers_angelone() -> None:
    """Verify default registry registers AngelOne."""
    broker = _AngelBroker()

    registry = create_default_rest_registry(angelone_broker=broker)

    assert registry.broker_names == ["angelone"]


def test_create_angelone_rest_adapter_wraps_supplied_broker() -> None:
    """Verify AngelOne adapter uses the supplied broker."""
    broker = _AngelBroker()
    adapter = create_angelone_rest_adapter(broker)

    response = adapter.get_ltp(
        LtpRequest(broker="angelone", exchange="NSE", symbol="SBIN")
    )

    assert response.data == {"ltp": 100}
    assert broker.calls == [("get_ltp", "NSE", "SBIN")]


def test_create_broker_rest_service_uses_supplied_registry() -> None:
    """Verify service factory respects an explicit registry."""
    registry = BrokerRegistry()
    registry.register(_Adapter("demo"))

    service = create_broker_rest_service(registry)

    assert isinstance(service, BrokerRestService)
    assert service.broker_names == ["demo"]


def test_create_broker_rest_service_builds_default_registry() -> None:
    """Verify service factory can build the default registry."""
    broker = _AngelBroker()

    service = create_broker_rest_service(angelone_broker=broker)
    response = service.get_ltp(
        LtpRequest(broker="angelone", exchange="NSE", symbol="SBIN")
    )

    assert response.data == {"ltp": 100}
    assert broker.calls == [("get_ltp", "NSE", "SBIN")]


class _Adapter:
    """Minimal canonical adapter."""

    def __init__(self, broker_name: str) -> None:
        """Store broker identity."""
        self.broker_name = broker_name


class _AngelBroker:
    """Minimal AngelRestBroker fake for registry tests."""

    def __init__(self) -> None:
        """Create a call recorder."""
        self.calls = []

    def get_ltp(self, exchange: str, key: str) -> dict:
        """Return fake LTP data."""
        self.calls.append(("get_ltp", exchange, key))
        return {"status": True, "data": {"ltp": 100}}
