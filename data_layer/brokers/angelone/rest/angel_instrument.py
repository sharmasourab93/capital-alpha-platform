"""AngelOne instrument master parsing and lookup models."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Self
from urllib.request import urlopen

from data_layer.abstractions.instruments import (
    BaseScripData,
    StockExchangeList,
    parse_int,
)

ANGEL_SCRIP_MASTER_URL = (
    "https://margincalculator.angelbroking.com/OpenAPI_File/files/"
    "OpenAPIScripMaster.json"
)


@dataclass(frozen=True, slots=True)
class AngelOneIndex(BaseScripData):
    """AngelOne index metadata."""

    instrumenttype: str

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "AngelOneIndex":
        """Build index metadata from one AngelOne scrip-master row."""

        return cls(
            exchange=str(row.get("exch_seg").upper()),
            instrumenttype=str(row.get("instrumenttype")),
            symbol=str(row.get("symbol")).upper(),
            name=(row.get("name")).upper(),
            token=parse_int(row.get("token")),
        )


@dataclass(frozen=True, slots=True)
class AngelOneStock(BaseScripData):
    """AngelOne stock metadata."""

    ticksize: str

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "AngelOneStock":
        """Build stock metadata from one AngelOne scrip-master row."""
        return cls(
            exchange=str(row.get("exch_seg")).upper(),
            ticksize=int(row.get("tick_size")),
            symbol=str(row.get("symbol")).upper(),
            name=str(row.get("name")).upper(),
            token=parse_int(row.get("token")),
        )


@dataclass(frozen=True, slots=True)
class AngelOneOtherScrip(BaseScripData):
    """AngelOne non-stock and non-index scrip metadata."""

    instrumenttype: str
    ticksize: str

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "AngelOneOtherScrip":
        """Build other-scrip metadata from one AngelOne row."""
        return cls(
            exchange=str(row.get("exch_seg")).upper(),
            instrumenttype=str(row.get("instrumenttype")).upper(),
            ticksize=int(row.get("tick_size")),
            token=parse_int(row.get("token")),
            symbol=str(row.get("symbol")).upper(),
            name=str(row.get("name")).upper(),
        )


@dataclass(frozen=True, slots=True)
class AngelOneNSE(StockExchangeList):
    """NSE-specific AngelOne instrument group."""

    exchange: str = "NSE"


@dataclass(frozen=True, slots=True)
class AngelOneBSE(StockExchangeList):
    """BSE-specific AngelOne instrument group."""

    exchange: str = "BSE"


@dataclass(frozen=True, slots=True)
class AngelOneInstruments:
    """Parsed AngelOne instrument master grouped by exchange."""

    nse: AngelOneNSE
    bse: AngelOneBSE

    @property
    def nse_stocks(self):
        """Return NSE stock metadata."""
        return self.nse.stocks

    @property
    def bse_stocks(self):
        """Return BSE stock metadata."""
        return self.bse.stocks

    @property
    def nse_indices(self):
        """Return NSE index metadata."""
        return self.nse.indices

    @property
    def bse_indices(self):
        """Return BSE index metadata."""
        return self.bse.indices

    @classmethod
    def iterate_over_scrips(
        cls, data: Iterable[dict[str, Any]]
    ) -> AngelOneInstruments:
        """Group AngelOne scrip-master rows by exchange and type."""
        nse_stocks: dict[str, AngelOneStock] = {}
        bse_stocks: dict[str, AngelOneStock] = {}
        nse_indices: dict[str, AngelOneIndex] = {}
        bse_indices: dict[str, AngelOneIndex] = {}
        nse_others: dict[str, AngelOneOtherScrip] = {}
        bse_others: dict[str, AngelOneOtherScrip] = {}

        implemented_exchanges = ("NSE", "BSE")
        mapping = {
            ("NSE", "EQ"): nse_stocks,
            ("BSE", "EQ"): bse_stocks,
            ("NSE", "AMXIDX"): nse_indices,
            ("BSE", "AMXIDX"): bse_indices,
            ("NSE", ""): nse_others,
            ("BSE", ""): bse_others,
        }

        for row in data:
            exchange = str(row.get("exch_seg", "")).upper()
            name = str(row.get("name")).upper()
            instrument_type = str(row.get("instrumenttype", "")).strip()
            symbol = str(row.get("symbol", "")).upper()
            instrument_type = (
                "EQ" if symbol.endswith("-EQ") else instrument_type
            )
            is_equity = True if instrument_type == "EQ" else False
            is_index = True if instrument_type == "AMXIDX" else False

            if exchange in implemented_exchanges:
                if is_equity:
                    mapping[(exchange, instrument_type)].update(
                        {name: AngelOneStock.from_row(row)}
                    )
                elif is_index:
                    mapping[(exchange, instrument_type)].update(
                        {name: AngelOneIndex.from_row(row)}
                    )
                else:
                    mapping[(exchange, instrument_type)].update(
                        {name: AngelOneOtherScrip.from_row(row)}
                    )

        return cls(
            nse=AngelOneNSE(
                stocks=nse_stocks, indices=nse_indices, others=nse_others
            ),
            bse=AngelOneBSE(
                stocks=bse_others, indices=bse_indices, others=bse_stocks
            ),
        )

    @classmethod
    def from_scrip_master_rows(cls, rows: Iterable[dict[str, Any]]) -> Self:
        """Build instruments from parsed scrip-master rows."""
        return cls.iterate_over_scrips(rows)

    @classmethod
    def from_json(cls, payload: str | bytes) -> Self:
        """Build instruments from AngelOne scrip-master JSON."""
        rows = json.loads(payload)
        if not isinstance(rows, list):
            raise ValueError("Angel scrip master payload must be a JSON list")
        return cls.from_scrip_master_rows(rows)

    @classmethod
    def from_file(cls, path: str | Path) -> Self:
        """Build instruments from a local scrip-master file."""
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    @classmethod
    def from_url(cls, url: str = ANGEL_SCRIP_MASTER_URL) -> Self:
        """Build instruments from the AngelOne scrip-master URL."""
        with urlopen(url, timeout=30) as response:
            return cls.from_json(response.read())


class AngelOneBroker:
    """AngelOne instrument lookup facade."""

    def __init__(self, instrument_master: AngelOneInstruments):
        """Store a parsed AngelOne instrument master."""
        self.instrument_master = instrument_master

    def get_exchange(self, exchange: str) -> AngelOneNSE | AngelOneBSE | None:
        """Return parsed exchange data by exchange code."""
        exchange = exchange.upper()

        if exchange == self.instrument_master.nse.exchange:
            return self.instrument_master.nse

        if exchange == self.instrument_master.bse.exchange:
            return self.instrument_master.bse

        return None

    def get_scrip(
        self, exchange: str, key: str
    ) -> AngelOneStock | AngelOneIndex | AngelOneOtherScrip | None:
        """Return a scrip by name from the selected exchange."""
        exchange_data = self.get_exchange(exchange)
        if exchange_data is None:
            return None

        key = key.upper()

        return (
            exchange_data.get_stock(key)
            or exchange_data.get_index(key)
            or exchange_data.get_others(key)
        )

    def get_all_scrips(self, exchange: str = "NSE") -> list[str]:
        """Return stock and index display labels for an exchange."""
        exchange_data = self.get_exchange(exchange)
        if exchange_data is None:
            return []

        return exchange_data.all_scrips

    @classmethod
    def from_scrip_master_rows(cls, rows: Iterable[dict[str, Any]]) -> Self:
        """Build the broker lookup from parsed scrip-master rows."""
        return cls(AngelOneInstruments.from_scrip_master_rows(rows))

    @classmethod
    def from_json(cls, payload: str | bytes) -> Self:
        """Build the broker lookup from scrip-master JSON."""
        return cls(AngelOneInstruments.from_json(payload))

    @classmethod
    def from_file(cls, path: str | Path) -> Self:
        """Build the broker lookup from a local scrip-master file."""
        return cls(AngelOneInstruments.from_file(path))

    @classmethod
    def from_url(cls, url: str = ANGEL_SCRIP_MASTER_URL) -> Self:
        """Build the broker lookup from the AngelOne scrip-master URL."""
        return cls(AngelOneInstruments.from_url(url))


AngelInstrument = AngelOneBroker


if __name__ == "__main__":
    angel_one = AngelOneBroker.from_url()
    print(angel_one)
