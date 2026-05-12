from abc import ABC, abstractmethod


class RestBroker(ABC):

    @abstractmethod
    def get_candles(self, *args, **kwargs): ...

    @abstractmethod
    def get_ltp(self, *args, **kwargs): ...

    @abstractmethod
    def get_quote(self, *args, **kwargs): ...
