"""REST broker contract for market-data adapters."""

from abc import abstractmethod

from data_layer.abstractions.brokers.account import BrokerAccount


class RestBroker(BrokerAccount):
    """Define the REST market-data operations brokers must expose."""

    @abstractmethod
    def get_candles(self, *args, **kwargs):
        """Return historical candle data."""
        ...

    @abstractmethod
    def get_ltp(self, *args, **kwargs):
        """Return last traded price data."""
        ...

    @abstractmethod
    def get_quote(self, *args, **kwargs):
        """Return quote data for one or more instruments."""
        ...
