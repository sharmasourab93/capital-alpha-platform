from __future__ import annotations

from collections.abc import Sequence

from data_layer.abstractions.instruments import (
    BaseScripData,
    StockExchangeList,
)
from data_layer.brokers.angelone.rest.angel_instrument import AngelOneBroker
from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
)


class AngelInstrumentResolver:
    def __init__(self, instruments: AngelOneBroker) -> None:
        self.instruments = instruments

    def get_scrip(self, exchange: str, key: str) -> BaseScripData | None:
        exchange_data = self.instruments.get_exchange(exchange)
        if exchange_data is None:
            return None

        normalized_key = key.upper()
        return (
            exchange_data.get_stock(normalized_key)
            or exchange_data.get_index(normalized_key)
            or exchange_data.get_others(normalized_key)
            or self._find_by_symbol(exchange_data, normalized_key)
        )

    def get_all_scrips(self, exchange: str = "NSE") -> list[str]:
        return self.instruments.get_all_scrips(exchange)

    def require_scrip(self, exchange: str, key: str) -> BaseScripData:
        scrip = self.get_scrip(exchange, key)
        if scrip is None:
            raise AngelOneSmartApiRestBrokerError(
                "Unknown Angel One scrip",
                {"exchange": exchange, "key": key},
            )
        return scrip

    def require_scrips(
        self, exchange: str, key: str | Sequence[str]
    ) -> list[BaseScripData]:
        keys = [key] if isinstance(key, str) else list(key)
        if not keys:
            raise AngelOneSmartApiRestBrokerError(
                "At least one Angel One scrip key is required",
                {"exchange": exchange},
            )
        return [self.require_scrip(exchange, scrip_key) for scrip_key in keys]

    def _find_by_symbol(
        self, exchange_data: StockExchangeList, key: str
    ) -> BaseScripData | None:
        for scrip in (
            *exchange_data.stocks.values(),
            *exchange_data.indices.values(),
            *exchange_data.others.values(),
        ):
            if scrip.name == key:
                return scrip
        return None


__all__ = ["AngelInstrumentResolver"]
