from __future__ import annotations

from data_layer.abs import BrokerResponse

from .models import (
    CanonicalCandle,
    CanonicalDerivativeExpiry,
    CanonicalDerivativeUnderlying,
    CanonicalInstrument,
    CanonicalQuote,
)
from .providers.angelone import normalize_candles as normalize_angelone_candles
from .providers.angelone import (
    normalize_derivative_expiries as normalize_angelone_derivative_expiries,
)
from .providers.angelone import (
    normalize_derivative_underlyings as normalize_angelone_derivative_underlyings,
)
from .providers.angelone import (
    normalize_instruments as normalize_angelone_instruments,
)
from .providers.angelone import normalize_quotes as normalize_angelone_quotes
from .symbols import canonicalize_symbol

_QUOTE_NORMALIZERS = {
    "angelone": normalize_angelone_quotes,
}
_CANDLE_NORMALIZERS = {
    "angelone": normalize_angelone_candles,
}
_INSTRUMENT_NORMALIZERS = {
    "angelone": normalize_angelone_instruments,
}
_DERIVATIVE_UNDERLYING_NORMALIZERS = {
    "angelone": normalize_angelone_derivative_underlyings,
}
_DERIVATIVE_EXPIRY_NORMALIZERS = {
    "angelone": normalize_angelone_derivative_expiries,
}


def normalize_quotes(response: BrokerResponse) -> list[CanonicalQuote]:
    """Normalize a broker quote response into canonical quote rows."""

    return _dispatch(
        response,
        normalizers=_QUOTE_NORMALIZERS,
        label="quote",
    )


def normalize_candles(response: BrokerResponse) -> list[CanonicalCandle]:
    """Normalize a broker candle response into canonical candle rows."""

    return _dispatch(
        response,
        normalizers=_CANDLE_NORMALIZERS,
        label="candle",
    )


def normalize_instruments(
    response: BrokerResponse,
) -> list[CanonicalInstrument]:
    """Normalize a broker instrument response into canonical instrument rows."""

    return _dispatch(
        response,
        normalizers=_INSTRUMENT_NORMALIZERS,
        label="instrument",
    )


def normalize_derivative_underlyings(
    response: BrokerResponse,
) -> list[CanonicalDerivativeUnderlying]:
    """Normalize derivative-underlying discovery results into flat rows."""

    return _dispatch(
        response,
        normalizers=_DERIVATIVE_UNDERLYING_NORMALIZERS,
        label="derivative-underlying",
    )


def normalize_derivative_expiries(
    response: BrokerResponse,
) -> list[CanonicalDerivativeExpiry]:
    """Normalize derivative-expiry discovery results into flat rows."""

    return _dispatch(
        response,
        normalizers=_DERIVATIVE_EXPIRY_NORMALIZERS,
        label="derivative-expiry",
    )


def _dispatch(response: BrokerResponse, *, normalizers: dict, label: str):
    """Route canonical normalization to the provider-specific implementation."""

    normalizer = normalizers.get(response.broker_name)
    if normalizer is not None:
        return normalizer(response)

    raise NotImplementedError(
        "No canonical {0} normalizer registered for provider={1}".format(
            label, response.broker_name
        )
    )


__all__ = [
    "CanonicalCandle",
    "CanonicalDerivativeExpiry",
    "CanonicalDerivativeUnderlying",
    "CanonicalInstrument",
    "CanonicalQuote",
    "canonicalize_symbol",
    "normalize_candles",
    "normalize_derivative_expiries",
    "normalize_derivative_underlyings",
    "normalize_instruments",
    "normalize_quotes",
]
