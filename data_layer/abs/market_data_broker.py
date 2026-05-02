from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class BrokerMode(str, Enum):
    REST = "rest"
    WEBSOCKET = "websocket"


@dataclass(frozen=True)
class QuoteRequest:
    mode: str | None
    exchange: str
    symbols: tuple[str, ...]


@dataclass(frozen=True)
class CandleRequest:
    exchange: str
    interval: str
    from_date: str
    to_date: str
    symbol: Optional[str] = None
    instrument_token: Optional[str] = None


@dataclass(frozen=True)
class InstrumentRequest:
    exchange: str
    segment: Optional[str] = None
    symbol: Optional[str] = None
    query: Optional[str] = None


@dataclass(frozen=True)
class DerivativeInstrumentRequest:
    exchange: str
    underlying: str
    instrument_type: str
    expiry: str
    strike: float | None = None
    option_type: str | None = None


@dataclass(frozen=True)
class BrokerRequestContext:
    request_id: Optional[str] = None
    mode: BrokerMode = BrokerMode.REST
    timeout_seconds: float = 10.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class BrokerResponse:
    broker_name: str
    operation: str
    payload: Any
    status_code: int = 200
    success: bool = True
    raw_error: Any = None
    response_meta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BrokerCapabilities:
    supports_rest_quotes: bool = False
    supports_rest_candles: bool = False
    supports_rest_instruments: bool = False
    supports_websocket_quotes: bool = False
    supports_websocket_depth: bool = False


class MarketDataBroker(ABC):
    """
    Provider-facing contract for broker implementations.

    Concrete broker modules such as Zerodha and Angel One should implement
    these methods and return provider-native payloads inside BrokerResponse.
    Canonicalization should happen in a separate shared layer.
    """

    broker_name: str
    region: str = "india"
    capabilities: BrokerCapabilities = BrokerCapabilities()

    @abstractmethod
    def fetch_quotes(
        self,
        request: QuoteRequest,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        raise NotImplementedError

    @abstractmethod
    def fetch_candles(
        self,
        request: CandleRequest,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        raise NotImplementedError

    @abstractmethod
    def fetch_instruments(
        self,
        request: InstrumentRequest,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        raise NotImplementedError

    @abstractmethod
    def healthcheck(
        self,
        context: BrokerRequestContext | None = None,
    ) -> BrokerResponse:
        raise NotImplementedError
