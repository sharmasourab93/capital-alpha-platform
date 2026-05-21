from abc import ABC, abstractclassmethod
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class BaseScripData(ABC):
    exchange: str
    token: int
    symbol: str
    name: str

    def __str__(self):
        return f"{self.exchange}: {self.name}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @abstractclassmethod
    def from_row(cls, row: dict[str, Any]) -> "BaseScripData":
        raise NotImplementedError()


@dataclass(frozen=True, slots=True)
class StockExchangeList(ABC):
    stocks: dict[str, BaseScripData]
    indices: dict[str, BaseScripData]
    others: dict[str, BaseScripData]
    exchange: str
    region: str = "INDIA"

    def get_all_stocks_meta_data(self) -> dict[str, BaseScripData]:
        return self.stocks

    def get_all_indices_meta_data(self) -> dict[str, BaseScripData]:
        return self.indices

    def get_all_others_meta_data(self) -> dict[str, BaseScripData]:
        return self.others

    def get_stock(self, key: str) -> BaseScripData | None:
        return self.stocks.get(key)

    def get_index(self, key: str) -> BaseScripData | None:
        return self.indices.get(key)

    def get_others(self, key: str) -> BaseScripData | None:
        return self.others.get(key)

    @property
    def all_stocks(self) -> list[str]:
        return [str(stock) for stock in self.stocks.values()]

    @property
    def all_indices(self) -> list[str]:
        return [str(index) for index in self.indices.values()]

    @property
    def all_others(self) -> list[str]:
        return [str(other) for other in self.others.values()]

    @property
    def get_all_scrips(self) -> list[str]:
        return self.all_stocks + self.all_indices


def parse_int(value: Any) -> int:
    return int(float(str(value)))
