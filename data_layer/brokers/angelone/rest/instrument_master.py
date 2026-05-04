from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
import re
from threading import Lock
from typing import DefaultDict

from requests import get

from data_layer.abs import DerivativeInstrumentRequest

DEFAULT_SCRIP_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
DERIVATIVE_EXCHANGES = frozenset({"NFO", "BFO", "CDS", "MCX"})
_INSTRUMENT_MASTER_CACHE_LOCK = Lock()
_INSTRUMENT_MASTER_CACHE: dict[tuple[str, float], "AngelInstrumentMaster"] = {}


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
    option_type: str | None

    @property
    def is_derivative(self) -> bool:
        return self.exchange in DERIVATIVE_EXCHANGES

    @property
    def is_equity_like(self) -> bool:
        return (
            not self.is_derivative
            and self.expiry is None
            and self.strike is None
            and self.option_type is None
        )

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
            "option_type": self.option_type,
        }


@dataclass
class AngelInstrumentMaster:
    instruments: list[AngelInstrument]
    by_token: dict[str, AngelInstrument] = field(init=False)
    by_symbol_exchange: DefaultDict[tuple[str, str], list[AngelInstrument]] = (
        field(init=False)
    )
    symbol_name_map_by_exchange: dict[str, dict[str, str]] = field(init=False)
    symbol_name_counts_by_exchange: dict[str, int] = field(init=False)

    def __post_init__(self) -> None:
        self.by_token = {}
        self.by_symbol_exchange = defaultdict(list)
        self.symbol_name_map_by_exchange = {}

        for instrument in self.instruments:
            self.by_token[instrument.token] = instrument
            self.by_symbol_exchange[
                (instrument.symbol.upper(), instrument.exchange.upper())
            ].append(instrument)
            exchange_bucket = self.symbol_name_map_by_exchange.setdefault(
                instrument.exchange.upper(),
                {},
            )
            exchange_bucket.setdefault(
                instrument.symbol.upper(), instrument.name
            )

        self.symbol_name_counts_by_exchange = {
            exchange: len(symbol_map)
            for exchange, symbol_map in self.symbol_name_map_by_exchange.items()
        }

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
        instruments: list[AngelInstrument] = []
        for row in rows:
            instrument = cls._try_row_to_instrument(row)
            if instrument is not None:
                instruments.append(instrument)
        return cls(instruments=instruments)

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

    @staticmethod
    def _row_to_instrument(row: dict) -> AngelInstrument:
        symbol = (row.get("symbol") or "").upper()
        exchange = (row.get("exch_seg") or "").upper()
        instrument_type = (row.get("instrumenttype") or "").upper()
        option_type = _extract_option_type(symbol)
        strike = _parse_strike(
            row.get("strike"),
            symbol=symbol,
            instrument_type=instrument_type,
            option_type=option_type,
        )
        name = row.get("name") or ""

        return AngelInstrument(
            token=str(row["token"]),
            symbol=symbol,
            name=name,
            underlying=_normalize_underlying(
                name,
                symbol=symbol,
                instrument_type=instrument_type,
            ),
            exchange=exchange,
            exchange_segment=exchange,
            instrument_type=instrument_type,
            expiry=row.get("expiry") or None,
            strike=strike,
            lot_size=_parse_lot_size(row.get("lotsize")),
            option_type=option_type,
        )

    @classmethod
    def _try_row_to_instrument(cls, row: dict) -> AngelInstrument | None:
        token = row.get("token")
        symbol = row.get("symbol")
        exchange = row.get("exch_seg")
        if token in ("", None) or symbol in ("", None) or exchange in ("", None):
            return None

        try:
            return cls._row_to_instrument(row)
        except (TypeError, ValueError, KeyError):
            return None

    def get_by_token(self, token: str) -> AngelInstrument | None:
        return self.by_token.get(str(token))

    def get_by_symbol_exchange(
        self,
        symbol: str,
        exchange: str,
    ) -> list[AngelInstrument]:
        return self.by_symbol_exchange.get(
            (symbol.upper(), exchange.upper()), []
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
            instrument for instrument in matches if instrument.is_equity_like
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
        return tuple(
            sorted({instrument.exchange for instrument in self.instruments})
        )

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

        if offset < 0:
            raise ValueError("offset must be non-negative")
        if limit <= 0:
            raise ValueError("limit must be positive")

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

    def get_instrument_types(
        self,
        exchange: str | None = None,
    ) -> tuple[str, ...]:
        normalized_exchange = exchange.upper() if exchange else None
        instrument_types = {
            instrument.instrument_type
            for instrument in self.instruments
            if not normalized_exchange
            or instrument.exchange == normalized_exchange
        }
        return tuple(sorted(instrument_types))

    def get_instruments_by_exchange(
        self,
        exchange: str,
    ) -> list[dict[str, str | float | int | None]]:
        normalized_exchange = exchange.upper()
        return [
            instrument.as_dict()
            for instrument in self.instruments
            if instrument.exchange == normalized_exchange
        ]

    def get_derivative_symbols(
        self,
        exchange: str | None = None,
        instrument_type: str | None = None,
    ) -> dict[str, dict[str, list[str]]]:
        normalized_exchange = exchange.upper() if exchange else None
        normalized_instrument_type = (
            instrument_type.upper() if instrument_type else None
        )
        derivative_symbols: dict[str, dict[str, set[str]]] = {}

        for instrument in self.instruments:
            if not instrument.is_derivative:
                continue
            if (
                normalized_exchange
                and instrument.exchange != normalized_exchange
            ):
                continue
            if (
                normalized_instrument_type
                and instrument.instrument_type != normalized_instrument_type
            ):
                continue

            exchange_bucket = derivative_symbols.setdefault(
                instrument.exchange, {}
            )
            symbol_bucket = exchange_bucket.setdefault(
                instrument.instrument_type, set()
            )
            symbol_bucket.add(instrument.symbol)

        return {
            exchange_key: {
                instrument_type_key: sorted(symbols)
                for instrument_type_key, symbols in instrument_type_map.items()
            }
            for exchange_key, instrument_type_map in derivative_symbols.items()
        }

    def get_derivative_expiries(
        self,
        *,
        exchange: str,
        underlying: str,
        instrument_type: str,
    ) -> tuple[str, ...]:
        normalized_exchange = exchange.upper()
        normalized_underlying = underlying.upper()
        normalized_instrument_type = instrument_type.upper()

        expiries = {
            instrument.expiry
            for instrument in self.instruments
            if instrument.is_derivative
            and instrument.exchange == normalized_exchange
            and instrument.underlying == normalized_underlying
            and instrument.instrument_type == normalized_instrument_type
            and instrument.expiry
        }
        return tuple(sorted(expiries, key=_expiry_sort_key))

    def get_derivative_underlyings(
        self,
        *,
        exchange: str | None = None,
        instrument_type: str | None = None,
    ) -> dict[str, dict[str, list[str]]]:
        normalized_exchange = exchange.upper() if exchange else None
        normalized_instrument_type = (
            instrument_type.upper() if instrument_type else None
        )
        derivative_underlyings: dict[str, dict[str, set[str]]] = {}

        for instrument in self.instruments:
            if not instrument.is_derivative:
                continue
            if (
                normalized_exchange
                and instrument.exchange != normalized_exchange
            ):
                continue
            if (
                normalized_instrument_type
                and instrument.instrument_type != normalized_instrument_type
            ):
                continue

            exchange_bucket = derivative_underlyings.setdefault(
                instrument.exchange, {}
            )
            underlying_bucket = exchange_bucket.setdefault(
                instrument.instrument_type, set()
            )
            underlying_bucket.add(instrument.underlying)

        return {
            exchange_key: {
                instrument_type_key: sorted(underlyings)
                for instrument_type_key, underlyings in instrument_type_map.items()
            }
            for exchange_key, instrument_type_map in derivative_underlyings.items()
        }

    def get_derivative_contracts(
        self,
        *,
        exchange: str,
        underlying: str,
        instrument_type: str,
        expiry: str,
        option_type: str | None = None,
    ) -> list[dict[str, str | float | int | None]]:
        normalized_exchange = exchange.upper()
        normalized_underlying = underlying.upper()
        normalized_instrument_type = instrument_type.upper()
        normalized_option_type = option_type.upper() if option_type else None

        contracts_by_symbol: dict[str, dict[str, str | float | int | None]] = {}
        for instrument in self.instruments:
            if not instrument.is_derivative:
                continue
            if instrument.exchange != normalized_exchange:
                continue
            if instrument.underlying != normalized_underlying:
                continue
            if instrument.instrument_type != normalized_instrument_type:
                continue
            if instrument.expiry != expiry:
                continue
            if (
                normalized_option_type is not None
                and instrument.option_type != normalized_option_type
            ):
                continue

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
        normalized_exchange = exchange.upper()
        normalized_underlying = underlying.upper()
        normalized_instrument_type = instrument_type.upper()
        normalized_option_type = option_type.upper() if option_type else None

        strikes = {
            instrument.strike
            for instrument in self.instruments
            if instrument.is_derivative
            and instrument.exchange == normalized_exchange
            and instrument.underlying == normalized_underlying
            and instrument.instrument_type == normalized_instrument_type
            and instrument.expiry == expiry
            and instrument.strike is not None
            and (
                normalized_option_type is None
                or instrument.option_type == normalized_option_type
            )
        }
        return tuple(sorted(strikes))

    def resolve_derivative_instrument(
        self,
        request: DerivativeInstrumentRequest,
    ) -> AngelInstrument:
        normalized_exchange = request.exchange.upper()
        normalized_underlying = request.underlying.upper()
        normalized_instrument_type = request.instrument_type.upper()
        normalized_option_type = (
            request.option_type.upper() if request.option_type else None
        )
        normalized_strike = (
            float(request.strike) if request.strike is not None else None
        )

        matches = [
            instrument
            for instrument in self.instruments
            if instrument.is_derivative
            and instrument.exchange == normalized_exchange
            and instrument.underlying == normalized_underlying
            and instrument.instrument_type == normalized_instrument_type
            and instrument.expiry == request.expiry
            and (
                normalized_strike is None
                or instrument.strike == normalized_strike
            )
            and (
                normalized_option_type is None
                or instrument.option_type == normalized_option_type
            )
        ]
        unique_matches = _dedupe_instruments(matches)

        if not unique_matches:
            raise LookupError(
                "No derivative instrument found for exchange={0}, underlying={1}, "
                "instrument_type={2}, expiry={3}, strike={4}, option_type={5}".format(
                    normalized_exchange,
                    normalized_underlying,
                    normalized_instrument_type,
                    request.expiry,
                    request.strike,
                    normalized_option_type,
                )
            )

        if len(unique_matches) > 1:
            raise LookupError(
                "Multiple derivative instruments found for exchange={0}, underlying={1}, "
                "instrument_type={2}, expiry={3}, strike={4}, option_type={5}".format(
                    normalized_exchange,
                    normalized_underlying,
                    normalized_instrument_type,
                    request.expiry,
                    request.strike,
                    normalized_option_type,
                )
            )

        return unique_matches[0]


def _extract_option_type(symbol: str) -> str | None:
    if symbol.endswith("CE"):
        return "CE"
    if symbol.endswith("PE"):
        return "PE"
    return None


def _parse_strike(
    value,
    *,
    symbol: str,
    instrument_type: str,
    option_type: str | None,
) -> float | None:
    symbol_strike = _extract_strike_from_symbol(
        symbol,
        instrument_type=instrument_type,
        option_type=option_type,
    )
    if symbol_strike is not None:
        return symbol_strike

    if value in ("", None):
        return None

    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    if parsed >= 100000:
        return parsed / 100.0
    return parsed


def _parse_lot_size(value) -> int | None:
    if value in ("", None):
        return None
    return int(value)


def _extract_strike_from_symbol(
    symbol: str,
    *,
    instrument_type: str,
    option_type: str | None,
) -> float | None:
    if option_type is None or "OPT" not in instrument_type:
        return None

    match = re.search(r"\d{2}[A-Z]{3}\d{4}(\d+)(CE|PE)$", symbol)
    if match is None:
        return None

    return float(match.group(1))


def _normalize_underlying(
    value: str,
    *,
    symbol: str,
    instrument_type: str,
) -> str:
    normalized_value = _normalize_underlying_text(value)
    if normalized_value:
        return normalized_value

    inferred_underlying = _infer_underlying_from_symbol(
        symbol,
        instrument_type=instrument_type,
    )
    if inferred_underlying:
        return inferred_underlying

    return _normalize_underlying_text(symbol)


def _normalize_underlying_text(value: str) -> str:
    return " ".join(str(value).upper().split())


def _infer_underlying_from_symbol(
    symbol: str,
    *,
    instrument_type: str,
) -> str:
    if "FUT" not in instrument_type and "OPT" not in instrument_type:
        return ""

    match = re.search(r"^(.*?)(\d{2}[A-Z]{3}\d{4})", symbol)
    if match is None:
        return ""

    return match.group(1).upper().strip()


def _expiry_sort_key(expiry: str) -> tuple[int, datetime | str]:
    try:
        return (0, datetime.strptime(expiry.upper(), "%d%b%Y"))
    except ValueError:
        return (1, expiry)


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
    "AngelInstrument",
    "AngelInstrumentMaster",
    "DEFAULT_SCRIP_MASTER_URL",
    "DERIVATIVE_EXCHANGES",
]
