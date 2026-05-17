from __future__ import annotations

from typing import Any

from data_layer.abstractions.brokers.rest_broker import RestBroker
from data_layer.brokers.angelone.rest.angel_instrument import (
    AngelOneBroker,
    AngelOneStock,
)


class AngelRestBroker(RestBroker):
    broker_name = "angelone"
    capabilities = {
        "supports_rest_quotes": False,
        "supports_rest_candles": False,
        "supports_rest_instruments": True,
    }

    def __init__(self) -> None:
        self.instruments = AngelOneBroker.from_url()

    def get_scrip(self, exchange: str, key: str) -> AngelOneStock | None:
        return self.instruments.get_scrip(exchange, key)

    def get_all_scrips(
        self, exchange: str = "NSE"
    ) -> tuple[AngelOneStock, ...]:
        return self.instruments.get_all_scrips(exchange)

    def get_candles(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "Angel One candle REST calls are not wired yet"
        )

    def get_ltp(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("Angel One LTP REST calls are not wired yet")

    def get_quote(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError(
            "Angel One quote REST calls are not wired yet"
        )
