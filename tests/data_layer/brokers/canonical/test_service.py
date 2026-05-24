"""Tests for the canonical broker REST service."""

import pytest

from data_layer.brokers.canonical.errors import (
    BrokerNotRegisteredError,
    BrokerOperationError,
    BrokerValidationError,
)
from data_layer.brokers.canonical.models import (
    AccountRequest,
    AccountResponse,
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
from data_layer.brokers.canonical.registry import BrokerRegistry
from data_layer.brokers.canonical.service import BrokerRestService


def test_service_routes_ltp_request_to_registered_adapter() -> None:
    """Verify service dispatches requests through the registry."""
    adapter = _Adapter("angelone")
    service = _service(adapter)

    response = service.get_ltp(
        LtpRequest(broker="angelone", exchange="NSE", symbol="SBIN")
    )

    assert isinstance(response, LtpResponse)
    assert response.data == {"ltp": 100}
    assert adapter.calls == [("get_ltp", "NSE", "SBIN")]


def test_service_routes_market_data_operations() -> None:
    """Verify market-data operations route through the adapter."""
    adapter = _Adapter("angelone")
    service = _service(adapter)

    quote = service.get_quote(
        QuoteRequest(
            broker="angelone",
            exchange="NSE",
            symbols=["SBIN", "RELIANCE"],
            mode="ltp",
        )
    )
    candles = service.get_candles(
        CandleRequest(
            broker="angelone",
            exchange="NSE",
            symbol="SBIN",
            interval="ONE_MINUTE",
            from_time="2026-05-22 09:15",
            to_time="2026-05-22 09:20",
        )
    )

    assert isinstance(quote, QuoteResponse)
    assert isinstance(candles, CandleResponse)
    assert adapter.calls == [
        ("get_quote", "NSE", ("SBIN", "RELIANCE"), "LTP"),
        (
            "get_candles",
            "NSE",
            "SBIN",
            "ONE_MINUTE",
            "2026-05-22 09:15",
            "2026-05-22 09:20",
        ),
    ]


def test_service_routes_instrument_operations() -> None:
    """Verify instrument operations route through the adapter."""
    adapter = _Adapter("angelone")
    service = _service(adapter)

    scrip = service.get_scrip(
        ScripRequest(broker="angelone", exchange="NSE", symbol="SBIN")
    )
    scrips = service.get_all_scrips(
        ScripListRequest(broker="angelone", exchange="NSE")
    )

    assert isinstance(scrip, ScripResponse)
    assert isinstance(scrips, ScripListResponse)
    assert adapter.calls == [
        ("get_scrip", "NSE", "SBIN"),
        ("get_all_scrips", "NSE"),
    ]


def test_service_routes_all_account_operations() -> None:
    """Verify account operations route through the same entrypoint."""
    adapter = _Adapter("angelone")
    service = _service(adapter)
    request = AccountRequest(broker="angelone")

    responses = [
        service.get_profile(request),
        service.get_funds(request),
        service.get_holdings(request),
        service.get_positions(request),
        service.get_order_book(request),
        service.get_trade_book(request),
    ]

    assert all(isinstance(response, AccountResponse) for response in responses)
    assert adapter.calls == [
        ("get_profile",),
        ("get_funds",),
        ("get_holdings",),
        ("get_positions",),
        ("get_order_book",),
        ("get_trade_book",),
    ]


def test_service_exposes_registered_broker_names() -> None:
    """Verify service exposes registry broker names."""
    adapter = _Adapter("angelone")
    service = _service(adapter)

    assert service.broker_names == ["angelone"]


def test_service_raises_for_missing_broker() -> None:
    """Verify missing brokers raise registry errors."""
    service = BrokerRestService(BrokerRegistry())

    with pytest.raises(BrokerNotRegisteredError):
        service.get_profile(AccountRequest(broker="angelone"))


def test_service_preserves_canonical_adapter_errors() -> None:
    """Verify canonical adapter errors are not wrapped again."""
    adapter = _Adapter("angelone", raise_canonical=True)
    service = _service(adapter)

    with pytest.raises(BrokerValidationError) as exc_info:
        service.get_ltp(
            LtpRequest(broker="angelone", exchange="NSE", symbol="SBIN")
        )

    assert exc_info.value.details == {"field": "symbol"}


def test_service_wraps_unexpected_adapter_errors() -> None:
    """Verify unexpected adapter exceptions become canonical errors."""
    adapter = _Adapter("angelone", raise_unexpected=True)
    service = _service(adapter)

    with pytest.raises(BrokerOperationError) as exc_info:
        service.get_ltp(
            LtpRequest(broker="angelone", exchange="NSE", symbol="SBIN")
        )

    assert exc_info.value.details["broker"] == "angelone"
    assert exc_info.value.details["operation"] == "get_ltp"


def _service(adapter: "_Adapter") -> BrokerRestService:
    """Create a service with one registered adapter."""
    registry = BrokerRegistry()
    registry.register(adapter)
    return BrokerRestService(registry)


class _Adapter:
    """Fake canonical adapter used by service tests."""

    def __init__(
        self,
        broker_name: str,
        *,
        raise_unexpected: bool = False,
        raise_canonical: bool = False,
    ) -> None:
        """Store fake adapter behavior."""
        self.broker_name = broker_name
        self.raise_unexpected = raise_unexpected
        self.raise_canonical = raise_canonical
        self.calls = []

    def get_ltp(self, request: LtpRequest) -> LtpResponse:
        """Return fake LTP data."""
        if self.raise_unexpected:
            raise RuntimeError("socket closed")
        if self.raise_canonical:
            raise BrokerValidationError("Bad symbol", {"field": "symbol"})
        self.calls.append(("get_ltp", request.exchange, request.symbol))
        return LtpResponse(
            broker=self.broker_name,
            operation="get_ltp",
            success=True,
            data={"ltp": 100},
        )

    def get_quote(self, request: QuoteRequest) -> QuoteResponse:
        """Return fake quote data."""
        self.calls.append(
            ("get_quote", request.exchange, request.symbols, request.mode)
        )
        return QuoteResponse(
            broker=self.broker_name,
            operation="get_quote",
            success=True,
            data={"quote": 1},
        )

    def get_candles(self, request: CandleRequest) -> CandleResponse:
        """Return fake candle data."""
        self.calls.append(
            (
                "get_candles",
                request.exchange,
                request.symbol,
                request.interval,
                request.from_time,
                request.to_time,
            )
        )
        return CandleResponse(
            broker=self.broker_name,
            operation="get_candles",
            success=True,
            data=[],
        )

    def get_scrip(self, request: ScripRequest) -> ScripResponse:
        """Return fake scrip data."""
        self.calls.append(("get_scrip", request.exchange, request.symbol))
        return ScripResponse(
            broker=self.broker_name,
            operation="get_scrip",
            success=True,
            data={"symbol": request.symbol},
        )

    def get_all_scrips(self, request: ScripListRequest) -> ScripListResponse:
        """Return fake scrip labels."""
        self.calls.append(("get_all_scrips", request.exchange))
        return ScripListResponse(
            broker=self.broker_name,
            operation="get_all_scrips",
            success=True,
            data=[f"{request.exchange}: SBIN"],
        )

    def get_profile(self, request: AccountRequest) -> AccountResponse:
        """Return fake profile data."""
        self.calls.append(("get_profile",))
        return AccountResponse(
            broker=self.broker_name,
            operation="get_profile",
            success=True,
            data={"name": "demo"},
        )

    def get_funds(self, request: AccountRequest) -> AccountResponse:
        """Return fake funds data."""
        self.calls.append(("get_funds",))
        return _account_response(self.broker_name, "get_funds", {"cash": 1})

    def get_holdings(self, request: AccountRequest) -> AccountResponse:
        """Return fake holdings data."""
        self.calls.append(("get_holdings",))
        return _account_response(self.broker_name, "get_holdings", [])

    def get_positions(self, request: AccountRequest) -> AccountResponse:
        """Return fake positions data."""
        self.calls.append(("get_positions",))
        return _account_response(self.broker_name, "get_positions", [])

    def get_order_book(self, request: AccountRequest) -> AccountResponse:
        """Return fake order book data."""
        self.calls.append(("get_order_book",))
        return _account_response(self.broker_name, "get_order_book", [])

    def get_trade_book(self, request: AccountRequest) -> AccountResponse:
        """Return fake trade book data."""
        self.calls.append(("get_trade_book",))
        return _account_response(self.broker_name, "get_trade_book", [])


def _account_response(
    broker_name: str,
    operation: str,
    data,
) -> AccountResponse:
    """Return a fake account response."""
    return AccountResponse(
        broker=broker_name,
        operation=operation,
        success=True,
        data=data,
    )
