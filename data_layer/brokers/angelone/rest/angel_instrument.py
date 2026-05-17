from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Self
from urllib.request import urlopen

from data_layer.abstractions.instruments import (
    BaseScripData,
    StockList,
    parse_int,
)

ANGEL_SCRIP_MASTER_URL = (
    "https://margincalculator.angelbroking.com/OpenAPI_File/files/"
    "OpenAPIScripMaster.json"
)


@dataclass(frozen=True, slots=True)
class AngelOneIndex(BaseScripData):
    instrumenttype: str


@dataclass(frozen=True, slots=True)
class AngelOneStock(BaseScripData):
    ticksize: str


@dataclass(frozen=True, slots=True)
class AngelOneDerivative(BaseScripData):
    instrumenttype: str
    expiry: str
    strike: int | float
    lotsize: int | float
    tick_size: int | float


@dataclass(frozen=True, slots=True)
class AngelOneNSEList(StockList):
    @property
    def exchange_segment(self) -> str:
        return "NSE"

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(stock.symbol for stock in self.stocks.values())

    def get_by_symbol(self, symbol: str) -> AngelOneStock | None:
        lookup_key = symbol.upper()
        stock = self.stocks.get(lookup_key)
        if stock is not None:
            return stock

        nse_symbol = f"{lookup_key}-EQ"
        for stock in self.stocks.values():
            if stock.symbol.upper() in {lookup_key, nse_symbol}:
                return stock
        return None

    def get_all_scrips(self) -> tuple[AngelOneStock, ...]:
        return tuple(self.stocks.values())

    def get_by_token(self, token: int | str) -> AngelOneStock | None:
        token_value = parse_int(token)
        for stock in self.stocks.values():
            if stock.token == token_value:
                return stock
        return None

    def get_token(self, symbol: str) -> int | None:
        stock = self.get_by_symbol(symbol)
        if stock is None:
            return None
        return stock.token


@dataclass(frozen=True, slots=True)
class AngelOneBSEList(StockList):
    @property
    def exchange_segment(self) -> str:
        return "BSE"

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(stock.symbol for stock in self.stocks.values())

    def get_by_symbol(self, symbol: str) -> AngelOneStock | None:
        lookup_key = symbol.upper()
        stock = self.stocks.get(lookup_key)
        if stock is not None:
            return stock

        for stock in self.stocks.values():
            if stock.symbol.upper() == lookup_key:
                return stock
        return None

    def get_all_scrips(self) -> tuple[AngelOneStock, ...]:
        return tuple(self.stocks.values())

    def get_by_token(self, token: int | str) -> AngelOneStock | None:
        token_value = parse_int(token)
        for stock in self.stocks.values():
            if stock.token == token_value:
                return stock
        return None

    def get_token(self, symbol: str) -> int | None:
        stock = self.get_by_symbol(symbol)
        if stock is None:
            return None
        return stock.token


