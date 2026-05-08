from __future__ import annotations

from dataclasses import dataclass, field

from .classification import (
    AssetClass,
    AssetType,
    DerivativeKind,
    InstrumentClassification,
    normalize_symbol,
)


DERIVATIVE_EXCHANGES = frozenset({"NFO", "BFO", "CDS", "MCX"})


@dataclass(frozen=True)
class AngelInstrument:
    token: str
    symbol: str
    name: str
    underlying: str
    exchange: str
    exchange_segment: str
    instrument_type: str
    expiry: str | None
    strike: float | None
    lot_size: int | None
    tick_size: float | None
    option_type: str | None
    classification: InstrumentClassification

    @property
    def normalized_symbol(self) -> str:
        return normalize_symbol(self.symbol)

    @property
    def asset_class(self) -> str:
        return self.classification.asset_class.value

    @property
    def asset_type(self) -> str:
        return self.classification.asset_type.value

    @property
    def market_class(self) -> str:
        return self.classification.market_label

    @property
    def derivative_kind(self) -> str:
        return self.classification.derivative_kind.value

    @property
    def market_label(self) -> str:
        return self.classification.market_label

    @property
    def is_derivative(self) -> bool:
        return self.classification.derivative_kind != DerivativeKind.NONE

    @property
    def is_probable_debt(self) -> bool:
        return self.classification.asset_class == AssetClass.DEBT

    @property
    def is_equity_like(self) -> bool:
        return (
            self.classification.asset_class == AssetClass.EQUITY
            and self.classification.asset_type == AssetType.STOCK
        )

    @property
    def is_listed_stock(self) -> bool:
        return self.is_equity_like

    def as_dict(self) -> dict[str, str | float | int | None]:
        return {
            "token": self.token,
            "symbol": self.symbol,
            "name": self.name,
            "exchange": self.exchange,
            "exchange_segment": self.exchange_segment,
            "instrument_type": self.instrument_type,
            "underlying": self.underlying,
            "expiry": self.expiry,
            "strike": self.strike,
            "lot_size": self.lot_size,
            "tick_size": self.tick_size,
            "option_type": self.option_type,
            "asset_class": self.asset_class,
            "asset_type": self.asset_type,
            "derivative_kind": self.derivative_kind,
            "market_label": self.market_label,
        }


@dataclass(frozen=True)
class ListedEquity:
    symbol: str
    name: str
    exchange: str
    broker_symbol: str
    token: str


@dataclass(frozen=True)
class ListedEquityInstrument:
    token: str
    symbol: str
    name: str
    exchange: str
    tick_size: float | None

    def as_dict(self) -> dict[str, str | float | None]:
        return {
            "token": self.token,
            "symbol": self.symbol,
            "name": self.name,
            "exchange": self.exchange,
            "tick_size": self.tick_size,
        }


@dataclass(frozen=True)
class DerivativeInstrumentRecord:
    token: str
    symbol: str
    name: str
    exchange: str
    instrument_type: str
    underlying: str
    expiry: str | None
    strike: float | None
    lot_size: int | None
    tick_size: float | None
    option_type: str | None
    asset_class: str
    asset_type: str
    derivative_kind: str

    def as_dict(
        self,
    ) -> dict[str, str | float | int | None]:
        return {
            "token": self.token,
            "symbol": self.symbol,
            "name": self.name,
            "exchange": self.exchange,
            "instrument_type": self.instrument_type,
            "underlying": self.underlying,
            "expiry": self.expiry,
            "strike": self.strike,
            "lot_size": self.lot_size,
            "tick_size": self.tick_size,
            "option_type": self.option_type,
            "asset_class": self.asset_class,
            "asset_type": self.asset_type,
            "derivative_kind": self.derivative_kind,
        }


@dataclass(frozen=True)
class InstrumentBucket:
    exchange: str
    instrument_type: str
    asset_class: str
    asset_type: str
    derivative_kind: str
    items: tuple[ListedEquityInstrument | DerivativeInstrumentRecord, ...]

    @property
    def count(self) -> int:
        return len(self.items)

    def as_dict(
        self,
    ) -> dict[str, str | int | list[dict[str, str | float | int | None]]]:
        return {
            "exchange": self.exchange,
            "instrument_type": self.instrument_type,
            "asset_class": self.asset_class,
            "asset_type": self.asset_type,
            "derivative_kind": self.derivative_kind,
            "count": self.count,
            "items": [item.as_dict() for item in self.items],
        }


@dataclass(frozen=True)
class ExchangeSegmentIndex:
    by_exchange: dict[str, tuple[InstrumentBucket, ...]]
    by_exchange_and_type: dict[str, dict[str, InstrumentBucket]]


@dataclass(frozen=True)
class StockCatalog:
    exchange: str
    stock_names: tuple[str, ...]
    by_name: dict[str, tuple[ListedEquity, ...]]
    by_symbol: dict[str, ListedEquity]
    listed_equities: tuple[ListedEquity, ...]
    instruments_by_name: dict[str, tuple[AngelInstrument, ...]] = field(
        default_factory=dict
    )
    instruments_by_symbol: dict[str, tuple[AngelInstrument, ...]] = field(
        default_factory=dict
    )


@dataclass(frozen=True)
class DerivativeExpiryBook:
    expiry: str
    contracts: tuple[AngelInstrument, ...]
    option_strikes_by_type: dict[str, tuple[float, ...]]
    contracts_by_resolution_key: dict[
        tuple[float | None, str | None], tuple[AngelInstrument, ...]
    ]


@dataclass(frozen=True)
class DerivativeFamilyBook:
    exchange: str
    underlying: str
    instrument_type: str
    expiries: tuple[str, ...]
    expiries_by_value: dict[str, DerivativeExpiryBook]
    symbols: tuple[str, ...]


@dataclass(frozen=True)
class DerivativeMarketCatalog:
    exchange: str
    families_by_instrument_type: dict[str, dict[str, DerivativeFamilyBook]]
    underlyings_by_instrument_type: dict[str, tuple[str, ...]]
    symbols_by_instrument_type: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class ExchangeInstrumentCatalog:
    exchange: str
    instruments: tuple[AngelInstrument, ...]
    instrument_types: tuple[str, ...]
    stock_catalog: StockCatalog | None = None
    derivative_catalog: DerivativeMarketCatalog | None = None


@dataclass(frozen=True)
class InstrumentMasterIndexes:
    by_token: dict[str, AngelInstrument]
    by_symbol_exchange: dict[tuple[str, str], tuple[AngelInstrument, ...]]
    exchanges: tuple[str, ...]
    exchange_catalogs: dict[str, ExchangeInstrumentCatalog]
    symbol_name_map_by_exchange: dict[str, dict[str, str]]
    symbol_name_counts_by_exchange: dict[str, int]
    stock_name_lookup_by_exchange: dict[str, dict[str, tuple[ListedEquity, ...]]]
    segment_index: ExchangeSegmentIndex


__all__ = [
    "AngelInstrument",
    "DERIVATIVE_EXCHANGES",
    "DerivativeExpiryBook",
    "DerivativeFamilyBook",
    "DerivativeMarketCatalog",
    "DerivativeInstrumentRecord",
    "ExchangeSegmentIndex",
    "ExchangeInstrumentCatalog",
    "InstrumentBucket",
    "InstrumentMasterIndexes",
    "ListedEquity",
    "ListedEquityInstrument",
    "StockCatalog",
]
