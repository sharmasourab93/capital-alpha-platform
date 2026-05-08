from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock

from requests import get

from data_layer.abs import DerivativeInstrumentRequest

from .classification import AssetClass, AssetType, DerivativeKind
from .models import (
    AngelInstrument,
    DerivativeExpiryBook,
    DerivativeFamilyBook,
    DerivativeMarketCatalog,
    DerivativeInstrumentRecord,
    ExchangeSegmentIndex,
    ExchangeInstrumentCatalog,
    InstrumentBucket,
    InstrumentMasterIndexes,
    ListedEquity,
    ListedEquityInstrument,
    StockCatalog,
)
from .parser import expiry_sort_key, parse_instrument_rows

DEFAULT_SCRIP_MASTER_URL = (
    "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
)
_INSTRUMENT_MASTER_CACHE_LOCK = Lock()
_INSTRUMENT_MASTER_CACHE: dict[tuple[str, float], "AngelInstrumentMaster"] = {}


@dataclass
class AngelInstrumentMaster:
    instruments: list[AngelInstrument]
    indexes: InstrumentMasterIndexes = field(init=False)

    def __post_init__(self) -> None:
        self.indexes = _build_indexes(self.instruments)

    @property
    def by_token(self) -> dict[str, AngelInstrument]:
        return self.indexes.by_token

    @property
    def by_symbol_exchange(
        self,
    ) -> dict[tuple[str, str], tuple[AngelInstrument, ...]]:
        return self.indexes.by_symbol_exchange

    @property
    def listed_equities_by_exchange(self) -> dict[str, tuple[ListedEquity, ...]]:
        return {
            exchange: catalog.stock_catalog.listed_equities
            for exchange, catalog in self.indexes.exchange_catalogs.items()
            if catalog.stock_catalog is not None
        }

    @property
    def symbol_name_map_by_exchange(self) -> dict[str, dict[str, str]]:
        return self.indexes.symbol_name_map_by_exchange

    @property
    def symbol_name_counts_by_exchange(self) -> dict[str, int]:
        return self.indexes.symbol_name_counts_by_exchange

    @property
    def segment_index(self) -> ExchangeSegmentIndex:
        return self.indexes.segment_index

    @classmethod
    def from_url(
        cls,
        url: str = DEFAULT_SCRIP_MASTER_URL,
        timeout_seconds: float = 30.0,
    ) -> AngelInstrumentMaster:
        cache_key = (url, float(timeout_seconds))
        cached_master = _INSTRUMENT_MASTER_CACHE.get(cache_key)
        if cached_master is not None:
            return cached_master

        with _INSTRUMENT_MASTER_CACHE_LOCK:
            cached_master = _INSTRUMENT_MASTER_CACHE.get(cache_key)
            if cached_master is not None:
                return cached_master

            rows = cls._download_rows(url, timeout_seconds)
            master = cls.from_rows(rows)
            _INSTRUMENT_MASTER_CACHE[cache_key] = master
            return master

    @classmethod
    def from_rows(cls, rows: list[dict]) -> AngelInstrumentMaster:
        return cls(instruments=parse_instrument_rows(rows))

    @staticmethod
    def _download_rows(url: str, timeout_seconds: float) -> list[dict]:
        response = get(url, timeout=timeout_seconds)
        response.raise_for_status()
        payload = response.json()

        if payload is None:
            raise ValueError("Angel One scrip master returned null")
        if not isinstance(payload, list):
            raise TypeError(
                "Angel One scrip master returned {0}, expected list".format(
                    type(payload).__name__
                )
            )

        return payload

    def get_by_token(self, token: str) -> AngelInstrument | None:
        return self.indexes.by_token.get(str(token))

    def get_by_symbol_exchange(
        self,
        symbol: str,
        exchange: str,
    ) -> list[AngelInstrument]:
        return list(
            self.indexes.by_symbol_exchange.get(
                (symbol.upper(), exchange.upper()),
                (),
            )
        )

    def resolve_equity_instrument(
        self,
        symbol: str,
        exchange: str,
    ) -> AngelInstrument:
        candidate_keys = _equity_symbol_candidates(symbol)
        matches: list[AngelInstrument] = []

        for candidate_symbol in candidate_keys:
            matches.extend(
                self.get_by_symbol_exchange(candidate_symbol, exchange)
            )

        equity_matches = [
            instrument
            for instrument in matches
            if _is_equity_resolution_candidate(instrument)
        ]
        unique_matches = _dedupe_instruments(equity_matches)

        if not unique_matches:
            raise LookupError(
                "No equity instrument found for exchange={0}, symbol={1}".format(
                    exchange.upper(),
                    symbol.upper(),
                )
            )

        preferred_matches = [
            instrument
            for instrument in unique_matches
            if instrument.symbol == _preferred_equity_symbol(symbol)
        ]
        if len(preferred_matches) == 1:
            return preferred_matches[0]

        exact_symbol_matches = [
            instrument
            for instrument in unique_matches
            if instrument.symbol == symbol.upper()
        ]
        if len(exact_symbol_matches) == 1:
            return exact_symbol_matches[0]

        if len(unique_matches) == 1:
            return unique_matches[0]

        raise LookupError(
            "Multiple equity instruments found for exchange={0}, symbol={1}: {2}".format(
                exchange.upper(),
                symbol.upper(),
                ", ".join(
                    sorted(instrument.symbol for instrument in unique_matches)
                ),
            )
        )

    def get_exchanges(self) -> tuple[str, ...]:
        return self.indexes.exchanges

    def get_symbol_name_map_by_exchange(self) -> dict[str, dict[str, str]]:
        return {
            exchange: dict(symbol_map)
            for exchange, symbol_map in self.symbol_name_map_by_exchange.items()
        }

    def get_symbol_name_counts_by_exchange(self) -> dict[str, int]:
        return dict(self.symbol_name_counts_by_exchange)

    def get_symbol_name_page(
        self,
        exchange: str,
        *,
        query: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> dict[str, str | int | list[dict[str, str]] | None]:
        normalized_exchange = exchange.upper().strip()
        normalized_query = query.upper().strip() if query else None
        _validate_page_request(offset=offset, limit=limit)

        symbol_map = self.symbol_name_map_by_exchange.get(
            normalized_exchange,
            {},
        )
        items = [
            {"symbol": symbol, "name": name}
            for symbol, name in sorted(symbol_map.items())
            if not normalized_query
            or normalized_query in symbol
            or normalized_query in name.upper()
        ]
        page = items[offset : offset + limit]

        return {
            "exchange": normalized_exchange,
            "query": query,
            "offset": offset,
            "limit": limit,
            "total": len(items),
            "count": len(page),
            "items": page,
        }

    def get_stock_names(self, exchange: str) -> tuple[str, ...]:
        stock_catalog = self._stock_catalog(exchange)
        return stock_catalog.stock_names if stock_catalog else ()

    def get_stock_catalog(self, exchange: str) -> StockCatalog | None:
        return self._stock_catalog(exchange)

    def get_listed_equities(
        self,
        exchange: str,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> dict[str, str | int | list[dict[str, str]]]:
        _validate_page_request(offset=offset, limit=limit)
        normalized_exchange = exchange.upper().strip()
        stock_catalog = self._stock_catalog(normalized_exchange)
        listed_equities = (
            stock_catalog.listed_equities if stock_catalog is not None else ()
        )
        page = listed_equities[offset : offset + limit]

        return {
            "exchange": normalized_exchange,
            "total": len(listed_equities),
            "offset": offset,
            "limit": limit,
            "count": len(page),
            "items": [
                {
                    "symbol": equity.symbol,
                    "name": equity.name,
                }
                for equity in page
            ],
        }

    def get_stock_instruments(
        self,
        exchange: str,
    ) -> tuple[AngelInstrument, ...]:
        stock_catalog = self._stock_catalog(exchange)
        if stock_catalog is None:
            return ()

        instruments = [
            instrument
            for matches in stock_catalog.instruments_by_symbol.values()
            for instrument in matches
        ]
        return tuple(
            sorted(
                _dedupe_instruments(instruments),
                key=lambda item: (
                    item.normalized_symbol,
                    item.name,
                    item.symbol,
                    item.token,
                ),
            )
        )

    def resolve_equity_instruments_by_name(
        self,
        exchange: str,
        name: str,
    ) -> tuple[AngelInstrument, ...]:
        stock_catalog = self._stock_catalog(exchange)
        if stock_catalog is None:
            return ()
        normalized_name = " ".join(name.upper().split())
        return stock_catalog.instruments_by_name.get(normalized_name, ())

    def resolve_listed_equity_by_name(
        self,
        exchange: str,
        name: str,
    ) -> tuple[ListedEquity, ...]:
        normalized_exchange = exchange.upper().strip()
        normalized_name = " ".join(name.upper().split())
        return self.indexes.stock_name_lookup_by_exchange.get(
            normalized_exchange,
            {},
        ).get(normalized_name, ())

    def get_instrument_types(
        self,
        exchange: str | None = None,
    ) -> tuple[str, ...]:
        if exchange:
            exchange_catalog = self.indexes.exchange_catalogs.get(
                exchange.upper().strip()
            )
            return exchange_catalog.instrument_types if exchange_catalog else ()

        instrument_types = {
            instrument.instrument_type
            for instrument in self.instruments
        }
        return tuple(sorted(instrument_types))

    def get_instruments_by_exchange(
        self,
        exchange: str,
    ) -> list[dict[str, str | float | int | None]]:
        exchange_catalog = self.indexes.exchange_catalogs.get(
            exchange.upper().strip()
        )
        if exchange_catalog is None:
            return []
        return [instrument.as_dict() for instrument in exchange_catalog.instruments]

    def get_instruments_by_exchange_page(
        self,
        exchange: str,
        *,
        query: str | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> dict[str, str | int | list[dict[str, str | float | int | None]] | None]:
        normalized_exchange = exchange.upper().strip()
        normalized_query = query.upper().strip() if query else None
        _validate_page_request(offset=offset, limit=limit)

        exchange_catalog = self.indexes.exchange_catalogs.get(normalized_exchange)
        if exchange_catalog is None:
            items: list[dict[str, str | float | int | None]] = []
        else:
            items = [
                instrument.as_dict()
                for instrument in exchange_catalog.instruments
                if not normalized_query
                or normalized_query in instrument.symbol
                or normalized_query in instrument.name.upper()
            ]
        page = items[offset : offset + limit]

        return {
            "exchange": normalized_exchange,
            "query": query,
            "offset": offset,
            "limit": limit,
            "total": len(items),
            "count": len(page),
            "items": page,
        }

    def get_exchange_segment_bucket(
        self,
        exchange: str,
        instrument_type: str = "",
    ) -> InstrumentBucket | None:
        return self.segment_index.by_exchange_and_type.get(
            exchange.upper().strip(),
            {},
        ).get(instrument_type.upper().strip())

    def get_exchange_segment_types(
        self,
        exchange: str | None = None,
    ) -> dict[str, tuple[str, ...]]:
        if exchange:
            normalized_exchange = exchange.upper().strip()
            type_map = self.segment_index.by_exchange_and_type.get(
                normalized_exchange,
                {},
            )
            return {normalized_exchange: tuple(sorted(type_map))}

        return {
            exchange_key: tuple(sorted(type_map))
            for exchange_key, type_map in sorted(
                self.segment_index.by_exchange_and_type.items()
            )
        }

    def get_normalized_instruments(
        self,
        exchange: str,
        instrument_type: str = "",
    ) -> tuple[ListedEquityInstrument | DerivativeInstrumentRecord, ...]:
        bucket = self.get_exchange_segment_bucket(
            exchange=exchange,
            instrument_type=instrument_type,
        )
        if bucket is None:
            return ()
        return bucket.items

    def get_normalized_exchange_segments(
        self,
        exchange: str | None = None,
    ) -> dict[str, list[dict[str, str | int]]]:
        exchanges = (
            (exchange.upper().strip(),)
            if exchange
            else tuple(sorted(self.segment_index.by_exchange.items()))
        )
        if exchange:
            buckets = self.segment_index.by_exchange.get(exchanges[0], ())
            return {
                exchanges[0]: [
                    {
                        "instrument_type": bucket.instrument_type,
                        "asset_class": bucket.asset_class,
                        "asset_type": bucket.asset_type,
                        "derivative_kind": bucket.derivative_kind,
                        "count": bucket.count,
                    }
                    for bucket in buckets
                ]
            }

        result: dict[str, list[dict[str, str | int]]] = {}
        for exchange_key, buckets in sorted(self.segment_index.by_exchange.items()):
            result[exchange_key] = [
                {
                    "instrument_type": bucket.instrument_type,
                    "asset_class": bucket.asset_class,
                    "asset_type": bucket.asset_type,
                    "derivative_kind": bucket.derivative_kind,
                    "count": bucket.count,
                }
                for bucket in buckets
            ]
        return result

    def get_listed_stock_records(
        self,
        exchange: str,
    ) -> tuple[ListedEquityInstrument, ...]:
        for instrument_type in ("EQ", ""):
            bucket = self.get_exchange_segment_bucket(exchange, instrument_type)
            if bucket is None:
                continue
            records = tuple(
                item
                for item in bucket.items
                if isinstance(item, ListedEquityInstrument)
            )
            if records:
                return records
        return ()

    def get_derivative_symbols(
        self,
        exchange: str | None = None,
        instrument_type: str | None = None,
    ) -> dict[str, dict[str, list[str]]]:
        return _select_derivative_exchange_view(
            exchange_catalogs=self.indexes.exchange_catalogs,
            exchange=exchange,
            instrument_type=instrument_type,
            value_selector=lambda family: family.symbols,
        )

    def get_derivative_catalog(
        self,
        exchange: str,
    ) -> DerivativeMarketCatalog | None:
        exchange_catalog = self.indexes.exchange_catalogs.get(
            exchange.upper().strip()
        )
        if exchange_catalog is None:
            return None
        return exchange_catalog.derivative_catalog

    def get_derivative_family_catalog(
        self,
        *,
        exchange: str,
        underlying: str,
        instrument_type: str,
    ) -> DerivativeFamilyBook:
        return self._require_derivative_family(
            exchange=exchange,
            underlying=underlying,
            instrument_type=instrument_type,
        )

    def get_derivative_expiry_catalog(
        self,
        *,
        exchange: str,
        underlying: str,
        instrument_type: str,
        expiry: str,
    ) -> DerivativeExpiryBook:
        return self._require_derivative_expiry_book(
            exchange=exchange,
            underlying=underlying,
            instrument_type=instrument_type,
            expiry=expiry,
        )

    def get_derivative_underlyings(
        self,
        *,
        exchange: str | None = None,
        instrument_type: str | None = None,
    ) -> dict[str, dict[str, list[str]]]:
        result: dict[str, dict[str, list[str]]] = {}
        for exchange_key, exchange_catalog in sorted(
            self.indexes.exchange_catalogs.items()
        ):
            if exchange and exchange_key != exchange.upper().strip():
                continue
            derivative_catalog = exchange_catalog.derivative_catalog
            if derivative_catalog is None:
                continue

            type_map: dict[str, list[str]] = {}
            for instrument_type_key, underlyings in sorted(
                derivative_catalog.underlyings_by_instrument_type.items()
            ):
                if (
                    instrument_type
                    and instrument_type_key != instrument_type.upper().strip()
                ):
                    continue
                type_map[instrument_type_key] = list(underlyings)

            if type_map:
                result[exchange_key] = type_map
        return result

    def get_derivative_expiries(
        self,
        *,
        exchange: str,
        underlying: str,
        instrument_type: str,
    ) -> tuple[str, ...]:
        family = self._require_derivative_family(
            exchange=exchange,
            underlying=underlying,
            instrument_type=instrument_type,
        )
        return family.expiries

    def get_derivative_contracts(
        self,
        *,
        exchange: str,
        underlying: str,
        instrument_type: str,
        expiry: str,
        option_type: str | None = None,
    ) -> list[dict[str, str | float | int | None]]:
        expiry_book = self._require_derivative_expiry_book(
            exchange=exchange,
            underlying=underlying,
            instrument_type=instrument_type,
            expiry=expiry,
        )
        normalized_option_type = option_type.upper() if option_type else None

        contracts = [
            instrument
            for instrument in expiry_book.contracts
            if (
                normalized_option_type is None
                or instrument.option_type == normalized_option_type
            )
        ]
        contracts_by_symbol: dict[str, dict[str, str | float | int | None]] = {}
        for instrument in contracts:
            contracts_by_symbol.setdefault(
                instrument.symbol,
                {
                    "symbol": instrument.symbol,
                    "exchange": instrument.exchange,
                    "exchange_segment": instrument.exchange_segment,
                    "instrument_type": instrument.instrument_type,
                    "underlying": instrument.underlying,
                    "expiry": instrument.expiry,
                    "strike": instrument.strike,
                    "lot_size": instrument.lot_size,
                    "option_type": instrument.option_type,
                    "asset_class": instrument.asset_class,
                    "asset_type": instrument.asset_type,
                },
            )
        return sorted(
            contracts_by_symbol.values(),
            key=lambda item: (
                item["strike"] is None,
                item["strike"] or 0,
                item["option_type"] or "",
                item["symbol"],
            ),
        )

    def get_derivative_strikes(
        self,
        *,
        exchange: str,
        underlying: str,
        instrument_type: str,
        expiry: str,
        option_type: str | None = None,
    ) -> tuple[float, ...]:
        expiry_book = self._require_derivative_expiry_book(
            exchange=exchange,
            underlying=underlying,
            instrument_type=instrument_type,
            expiry=expiry,
        )
        if option_type:
            return expiry_book.option_strikes_by_type.get(
                option_type.upper().strip(),
                (),
            )
        unique_strikes = {
            strike
            for strikes in expiry_book.option_strikes_by_type.values()
            for strike in strikes
        }
        return tuple(sorted(unique_strikes))

    def resolve_derivative_instrument(
        self,
        request: DerivativeInstrumentRequest,
    ) -> AngelInstrument:
        try:
            expiry_book = self._require_derivative_expiry_book(
                exchange=request.exchange,
                underlying=request.underlying,
                instrument_type=request.instrument_type,
                expiry=request.expiry,
            )
        except LookupError as exc:
            raise LookupError(
                "No derivative instrument found for exchange={0}, underlying={1}, "
                "instrument_type={2}, expiry={3}, strike={4}, option_type={5}".format(
                    request.exchange.upper(),
                    request.underlying.upper(),
                    request.instrument_type.upper(),
                    request.expiry,
                    request.strike,
                    request.option_type.upper()
                    if request.option_type
                    else None,
                )
            ) from exc
        key = (
            float(request.strike) if request.strike is not None else None,
            request.option_type.upper() if request.option_type else None,
        )
        matches = expiry_book.contracts_by_resolution_key.get(key, ())
        unique_matches = _dedupe_instruments(list(matches))

        if not unique_matches:
            raise LookupError(
                "No derivative instrument found for exchange={0}, underlying={1}, "
                "instrument_type={2}, expiry={3}, strike={4}, option_type={5}".format(
                    request.exchange.upper(),
                    request.underlying.upper(),
                    request.instrument_type.upper(),
                    request.expiry,
                    request.strike,
                    request.option_type.upper()
                    if request.option_type
                    else None,
                )
            )
        if len(unique_matches) > 1:
            raise LookupError(
                "Multiple derivative instruments found for exchange={0}, underlying={1}, "
                "instrument_type={2}, expiry={3}, strike={4}, option_type={5}".format(
                    request.exchange.upper(),
                    request.underlying.upper(),
                    request.instrument_type.upper(),
                    request.expiry,
                    request.strike,
                    request.option_type.upper()
                    if request.option_type
                    else None,
                )
            )
        return unique_matches[0]

    def _stock_catalog(self, exchange: str) -> StockCatalog | None:
        exchange_catalog = self.indexes.exchange_catalogs.get(
            exchange.upper().strip()
        )
        if exchange_catalog is None:
            return None
        return exchange_catalog.stock_catalog

    def _require_derivative_family(
        self,
        *,
        exchange: str,
        underlying: str,
        instrument_type: str,
    ) -> DerivativeFamilyBook:
        exchange_catalog = self.indexes.exchange_catalogs.get(
            exchange.upper().strip()
        )
        derivative_catalog = (
            exchange_catalog.derivative_catalog if exchange_catalog else None
        )
        if derivative_catalog is None:
            raise LookupError(
                "No derivative catalog found for exchange={0}".format(
                    exchange.upper()
                )
            )
        family = derivative_catalog.families_by_instrument_type.get(
            instrument_type.upper().strip(),
            {},
        ).get(underlying.upper().strip())
        if family is None:
            raise LookupError(
                "No derivative family found for exchange={0}, underlying={1}, instrument_type={2}".format(
                    exchange.upper(),
                    underlying.upper(),
                    instrument_type.upper(),
                )
            )
        return family

    def _require_derivative_expiry_book(
        self,
        *,
        exchange: str,
        underlying: str,
        instrument_type: str,
        expiry: str,
    ) -> DerivativeExpiryBook:
        family = self._require_derivative_family(
            exchange=exchange,
            underlying=underlying,
            instrument_type=instrument_type,
        )
        expiry_book = family.expiries_by_value.get(expiry)
        if expiry_book is None:
            raise LookupError(
                "No derivative expiry found for exchange={0}, underlying={1}, instrument_type={2}, expiry={3}".format(
                    exchange.upper(),
                    underlying.upper(),
                    instrument_type.upper(),
                    expiry,
                )
            )
        return expiry_book


def _build_indexes(
    instruments: list[AngelInstrument],
) -> InstrumentMasterIndexes:
    by_token: dict[str, AngelInstrument] = {}
    by_symbol_exchange: dict[tuple[str, str], list[AngelInstrument]] = defaultdict(
        list
    )
    instruments_by_exchange: dict[str, list[AngelInstrument]] = defaultdict(list)
    symbol_name_map_by_exchange: dict[str, dict[str, str]] = defaultdict(dict)

    for instrument in instruments:
        by_token[instrument.token] = instrument
        by_symbol_exchange[(instrument.symbol, instrument.exchange)].append(
            instrument
        )
        instruments_by_exchange[instrument.exchange].append(instrument)
        symbol_name_map_by_exchange[instrument.exchange].setdefault(
            instrument.symbol,
            instrument.name,
        )

    exchange_catalogs: dict[str, ExchangeInstrumentCatalog] = {}
    stock_name_lookup_by_exchange: dict[
        str, dict[str, tuple[ListedEquity, ...]]
    ] = {}
    segment_buckets_by_exchange_and_type: dict[
        str, dict[str, InstrumentBucket]
    ] = defaultdict(dict)

    for exchange, exchange_instruments in sorted(instruments_by_exchange.items()):
        stock_catalog = _build_stock_catalog(exchange, exchange_instruments)
        derivative_catalog = _build_derivative_catalog(
            exchange,
            exchange_instruments,
        )
        exchange_catalogs[exchange] = ExchangeInstrumentCatalog(
            exchange=exchange,
            instruments=tuple(exchange_instruments),
            instrument_types=tuple(
                sorted({item.instrument_type for item in exchange_instruments})
            ),
            stock_catalog=stock_catalog,
            derivative_catalog=derivative_catalog,
        )
        if stock_catalog is not None:
            stock_name_lookup_by_exchange[exchange] = stock_catalog.by_name
        segment_buckets_by_exchange_and_type[exchange] = (
            _build_exchange_segment_buckets(
                exchange=exchange,
                instruments=exchange_instruments,
            )
        )

    return InstrumentMasterIndexes(
        by_token=by_token,
        by_symbol_exchange={
            key: tuple(value) for key, value in by_symbol_exchange.items()
        },
        exchanges=tuple(sorted(exchange_catalogs)),
        exchange_catalogs=exchange_catalogs,
        symbol_name_map_by_exchange={
            exchange: dict(symbol_map)
            for exchange, symbol_map in symbol_name_map_by_exchange.items()
        },
        symbol_name_counts_by_exchange={
            exchange: len(symbol_map)
            for exchange, symbol_map in symbol_name_map_by_exchange.items()
        },
        stock_name_lookup_by_exchange=stock_name_lookup_by_exchange,
        segment_index=ExchangeSegmentIndex(
            by_exchange={
                exchange: tuple(
                    bucket
                    for _, bucket in sorted(type_map.items())
                )
                for exchange, type_map in sorted(
                    segment_buckets_by_exchange_and_type.items()
                )
            },
            by_exchange_and_type={
                exchange: dict(type_map)
                for exchange, type_map in segment_buckets_by_exchange_and_type.items()
            },
        ),
    )


def _build_stock_catalog(
    exchange: str,
    instruments: list[AngelInstrument],
) -> StockCatalog | None:
    listed_equities_by_symbol: dict[str, ListedEquity] = {}
    instruments_by_name: dict[str, list[AngelInstrument]] = defaultdict(list)
    instruments_by_symbol: dict[str, list[AngelInstrument]] = defaultdict(list)

    for instrument in instruments:
        if not instrument.is_listed_stock:
            continue
        normalized_name = " ".join(instrument.name.upper().split())
        instruments_by_name[normalized_name].append(instrument)
        instruments_by_symbol[instrument.normalized_symbol].append(instrument)
        listed_equities_by_symbol.setdefault(
            instrument.normalized_symbol,
            ListedEquity(
                symbol=instrument.normalized_symbol,
                name=instrument.name,
                exchange=exchange,
                broker_symbol=instrument.symbol,
                token=instrument.token,
            ),
        )

    if not listed_equities_by_symbol:
        return None

    listed_equities = tuple(
        sorted(
            listed_equities_by_symbol.values(),
            key=lambda equity: (equity.symbol, equity.name, equity.token),
        )
    )
    by_name: dict[str, list[ListedEquity]] = defaultdict(list)
    for equity in listed_equities:
        by_name[" ".join(equity.name.upper().split())].append(equity)

    return StockCatalog(
        exchange=exchange,
        stock_names=tuple(equity.name for equity in listed_equities),
        by_name={
            name: tuple(matches)
            for name, matches in sorted(by_name.items())
        },
        by_symbol=dict(listed_equities_by_symbol),
        listed_equities=listed_equities,
        instruments_by_name={
            name: tuple(
                sorted(
                    matches,
                    key=lambda item: (item.symbol, item.name, item.token),
                )
            )
            for name, matches in sorted(instruments_by_name.items())
        },
        instruments_by_symbol={
            symbol: tuple(
                sorted(
                    matches,
                    key=lambda item: (item.symbol, item.name, item.token),
                )
            )
            for symbol, matches in sorted(instruments_by_symbol.items())
        },
    )


def _build_derivative_catalog(
    exchange: str,
    instruments: list[AngelInstrument],
) -> DerivativeMarketCatalog | None:
    derivative_instruments = [
        instrument
        for instrument in instruments
        if instrument.classification.derivative_kind != DerivativeKind.NONE
    ]
    if not derivative_instruments:
        return None

    grouped: dict[str, dict[str, list[AngelInstrument]]] = defaultdict(
        lambda: defaultdict(list)
    )
    symbols_by_type: dict[str, set[str]] = defaultdict(set)

    for instrument in derivative_instruments:
        grouped[instrument.instrument_type][instrument.underlying].append(
            instrument
        )
        symbols_by_type[instrument.instrument_type].add(instrument.symbol)

    families_by_instrument_type: dict[str, dict[str, DerivativeFamilyBook]] = {}
    underlyings_by_instrument_type: dict[str, tuple[str, ...]] = {}

    for instrument_type, family_map in grouped.items():
        families_by_underlying: dict[str, DerivativeFamilyBook] = {}
        for underlying, family_instruments in family_map.items():
            families_by_underlying[underlying] = _build_derivative_family(
                exchange=exchange,
                underlying=underlying,
                instrument_type=instrument_type,
                instruments=family_instruments,
            )

        families_by_instrument_type[instrument_type] = families_by_underlying
        underlyings_by_instrument_type[instrument_type] = tuple(
            sorted(families_by_underlying)
        )

    return DerivativeMarketCatalog(
        exchange=exchange,
        families_by_instrument_type=families_by_instrument_type,
        underlyings_by_instrument_type=underlyings_by_instrument_type,
        symbols_by_instrument_type={
            instrument_type: tuple(sorted(symbols))
            for instrument_type, symbols in symbols_by_type.items()
        },
    )


def _build_derivative_family(
    *,
    exchange: str,
    underlying: str,
    instrument_type: str,
    instruments: list[AngelInstrument],
) -> DerivativeFamilyBook:
    grouped_by_expiry: dict[str, list[AngelInstrument]] = defaultdict(list)
    symbol_set: set[str] = set()

    for instrument in instruments:
        if not instrument.expiry:
            continue
        grouped_by_expiry[instrument.expiry].append(instrument)
        symbol_set.add(instrument.symbol)

    expiries = tuple(sorted(grouped_by_expiry, key=expiry_sort_key))
    expiries_by_value = {
        expiry: _build_derivative_expiry_book(
            expiry=expiry,
            instruments=grouped_by_expiry[expiry],
        )
        for expiry in expiries
    }

    return DerivativeFamilyBook(
        exchange=exchange,
        underlying=underlying,
        instrument_type=instrument_type,
        expiries=expiries,
        expiries_by_value=expiries_by_value,
        symbols=tuple(sorted(symbol_set)),
    )


def _build_derivative_expiry_book(
    *,
    expiry: str,
    instruments: list[AngelInstrument],
) -> DerivativeExpiryBook:
    option_strikes_by_type: dict[str, set[float]] = defaultdict(set)
    contracts_by_resolution_key: dict[
        tuple[float | None, str | None], list[AngelInstrument]
    ] = defaultdict(list)

    for instrument in instruments:
        if instrument.option_type and instrument.strike is not None:
            option_strikes_by_type[instrument.option_type].add(
                instrument.strike
            )
        key = (instrument.strike, instrument.option_type)
        contracts_by_resolution_key[key].append(instrument)

    return DerivativeExpiryBook(
        expiry=expiry,
        contracts=tuple(
            sorted(
                instruments,
                key=lambda item: (
                    item.strike is None,
                    item.strike or 0,
                    item.option_type or "",
                    item.symbol,
                ),
            )
        ),
        option_strikes_by_type={
            option_type: tuple(sorted(strikes))
            for option_type, strikes in option_strikes_by_type.items()
        },
        contracts_by_resolution_key={
            key: tuple(value)
            for key, value in contracts_by_resolution_key.items()
        },
    )


def _build_exchange_segment_buckets(
    *,
    exchange: str,
    instruments: list[AngelInstrument],
) -> dict[str, InstrumentBucket]:
    grouped: dict[str, list[AngelInstrument]] = defaultdict(list)
    for instrument in instruments:
        grouped[instrument.instrument_type].append(instrument)

    buckets: dict[str, InstrumentBucket] = {}
    for instrument_type, grouped_instruments in sorted(grouped.items()):
        buckets[instrument_type] = _build_exchange_segment_bucket(
            exchange=exchange,
            instrument_type=instrument_type,
            instruments=grouped_instruments,
        )
    return buckets


def _build_exchange_segment_bucket(
    *,
    exchange: str,
    instrument_type: str,
    instruments: list[AngelInstrument],
) -> InstrumentBucket:
    first = instruments[0]
    if _is_compact_equity_bucket(first, instrument_type):
        items: tuple[
            ListedEquityInstrument | DerivativeInstrumentRecord, ...
        ] = tuple(
            sorted(
                (
                    ListedEquityInstrument(
                        token=instrument.token,
                        symbol=instrument.normalized_symbol,
                        name=instrument.name,
                        exchange=instrument.exchange,
                        tick_size=instrument.tick_size,
                    )
                    for instrument in instruments
                ),
                key=lambda item: (item.symbol, item.name, item.token),
            )
        )
    else:
        items = tuple(
            sorted(
                (
                    DerivativeInstrumentRecord(
                        token=instrument.token,
                        symbol=instrument.symbol,
                        name=instrument.name,
                        exchange=instrument.exchange,
                        instrument_type=instrument.instrument_type,
                        underlying=instrument.underlying,
                        expiry=instrument.expiry,
                        strike=instrument.strike,
                        lot_size=instrument.lot_size,
                        tick_size=instrument.tick_size,
                        option_type=instrument.option_type,
                        asset_class=instrument.asset_class,
                        asset_type=instrument.asset_type,
                        derivative_kind=instrument.derivative_kind,
                    )
                    for instrument in instruments
                ),
                key=lambda item: (
                    item.underlying,
                    expiry_sort_key(item.expiry or ""),
                    item.strike is None,
                    item.strike or 0.0,
                    item.option_type or "",
                    item.symbol,
                    item.token,
                ),
            )
        )

    return InstrumentBucket(
        exchange=exchange,
        instrument_type=instrument_type,
        asset_class=first.asset_class,
        asset_type=first.asset_type,
        derivative_kind=first.derivative_kind,
        items=items,
    )


def _select_derivative_exchange_view(
    *,
    exchange_catalogs: dict[str, ExchangeInstrumentCatalog],
    exchange: str | None,
    instrument_type: str | None,
    value_selector,
) -> dict[str, dict[str, list[str]]]:
    result: dict[str, dict[str, list[str]]] = {}

    for exchange_key, exchange_catalog in sorted(exchange_catalogs.items()):
        if exchange and exchange_key != exchange.upper().strip():
            continue
        derivative_catalog = exchange_catalog.derivative_catalog
        if derivative_catalog is None:
            continue

        type_map: dict[str, list[str]] = {}
        for instrument_type_key, families in sorted(
            derivative_catalog.families_by_instrument_type.items()
        ):
            if (
                instrument_type
                and instrument_type_key != instrument_type.upper().strip()
            ):
                continue
            values = {
                symbol
                for family in families.values()
                for symbol in value_selector(family)
            }
            type_map[instrument_type_key] = sorted(values)

        if type_map:
            result[exchange_key] = type_map

    return result


def _validate_page_request(*, offset: int, limit: int) -> None:
    if offset < 0:
        raise ValueError("offset must be non-negative")
    if limit <= 0:
        raise ValueError("limit must be positive")


def _is_equity_resolution_candidate(instrument: AngelInstrument) -> bool:
    if (
        instrument.classification.asset_class == AssetClass.EQUITY
        and instrument.classification.asset_type == AssetType.STOCK
    ):
        return True
    return (
        instrument.exchange in {"NSE", "BSE"}
        and instrument.instrument_type == "EQ"
        and instrument.expiry is None
        and instrument.strike is None
        and instrument.option_type is None
    )


def _is_compact_equity_bucket(
    instrument: AngelInstrument,
    instrument_type: str,
) -> bool:
    return (
        instrument.exchange in {"NSE", "BSE"}
        and instrument_type in {"", "EQ"}
        and instrument.is_listed_stock
    )


def _equity_symbol_candidates(symbol: str) -> tuple[str, ...]:
    normalized_symbol = symbol.upper().strip()
    candidates = [normalized_symbol]

    if not normalized_symbol.endswith("-EQ"):
        candidates.append("{0}-EQ".format(normalized_symbol))

    return tuple(dict.fromkeys(candidates))


def _preferred_equity_symbol(symbol: str) -> str:
    normalized_symbol = symbol.upper().strip()
    if normalized_symbol.endswith("-EQ"):
        return normalized_symbol
    return "{0}-EQ".format(normalized_symbol)


def _dedupe_instruments(
    instruments: list[AngelInstrument],
) -> list[AngelInstrument]:
    unique_by_token: dict[str, AngelInstrument] = {}
    for instrument in instruments:
        unique_by_token[instrument.token] = instrument
    return list(unique_by_token.values())


__all__ = [
    "AngelInstrumentMaster",
    "DEFAULT_SCRIP_MASTER_URL",
]
