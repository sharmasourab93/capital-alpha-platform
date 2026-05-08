from __future__ import annotations

from SmartApi import SmartConnect


class SmartApiTransport:
    def __init__(self, client: SmartConnect) -> None:
        self._client = client

    def get_market_data(self, payload: dict) -> dict:
        return self._client.getMarketData(**payload)

    def get_candle_data(self, payload: dict) -> dict:
        return self._client.getCandleData(payload)

    def search_scrip(self, exchange: str, query: str) -> dict:
        return self._client.searchScrip(exchange, query)


__all__ = ["SmartApiTransport"]
