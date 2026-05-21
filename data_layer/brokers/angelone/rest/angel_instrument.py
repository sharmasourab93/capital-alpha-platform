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
    instrumenttype: str

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "AngelOneIndex":

        return cls(
            exchange=str(row.get("exch_seg").upper()),
            instrumenttype=str(row.get("instrumenttype")),
            symbol=str(row.get("symbol")).upper(),
            name=(row.get("name")).upper(),
            token=parse_int(row.get("token"))
        )


@dataclass(frozen=True, slots=True)
class AngelOneStock(BaseScripData):
    ticksize: str

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "AngelOneStock":
        return cls(
            exchange=str(row.get("exch_seg")).upper(),
            ticksize=row.get("tick_size"),
            symbol=str(row.get("symbol")).upper(),
            name=str(row.get("name")).upper(),
            token=parse_int(row.get("token"))
        )


@dataclass(frozen=True, slots=True)
class AngelOneOtherScrip(BaseScripData):
    instrumenttype: str
    ticksize: str

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "AngelOneOtherScrip":
        return cls(
            exchange=str(row.get("exch_seg")).upper(),
            instrumenttype=str(row.get("instrumenttype")).upper(),
            ticksize=row.get("tick_size"),
            token=parse_int(row.get("token")),
            symbol=str(row.get("symbol")).upper(),
            name=str(row.get("name")).upper(),
        )


@dataclass(frozen=True, slots=True)
class AngelOneNSE(StockExchangeList):
    exchange: str = "NSE"


@dataclass(frozen=True, slots=True)
class AngelOneBSE(StockExchangeList):
    exchange: str = "BSE"


@dataclass(frozen=True, slots=True)
class AngelOneInstruments:
    nse: AngelOneNSE
    bse: AngelOneBSE

    @property
    def nse_stocks(self):
        return self.nse.stocks

    @property
    def bse_stocks(self):
        return self.bse.stocks

    @property
    def nse_indices(self):
        return self.nse.indices

    @property
    def bse_indices(self):
        return self.bse.indices

    @classmethod
    def iterate_over_scrips(
        cls, data: Iterable[dict[str, Any]]
    ) -> AngelOneInstruments:
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
                stocks=bse_stocks, indices=bse_indices, others=bse_others
            ),
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
