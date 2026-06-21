"""Tests for REST runtime route modules."""

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from data_layer.brokers.canonical.errors import (
    BrokerNotRegisteredError,
    BrokerOperationError,
)
from data_layer.brokers.canonical.models import (
    AccountResponse,
    CandleResponse,
    LtpResponse,
    QuoteResponse,
    ScripListResponse,
)
from data_layer.runtimes.rest.app import create_app
from data_layer.runtimes.rest.routes.account import (
    get_funds,
    get_holdings,
    get_order_book,
    get_positions,
    get_profile,
    get_trade_book,
)
from data_layer.runtimes.rest.routes.brokers import list_brokers_compat
from data_layer.runtimes.rest.routes.funda import fundamentals_namespace
from data_layer.runtimes.rest.routes.health import health
from data_layer.runtimes.rest.routes.market import (
    get_all_scrips,
    get_candles,
    get_intervals,
    get_ltp,
    get_quote,
    list_brokers,
)
from data_layer.runtimes.rest.schemas import (
    MAX_MARKET_SYMBOLS,
    CandlePayload,
    QuotePayload,
)


@pytest.mark.skip
def test_app_registers_expected_routes() -> None:
    """Verify the app includes the agreed REST routes."""
    app = create_app()
    paths = {getattr(route, "path", "") for route in app.routes}

    assert "/health" in paths
    assert "/brokers" in paths
    assert "/market/brokers" in paths
    assert "/market/{broker}/{exchange}/intervals" in paths
    assert "/market/{broker}/{exchange}/scrips" in paths
    assert "/market/{broker}/{exchange}/ltp" in paths
    assert "/market/{broker}/{exchange}/quotes" in paths
    assert "/market/{broker}/{exchange}/candles" in paths
    assert "/funda/{market}" in paths
    assert "/account/{broker}/profile" in paths
    assert "/account/{broker}/funds" in paths
    assert "/account/{broker}/holdings" in paths
    assert "/account/{broker}/positions" in paths
    assert "/account/{broker}/orders" in paths
    assert "/account/{broker}/trades" in paths


def test_health_route() -> None:
    """Verify health route is independent of broker wiring."""
    assert health() == {"status": "ok"}


def test_market_brokers_route() -> None:
    """Verify broker discovery lives under market namespace."""
    assert list_brokers() == {"brokers": ["angelone"]}
    assert list_brokers_compat() == {"brokers": ["angelone"]}


def test_intervals_route_returns_broker_intervals() -> None:
    """Verify interval discovery returns broker-specific intervals."""
    response = get_intervals(broker="angelone", exchange="nse")

    assert response["broker"] == "angelone"
    assert response["exchange"] == "NSE"
    assert {"label": "1m", "value": "ONE_MINUTE"} in response["intervals"]


def test_market_scrips_route_builds_canonical_request() -> None:
    """Verify market scrip listing uses canonical service."""
    service = _Service()

    response = get_all_scrips(
        broker="angelone",
        exchange="nse",
        service=service,
    )

    assert response["data"] == ["NSE: SBIN"]
    assert service.calls == [("get_all_scrips", "angelone", "NSE")]


def test_ltp_route_uses_ltp_for_one_symbol() -> None:
    """Verify one-symbol LTP requests use canonical LTP."""
    service = _Service()

    response = get_ltp(
        broker="angelone",
        exchange="nse",
        symbol="SBIN",
        service=service,
    )

    assert response["data"] == {"ltp": 100}
    assert service.calls == [("get_ltp", "angelone", "NSE", "SBIN")]


def test_ltp_route_uses_quote_ltp_for_many_symbols() -> None:
    """Verify multi-symbol LTP requests use quote mode LTP."""
    service = _Service()

    response = get_ltp(
        broker="angelone",
        exchange="nse",
        symbol="SBIN, RELIANCE",
        service=service,
    )

    assert response["data"] == {"quote": 1}
    assert service.calls == [
        ("get_quote", "angelone", "NSE", ("SBIN", "RELIANCE"), "LTP")
    ]