@dataclass(frozen=True, slots=True)
class AngelOneInstruments:
    nse: AngelOneNSEList
    bse: AngelOneBSEList

    @property
    def exchange_segments(self) -> tuple[str, ...]:
        return (self.nse.exchange_segment, self.bse.exchange_segment)

    def get_exchange(
        self, exchange: str
    ) -> AngelOneNSEList | AngelOneBSEList | None:
        exchange_segment = exchange.upper()
        if exchange_segment == self.nse.exchange_segment:
            return self.nse
        if exchange_segment == self.bse.exchange_segment:
            return self.bse
        return None

    def get_scrip(self, exchange: str, key: str) -> AngelOneStock | None:
        exchange_list = self.get_exchange(exchange)
        if exchange_list is None:
            return None
        return exchange_list.get_by_symbol(key)

    def get_all_scrips(
        self, exchange: str = "NSE"
    ) -> tuple[AngelOneStock, ...]:
        exchange_list = self.get_exchange(exchange)
        if exchange_list is None:
            return ()
        return exchange_list.get_all_scrips()

    @property
    def nse_stock(self) -> AngelOneNSEList:
        return self.nse

    @property
    def bse_stock(self) -> AngelOneBSEList:
        return self.bse

    @classmethod
    def iterate_over_scrips(
        cls, data: Iterable[dict[str, Any]]
    ) -> AngelOneInstruments:
        nse_stocks: dict[str, AngelOneStock] = {}
        bse_stocks: dict[str, AngelOneStock] = {}
        nse_indices: dict[str, AngelOneIndex] = {}
        bse_indices: dict[str, AngelOneIndex] = {}

        for row in data:
            exchange = str(row.get("exch_seg", "")).upper()
            if exchange not in {"NSE", "BSE"}:
                continue

            if cls._is_stock_row(row, exchange):
                stock = cls._stock_from_row(row)
                stocks = nse_stocks if exchange == "NSE" else bse_stocks
                if stock.name in stocks:
                    raise ValueError(
                        "Duplicate Angel instrument stock key "
                        f"{stock.name!r} in {exchange}"
                    )

                stocks[stock.name] = stock
                continue

            index = cls._index_from_row(row)
            indices = nse_indices if exchange == "NSE" else bse_indices
            indices[index.symbol] = index

        return cls(
            nse=AngelOneNSEList(stocks=nse_stocks, indices=nse_indices),
            bse=AngelOneBSEList(stocks=bse_stocks, indices=bse_indices),
        )

    @staticmethod
    def _is_stock_row(row: dict[str, Any], exchange: str) -> bool:
        instrument_type = str(row.get("instrumenttype", "")).strip()
        if instrument_type != "":
            return False

        symbol = str(row.get("symbol", "")).strip().upper()
        if exchange == "NSE":
            return symbol.endswith("-EQ")

        if exchange == "BSE":
            return parse_int(row.get("tick_size", 0)) > 0

        return False

    @staticmethod
    def _stock_from_row(row: dict[str, Any]) -> AngelOneStock:
        return AngelOneStock(
            exchange=str(row.get("exch_seg", "")).upper(),
            # instrumenttype=str(row.get("instrumenttype", "")),
            token=parse_int(row.get("token")),
            symbol=str(row.get("symbol", "")),
            name=str(row.get("name", "")),
            ticksize=str(row.get("tick_size", "")),
        )

    @staticmethod
    def _index_from_row(row: dict[str, Any]) -> AngelOneIndex:
        return AngelOneIndex(
            exchange=str(row.get("exch_seg", "")).upper(),
            instrumenttype=str(row.get("instrumenttype", "")),
            token=parse_int(row.get("token")),
            symbol=str(row.get("symbol", "")),
            name=str(row.get("name", "")),
        )

    @classmethod
    def from_scrip_master_rows(cls, rows: Iterable[dict[str, Any]]) -> Self:
        return cls.iterate_over_scrips(rows)

    @classmethod
    def from_json(cls, payload: str | bytes) -> Self:
        rows = json.loads(payload)
        if not isinstance(rows, list):
            raise ValueError("Angel scrip master payload must be a JSON list")
        return cls.from_scrip_master_rows(rows)

    @classmethod
    def from_file(cls, path: str | Path) -> Self:
        return cls.from_json(Path(path).read_text(encoding="utf-8"))

    @classmethod
    def from_url(cls, url: str = ANGEL_SCRIP_MASTER_URL) -> Self:
        with urlopen(url, timeout=30) as response:
            return cls.from_json(response.read())


class AngelOneBroker:
    def __init__(self, instrument_master: AngelOneInstruments):
        self.instrument_master = instrument_master

    def get_exchange(
        self, exchange: str
    ) -> AngelOneNSEList | AngelOneBSEList | None:
        return self.instrument_master.get_exchange(exchange)

    def get_scrip(self, exchange: str, key: str) -> AngelOneStock | None:
        return self.instrument_master.get_scrip(exchange, key)

    def get_all_scrips(
        self, exchange: str = "NSE"
    ) -> tuple[AngelOneStock, ...]:
        return self.instrument_master.get_all_scrips(exchange)

    @classmethod
    def from_scrip_master_rows(cls, rows: Iterable[dict[str, Any]]) -> Self:
        return cls(AngelOneInstruments.from_scrip_master_rows(rows))

    @classmethod
    def from_json(cls, payload: str | bytes) -> Self:
        return cls(AngelOneInstruments.from_json(payload))

    @classmethod
    def from_file(cls, path: str | Path) -> Self:
        return cls(AngelOneInstruments.from_file(path))

    @classmethod
    def from_url(cls, url: str = ANGEL_SCRIP_MASTER_URL) -> Self:
        return cls(AngelOneInstruments.from_url(url))


AngelInstrument = AngelOneBroker
