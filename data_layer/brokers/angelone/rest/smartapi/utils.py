from __future__ import annotations

import os

from ..errors import AngelOneSmartApiRestBrokerError


def required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError("{0} is not set".format(name))
    return value


def chunk_sequence(
    values: tuple[str, ...],
    chunk_size: int,
):
    for index in range(0, len(values), chunk_size):
        yield values[index : index + chunk_size]


def validate_bulk_chunk_size(chunk_size: int) -> int:
    if chunk_size <= 0:
        raise AngelOneSmartApiRestBrokerError(
            "Angel One bulk quotes chunk_size must be positive"
        )
    if chunk_size > 50:
        raise AngelOneSmartApiRestBrokerError(
            "Angel One bulk quotes chunk_size cannot exceed 50",
            {"chunk_size": chunk_size},
        )
    return chunk_size


def require_symbols(
    symbols: tuple[str, ...],
    operation: str,
) -> tuple[str, ...]:
    if not symbols:
        raise AngelOneSmartApiRestBrokerError(
            "Angel One {0} requires symbols".format(operation)
        )
    return symbols


def require_tokens(
    tokens: tuple[str, ...],
    operation: str,
) -> tuple[str, ...]:
    if not tokens:
        raise AngelOneSmartApiRestBrokerError(
            "Angel One {0} requires instrument_tokens".format(operation)
        )
    return tuple(str(token) for token in tokens)


def map_interval(interval: str) -> str:
    mapping = {
        "1m": "ONE_MINUTE",
        "3m": "THREE_MINUTE",
        "5m": "FIVE_MINUTE",
        "10m": "TEN_MINUTE",
        "15m": "FIFTEEN_MINUTE",
        "30m": "THIRTY_MINUTE",
        "1h": "ONE_HOUR",
        "1d": "ONE_DAY",
    }
    try:
        return mapping[interval]
    except KeyError as exc:
        raise AngelOneSmartApiRestBrokerError(
            "Unsupported Angel One interval: {0}".format(interval)
        ) from exc


__all__ = [
    "chunk_sequence",
    "map_interval",
    "required_env",
    "require_symbols",
    "require_tokens",
    "validate_bulk_chunk_size",
]