def test_ltp_route_rejects_more_than_max_symbols() -> None:
    """Verify LTP query symbols follow SmartAPI request limits."""
    symbols = ",".join(
        f"SYM{index}" for index in range(MAX_MARKET_SYMBOLS + 1)
    )
    service = _Service()

    with pytest.raises(HTTPException) as exc_info:
        get_ltp(
            broker="angelone",
            exchange="nse",
            symbol=symbols,
            service=service,
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["details"]["max_symbols"] == 50
    assert service.calls == []


def test_quote_payload_rejects_more_than_max_symbols() -> None:
    """Verify quote payloads follow SmartAPI request limits."""
    symbols = [f"SYM{index}" for index in range(MAX_MARKET_SYMBOLS + 1)]

    with pytest.raises(ValidationError):
        QuotePayload(symbols=symbols)


def test_quote_and_candle_routes_build_canonical_requests() -> None:
    """Verify quote and candle routes pass path exchange."""
    service = _Service()

    quote = get_quote(
        broker="angelone",
        exchange="nse",
        payload=QuotePayload(symbols=["SBIN", "RELIANCE"], mode="full"),
        service=service,
    )
    candles = get_candles(
        broker="angelone",
        exchange="nse",
        payload=CandlePayload(
            symbol="SBIN",
            interval="one_minute",
            from_time="2026-05-22 09:15",
            to_time="2026-05-22 09:20",
        ),
        service=service,
    )

    assert quote["data"] == {"quote": 1}
    assert candles["data"] == []
    assert service.calls == [
        ("get_quote", "angelone", "NSE", ("SBIN", "RELIANCE"), "FULL"),
        (
            "get_candles",
            "angelone",
            "NSE",
            "SBIN",
            "ONE_MINUTE",
            "2026-05-22 09:15",
            "2026-05-22 09:20",
        ),
    ]


def test_account_routes_build_canonical_requests() -> None:
    """Verify account routes use canonical account requests."""
    service = _Service()

    profile = get_profile(broker="angelone", service=service)
    get_funds(broker="angelone", service=service)
    get_holdings(broker="angelone", service=service)
    get_positions(broker="angelone", service=service)
    get_order_book(broker="angelone", service=service)
    get_trade_book(broker="angelone", service=service)

    assert profile["status"] == "work_in_progress"
    assert service.calls == [
        ("get_profile", "angelone"),
        ("get_funds", "angelone"),
        ("get_holdings", "angelone"),
        ("get_positions", "angelone"),
        ("get_order_book", "angelone"),
        ("get_trade_book", "angelone"),
    ]


def test_funda_namespace_is_reserved() -> None:
    """Verify fundamental namespace is reserved."""
    assert fundamentals_namespace("NSE") == {
        "market": "NSE",
        "status": "work_in_progress",
        "message": "Fundamental data endpoints are not implemented yet.",
    }


def test_validation_errors_map_to_http_exception() -> None:
    """Verify canonical validation failures return HTTP 422."""
    with pytest.raises(HTTPException) as exc_info:
        get_ltp(
            broker="angelone",
            exchange="NSE",
            symbol=" ",
            service=_Service(),
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "BROKER_VALIDATION_ERROR"


def test_missing_broker_errors_map_to_http_exception() -> None:
    """Verify missing brokers return HTTP 404."""
    with pytest.raises(HTTPException) as exc_info:
        get_ltp(
            broker="zerodha",
            exchange="NSE",
            symbol="SBIN",
            service=_Service(raise_missing=True),
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail["code"] == "BROKER_NOT_REGISTERED"


def test_operation_errors_map_to_http_exception() -> None:
    """Verify broker operation failures return HTTP 502."""
    with pytest.raises(HTTPException) as exc_info:
        get_ltp(
            broker="angelone",
            exchange="NSE",
            symbol="SBIN",
            service=_Service(raise_operation=True),
        )

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail["code"] == "BROKER_OPERATION_ERROR"


class _Service:
    """Fake canonical broker service for route tests."""

    broker_names = ["angelone"]

    def __init__(
        self,
        *,
        raise_missing: bool = False,
        raise_operation: bool = False,
    ) -> None:
        """Store fake service behavior."""
        self.calls = []
        self.raise_missing = raise_missing
        self.raise_operation = raise_operation

    def get_ltp(self, request) -> LtpResponse:
        """Return fake LTP response."""
        self._raise_if_needed(request.broker, "get_ltp")
        self.calls.append(
            ("get_ltp", request.broker, request.exchange, request.symbol)
        )
        return LtpResponse(
            broker=request.broker,
            operation="get_ltp",
            success=True,
            data={"ltp": 100},
        )

    def get_quote(self, request) -> QuoteResponse:
        """Return fake quote response."""
        self._raise_if_needed(request.broker, "get_quote")
        self.calls.append(
            (
                "get_quote",
                request.broker,
                request.exchange,
                request.symbols,
                request.mode,
            )
        )
        return QuoteResponse(
            broker=request.broker,
            operation="get_quote",
            success=True,
            data={"quote": 1},
        )

    def get_candles(self, request) -> CandleResponse:
        """Return fake candle response."""
        self.calls.append(
            (
                "get_candles",
                request.broker,
                request.exchange,
                request.symbol,
                request.interval,
                request.from_time,
                request.to_time,
            )
        )
        return CandleResponse(
            broker=request.broker,
            operation="get_candles",
            success=True,
            data=[],
        )

    def get_all_scrips(self, request) -> ScripListResponse:
        """Return fake scrip labels."""
        self.calls.append(("get_all_scrips", request.broker, request.exchange))
        return ScripListResponse(
            broker=request.broker,
            operation="get_all_scrips",
            success=True,
            data=[f"{request.exchange}: SBIN"],
        )

    def get_profile(self, request) -> AccountResponse:
        """Return fake profile data."""
        self.calls.append(("get_profile", request.broker))
        return _account_response(
            request.broker, "get_profile", {"name": "demo"}
        )

    def get_funds(self, request) -> AccountResponse:
        """Return fake funds data."""
        self.calls.append(("get_funds", request.broker))
        return _account_response(request.broker, "get_funds", {"cash": 1})

    def get_holdings(self, request) -> AccountResponse:
        """Return fake holdings data."""
        self.calls.append(("get_holdings", request.broker))
        return _account_response(request.broker, "get_holdings", [])

    def get_positions(self, request) -> AccountResponse:
        """Return fake positions data."""
        self.calls.append(("get_positions", request.broker))
        return _account_response(request.broker, "get_positions", [])

    def get_order_book(self, request) -> AccountResponse:
        """Return fake order book data."""
        self.calls.append(("get_order_book", request.broker))
        return _account_response(request.broker, "get_order_book", [])

    def get_trade_book(self, request) -> AccountResponse:
        """Return fake trade book data."""
        self.calls.append(("get_trade_book", request.broker))
        return _account_response(request.broker, "get_trade_book", [])

    def _raise_if_needed(self, broker: str, operation: str) -> None:
        """Raise configured canonical errors."""
        if self.raise_missing:
            raise BrokerNotRegisteredError(broker, ["angelone"])
        if self.raise_operation:
            raise BrokerOperationError(
                "Broker failed",
                broker=broker,
                operation=operation,
            )


def _account_response(broker: str, operation: str, data) -> AccountResponse:
    """Return an account response."""
    return AccountResponse(
        broker=broker,
        operation=operation,
        success=True,
        data=data,
    )
