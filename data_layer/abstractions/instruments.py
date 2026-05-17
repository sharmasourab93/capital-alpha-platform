from abc import ABC
from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass(frozen=True, slots=True)
class BaseScripData(ABC):
    exchange: str
    token: int
    symbol: str
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class StockList(ABC):
    stocks: List[Dict[str, Any]]
    indices: List[Dict[str, Any]]

    @property
    def all_stocks(self) -> List[str]:
        return list(self.stocks.keys())

    def all_indices(self) -> List[Dict[str, Any]]:
        return list(self.indices.keys())


@dataclass(frozen=True, slots=True)
class DerivativeList(ABC):
    stocks: List[Dict[str, Any]]


def parse_int(value: Any) -> int:
    return int(float(str(value)))
