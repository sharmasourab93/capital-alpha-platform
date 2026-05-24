"""Canonical adapter for AngelOne REST broker operations."""

from __future__ import annotations

from typing import Any

from data_layer.abstractions.instruments import BaseScripData
from data_layer.brokers.angelone.rest.angel_rest_broker import AngelRestBroker
from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
)
from data_layer.brokers.canonical.errors import BrokerOperationError
from data_layer.brokers.canonical.models import (
    AccountRequest,
    AccountResponse,
    BrokerResponse,
    CandleRequest,
    CandleResponse,
    LtpRequest,
    LtpResponse,
    QuoteRequest,
    QuoteResponse,
    ScripListRequest,
    ScripListResponse,
    ScripRequest,
    ScripResponse,
)


class AngelOneRestAdapter:
    """Expose AngelRestBroker through the canonical REST port."""

    broker_name = "angelone"

    def __init__(self, broker: AngelRestBroker) -> None:
        """Store the AngelOne REST broker facade."""
        self._broker = broker

    def get_scrip(self, request: ScripRequest) -> ScripResponse:
        """Return one AngelOne instrument as canonical data."""
        try:
            scrip = self._broker.get_scrip(request.exchange, request.symbol)
        except AngelOneSmartApiRestBrokerError as exc:
            raise self._operation_error("get_scrip", exc) from exc

        if scrip is None:
            return ScripResponse(
                broker=self.broker_name,
                operation="get_scrip",
                success=False,
                data=None,
                message="Scrip not found",
                error_code="SCRIP_NOT_FOUND",
            )

        return ScripResponse(
            broker=self.broker_name,
            operation="get_scrip",
            success=True,
            data=_scrip_to_dict(scrip),
        )

    def get_all_scrips(self, request: ScripListRequest) -> ScripListResponse:
        """Return AngelOne instrument labels for an exchange."""
        try:
            data = self._broker.get_all_scrips(request.exchange)
        except AngelOneSmartApiRestBrokerError as exc:
            raise self._operation_error("get_all_scrips", exc) from exc

        return ScripListResponse(
            broker=self.broker_name,
            operation="get_all_scrips",
            success=True,
            data=data,
        )

    def get_ltp(self, request: LtpRequest) -> LtpResponse:
        """Return AngelOne LTP data."""
        try:
            response = self._broker.get_ltp(request.exchange, request.symbol)
        except AngelOneSmartApiRestBrokerError as exc:
            raise self._operation_error("get_ltp", exc) from exc
        return _canonical_response(
            LtpResponse,
            self.broker_name,
            "get_ltp",
            response,
        )

    def get_quote(self, request: QuoteRequest) -> QuoteResponse:
        """Return AngelOne quote data."""
        try:
            response = self._broker.get_quote(
                request.exchange,
                list(request.symbols),
                mode=request.mode,
            )
        except AngelOneSmartApiRestBrokerError as exc:
            raise self._operation_error("get_quote", exc) from exc
        return _canonical_response(
            QuoteResponse,
            self.broker_name,
            "get_quote",
            response,
        )

    def get_candles(self, request: CandleRequest) -> CandleResponse:
        """Return AngelOne historical candles."""
        try:
            response = self._broker.get_candles(
                request.exchange,
                request.symbol,
                request.interval,
                request.from_time,
                request.to_time,
            )
        except AngelOneSmartApiRestBrokerError as exc:
            raise self._operation_error("get_candles", exc) from exc
        return _canonical_response(
            CandleResponse,
            self.broker_name,
            "get_candles",
            response,
        )

    def get_profile(self, request: AccountRequest) -> AccountResponse:
        """Return AngelOne account profile."""
        return self._account_response("get_profile", self._broker.get_profile)

    def get_funds(self, request: AccountRequest) -> AccountResponse:
        """Return AngelOne funds and margin details."""
        return self._account_response("get_funds", self._broker.get_funds)

    def get_holdings(self, request: AccountRequest) -> AccountResponse:
        """Return AngelOne holdings."""
        return self._account_response(
            "get_holdings", self._broker.get_holdings
        )

    def get_positions(self, request: AccountRequest) -> AccountResponse:
        """Return AngelOne positions."""
        return self._account_response(
            "get_positions",
            self._broker.get_positions,
        )

    def get_order_book(self, request: AccountRequest) -> AccountResponse:
        """Return AngelOne order book."""
        return self._account_response(
            "get_order_book",
            self._broker.get_order_book,
        )

    def get_trade_book(self, request: AccountRequest) -> AccountResponse:
        """Return AngelOne trade book."""
        return self._account_response(
            "get_trade_book",
            self._broker.get_trade_book,
        )

    def _account_response(self, operation: str, call) -> AccountResponse:
        """Return a canonical account response for one broker call."""
        try:
            response = call()
        except AngelOneSmartApiRestBrokerError as exc:
            raise self._operation_error(operation, exc) from exc
        return _canonical_response(
            AccountResponse,
            self.broker_name,
            operation,
            response,
        )

    def _operation_error(
        self,
        operation: str,
        exc: AngelOneSmartApiRestBrokerError,
    ) -> BrokerOperationError:
        """Convert AngelOne errors to canonical operation errors."""
        return BrokerOperationError(
            "AngelOne broker operation failed",
            broker=self.broker_name,
            operation=operation,
            details={
                "reason": str(exc),
                "source_details": exc.details,
            },
        )


def _canonical_response(
    response_type: type[BrokerResponse],
    broker: str,
    operation: str,
    response: dict[str, Any],
) -> BrokerResponse:
    """Convert a SmartAPI dict response into a canonical response."""
    success = response.get("status") is not False
    return response_type(
        broker=broker,
        operation=operation,
        success=success,
        data=response.get("data"),
        message=response.get("message"),
        error_code=response.get("errorcode") or response.get("errorCode"),
    )


def _scrip_to_dict(scrip: BaseScripData) -> dict[str, Any]:
    """Return broker-neutral scrip fields plus adapter metadata."""
    return scrip.to_dict()
