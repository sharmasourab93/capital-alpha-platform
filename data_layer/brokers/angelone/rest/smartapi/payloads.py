from __future__ import annotations

from dataclasses import dataclass

from data_layer.abstractions.instruments import BaseScripData
from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
)

SUPPORTED_QUOTE_MODES = frozenset({"LTP", "OHLC", "FULL"})


@dataclass(frozen=True, slots=True)
class CandleRequest:
    exchange: str
    symboltoken: str
    interval: str
    fromdate: str
    todate: str

    @classmethod
    def from_scrip(
        cls,
        scrip: BaseScripData,
        interval: str,
        fromdate: str,
        todate: str,
    ) -> "CandleRequest":
        return cls(
            exchange=scrip.exchange,
            symboltoken=str(scrip.token),
            interval=interval,
            fromdate=fromdate,
            todate=todate,
        )

    def to_payload(self) -> dict[str, str]:
        return {
            "exchange": self.exchange,
            "symboltoken": self.symboltoken,
            "interval": self.interval,
            "fromdate": self.fromdate,
            "todate": self.todate,
        }


@dataclass(frozen=True, slots=True)
class LtpRequest:
    exchange: str
    tradingsymbol: str
    symboltoken: str

    @classmethod
    def from_scrip(cls, scrip: BaseScripData) -> "LtpRequest":
        return cls(
            exchange=scrip.exchange,
            tradingsymbol=scrip.symbol,
            symboltoken=str(scrip.token),
        )


@dataclass(frozen=True, slots=True)
class QuoteRequest:
    mode: str
    exchange_tokens: dict[str, list[str]]

    @classmethod
    def from_scrips(
        cls, mode: str, scrips: list[BaseScripData]
    ) -> "QuoteRequest":
        quote_mode = validate_quote_mode(mode)
        return cls(
            mode=quote_mode,
            exchange_tokens={
                scrips[0].exchange: [str(scrip.token) for scrip in scrips]
            },
        )


def validate_quote_mode(mode: str) -> str:
    quote_mode = mode.upper()
    if quote_mode not in SUPPORTED_QUOTE_MODES:
        raise AngelOneSmartApiRestBrokerError(
            "Unsupported Angel One quote mode",
            {"mode": mode, "supported_modes": sorted(SUPPORTED_QUOTE_MODES)},
        )
    return quote_mode


__all__ = [
    "CandleRequest",
    "LtpRequest",
    "QuoteRequest",
    "SUPPORTED_QUOTE_MODES",
    "validate_quote_mode",
]
