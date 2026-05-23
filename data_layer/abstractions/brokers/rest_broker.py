from abc import abstractmethod

from data_layer.abstractions.brokers.account import BrokerAccount


class RestBroker(BrokerAccount):

    @abstractmethod
    def get_candles(self, *args, **kwargs): ...

    @abstractmethod
    def get_ltp(self, *args, **kwargs): ...

    @abstractmethod
    def get_quote(self, *args, **kwargs): ...
