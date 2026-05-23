"""Account lifecycle contract for broker adapters."""

from abc import ABC, abstractmethod


class BrokerAccount(ABC):
    """Define the minimum account lifecycle for a broker."""

    broker_name: str
    region: str

    @abstractmethod
    def login(self, *args, **kwargs) -> None:
        """Open or authenticate a broker session."""
        ...

    @abstractmethod
    def logout(self, *args, **kwargs) -> None:
        """Close or invalidate a broker session."""
        ...
