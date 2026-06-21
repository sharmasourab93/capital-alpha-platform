"""Account REST routes."""

from __future__ import annotations

from typing import Any

from data_layer.brokers.canonical.models import AccountRequest
from data_layer.brokers.canonical.service import BrokerRestService
from data_layer.runtimes.rest.dependencies import get_broker_rest_service
from data_layer.runtimes.rest.errors import call_or_raise
from data_layer.runtimes.rest.responses import response_body
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/account/{broker}", tags=["account"])
WORK_IN_PROGRESS_STATUS = "work_in_progress"


@router.get("/profile")
def get_profile(
    broker: str,
    service: BrokerRestService = Depends(get_broker_rest_service),
) -> dict[str, Any]:
    """Return account profile."""
    return _account_response(service.get_profile, broker)


@router.get("/funds")
def get_funds(
    broker: str,
    service: BrokerRestService = Depends(get_broker_rest_service),
) -> dict[str, Any]:
    """Return account funds."""
    return _account_response(service.get_funds, broker)


@router.get("/holdings")
def get_holdings(
    broker: str,
    service: BrokerRestService = Depends(get_broker_rest_service),
) -> dict[str, Any]:
    """Return account holdings."""
    return _account_response(service.get_holdings, broker)


@router.get("/positions")
def get_positions(
    broker: str,
    service: BrokerRestService = Depends(get_broker_rest_service),
) -> dict[str, Any]:
    """Return account positions."""
    return _account_response(service.get_positions, broker)


@router.get("/orders")
def get_order_book(
    broker: str,
    service: BrokerRestService = Depends(get_broker_rest_service),
) -> dict[str, Any]:
    """Return account order book."""
    return _account_response(service.get_order_book, broker)


@router.get("/trades")
def get_trade_book(
    broker: str,
    service: BrokerRestService = Depends(get_broker_rest_service),
) -> dict[str, Any]:
    """Return account trade book."""
    return _account_response(service.get_trade_book, broker)


def _account_response(call, broker: str) -> dict[str, Any]:
    """Execute an account operation."""
    response = call_or_raise(
        lambda: response_body(call(AccountRequest(broker=broker)))
    )
    response["status"] = WORK_IN_PROGRESS_STATUS
    return response
