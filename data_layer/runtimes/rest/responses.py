"""Response conversion helpers for REST routes."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from data_layer.brokers.canonical.models import BrokerResponse


def response_body(response: BrokerResponse) -> dict[str, Any]:
    """Convert a canonical response to an HTTP body."""
    return asdict(response)
