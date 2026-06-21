"""Broker discovery compatibility routes."""

from __future__ import annotations

from data_layer.brokers import get_available_rest_brokers
from fastapi import APIRouter

router = APIRouter(tags=["market"])


@router.get("/brokers", include_in_schema=False)
def list_brokers_compat() -> dict[str, list[str]]:
    """Return brokers for the legacy broker discovery path."""
    return {"brokers": get_available_rest_brokers()}
