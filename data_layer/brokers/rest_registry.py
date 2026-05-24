"""Broker-level REST registry factories."""

from __future__ import annotations

from collections.abc import Iterable

from data_layer.brokers.angelone.rest.angel_rest_broker import AngelRestBroker
from data_layer.brokers.angelone.rest.angelone_adapter import (
    AngelOneRestAdapter,
)
from data_layer.brokers.canonical.ports import RestBrokerPort
from data_layer.brokers.canonical.registry import BrokerRegistry
from data_layer.brokers.canonical.service import BrokerRestService

AVAILABLE_REST_BROKERS = ("angelone",)


def get_available_rest_brokers() -> list[str]:
    """Return broker names supported by the REST registry."""
    return list(AVAILABLE_REST_BROKERS)


def create_angelone_rest_adapter(
    broker: AngelRestBroker | None = None,
) -> AngelOneRestAdapter:
    """Create the canonical AngelOne REST adapter."""
    return AngelOneRestAdapter(broker or AngelRestBroker())


def create_rest_registry(
    adapters: Iterable[RestBrokerPort] = (),
) -> BrokerRegistry:
    """Create a registry from explicit REST broker adapters."""
    registry = BrokerRegistry()
    for adapter in adapters:
        registry.register(adapter)
    return registry


def create_default_rest_registry(
    *,
    angelone_broker: AngelRestBroker | None = None,
) -> BrokerRegistry:
    """Create the default REST registry with AngelOne registered."""
    return create_rest_registry(
        [create_angelone_rest_adapter(angelone_broker)]
    )


def create_broker_rest_service(
    registry: BrokerRegistry | None = None,
    *,
    angelone_broker: AngelRestBroker | None = None,
) -> BrokerRestService:
    """Create the canonical REST service for broker access."""
    return BrokerRestService(
        registry
        or create_default_rest_registry(angelone_broker=angelone_broker)
    )


__all__ = [
    "AVAILABLE_REST_BROKERS",
    "create_angelone_rest_adapter",
    "create_broker_rest_service",
    "create_default_rest_registry",
    "create_rest_registry",
    "get_available_rest_brokers",
]
