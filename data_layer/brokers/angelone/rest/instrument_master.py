from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import DefaultDict

from requests import get

from data_layer.abs import DerivativeInstrumentRequest

DEFAULT_SCRIP_MASTER_URL = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
DERIVATIVE_EXCHANGES = frozenset({"NFO", "BFO", "CDS", "MCX"})


@dataclass(frozen=True)
class AngelInstrument:
    token: str
    symbol: str
    name: str
    exchange: str
    exchange_segment: str
    instrument_type: str
    expiry: str | None
    strike: float | None
    lot_size: int | None
    option_type: str | None

    @property
    def underlying(self) -> str:
        return self.name.upper()

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

    def __post_init__(self) -> None:
        self.by_token = {}
        self.by_symbol_exchange = defaultdict(list)

        for instrument in self.instruments:
            self.by_token[instrument.token] = instrument
            self.by_symbol_exchange[
                (instrument.symbol.upper(), instrument.exchange.upper())
            ].append(instrument)

    @classmethod
    def from_url(
        cls,
        url: str = DEFAULT_SCRIP_MASTER_URL,
        timeout_seconds: float = 30.0,
    ) -> AngelInstrumentMaster:
        rows = cls._download_rows(url, timeout_seconds)
        return cls.from_rows(rows)

    @classmethod
    def from_rows(cls, rows: list[dict]) -> AngelInstrumentMaster:
        instruments = [cls._row_to_instrument(row) for row in rows]
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

        return AngelInstrument(
            token=str(row["token"]),
            symbol=symbol,
            name=row.get("name") or "",
            exchange=exchange,
            exchange_segment=exchange,
            instrument_type=instrument_type,
            expiry=row.get("expiry") or None,
            strike=(
                float(row["strike"])
                if row.get("strike") not in ("", None)
                else None
            ),
            lot_size=(
                int(row["lotsize"])
                if row.get("lotsize") not in ("", None)
                else None
            ),
            option_type=_extract_option_type(symbol),
        )

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
        exchange_map: dict[str, dict[str, str]] = {}

        for instrument in self.instruments:
            exchange_bucket = exchange_map.setdefault(instrument.exchange, {})
            exchange_bucket.setdefault(instrument.symbol, instrument.name)

        return exchange_map

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

        if not matches:
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

        if len(matches) > 1:
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

        return matches[0]


def _extract_option_type(symbol: str) -> str | None:
    if symbol.endswith("CE"):
        return "CE"
    if symbol.endswith("PE"):
        return "PE"
    return None


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
