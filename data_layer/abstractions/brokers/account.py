from abc import ABC, abstractmethod


class BrokerAccount(ABC):
    broker_name: str
    region: str

    @abstractmethod
    def login(self, *args, **kwargs) -> None: ...

    @abstractmethod
    def logout(self, *args, **kwargs) -> None: ...
