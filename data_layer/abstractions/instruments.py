"""Broker-neutral instrument metadata contracts."""

from abc import ABC, abstractclassmethod
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class BaseScripData(ABC):
    """Base identity for a broker instrument."""

    exchange: str
    token: int
    symbol: str
    name: str

    def __str__(self):
        """Return a display label for the scrip."""
        return f"{self.exchange}: {self.name}"

    def to_dict(self) -> dict[str, Any]:
        """Return the scrip metadata as a dictionary."""
        return asdict(self)

    @abstractclassmethod
    def from_row(cls, row: dict[str, Any]) -> "BaseScripData":
        """Build broker-specific scrip metadata from one source row."""
        raise NotImplementedError()


@dataclass(frozen=True, slots=True)
class StockExchangeList(ABC):
    """Grouped instrument metadata for a single exchange."""

    stocks: dict[str, BaseScripData]
    indices: dict[str, BaseScripData]
    others: dict[str, BaseScripData]
    exchange: str
    region: str = "INDIA"

    def get_all_stocks_meta_data(self) -> dict[str, BaseScripData]:
        """Return all stock metadata keyed by lookup name."""
        return self.stocks

    def get_all_indices_meta_data(self) -> dict[str, BaseScripData]:
        """Return all index metadata keyed by lookup name."""
        return self.indices

    def get_all_others_meta_data(self) -> dict[str, BaseScripData]:
        """Return all other scrip metadata keyed by lookup name."""
        return self.others

    def get_stock(self, key: str) -> BaseScripData | None:
        """Return stock metadata for the provided key."""
        return self.stocks.get(key)

    def get_index(self, key: str) -> BaseScripData | None:
        """Return index metadata for the provided key."""
        return self.indices.get(key)

    def get_others(self, key: str) -> BaseScripData | None:
        """Return other scrip metadata for the provided key."""
        return self.others.get(key)

    @property
    def all_stocks(self) -> list[str]:
        """Return display labels for all stocks."""
        return [str(stock) for stock in self.stocks.values()]

    @property
    def all_indices(self) -> list[str]:
        """Return display labels for all indices."""
        return [str(index) for index in self.indices.values()]

    @property
    def all_others(self) -> list[str]:
        """Return display labels for all other scrips."""
        return [str(other) for other in self.others.values()]

    @property
    def all_scrips(self) -> list[str]:
        """Return display labels for stocks and indices."""
        return self.all_stocks + self.all_indices


def parse_int(value: Any) -> int:
    """Parse int-like source values, including numeric strings."""
    return int(float(str(value)))
