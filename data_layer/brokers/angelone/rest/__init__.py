from .errors import AngelOneSmartApiRestBrokerError
from .instrument_master import AngelInstrument, AngelInstrumentMaster

__all__ = [
    "AngelInstrument",
    "AngelInstrumentMaster",
    "AngelOneSmartApiRestBroker",
    "AngelOneSmartApiRestBrokerError",
]


def __getattr__(name: str):
    if name == "AngelOneSmartApiRestBroker":
        from .smartapi_rest_broker import AngelOneSmartApiRestBroker

        return AngelOneSmartApiRestBroker
    raise AttributeError(name)
