"""FastAPI dependencies for REST routes."""

from __future__ import annotations

from functools import lru_cache

from data_layer.brokers import create_broker_rest_service
from data_layer.brokers.canonical.service import BrokerRestService


@lru_cache(maxsize=1)
def get_broker_rest_service() -> BrokerRestService:
    """Return the canonical broker service."""
    return create_broker_rest_service()


def clear_broker_rest_service_cache() -> None:
    """Clear the cached canonical broker service."""
    get_broker_rest_service.cache_clear()


__all__ = ["clear_broker_rest_service_cache", "get_broker_rest_service"]
