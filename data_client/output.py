"""Output adapters for data-layer client results.

Endpoint methods return raw API payloads by default. Callers that want pandas
objects can opt in per call with ``as_dataframe=True`` or configure the client
with ``output="dataframe"``. Pandas is imported lazily so raw-client users do
not pay the import cost.
"""

from __future__ import annotations

from typing import Any, Literal

from data_client.exceptions import DataLayerClientConfigError

OutputMode = Literal["raw", "dataframe"]
OutputShape = Literal["generic", "candles"]
CANDLE_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def adapt_output(
    payload: Any,
    *,
    output: OutputMode,
    force: bool = False,
    shape: OutputShape = "generic",
) -> Any:
    """Return payload as raw data or as a pandas DataFrame.

    Args:
        payload: Data returned by the transport or extracted from the API
            response envelope.
        output: Client-level default output mode.
        force: Per-call override from ``as_dataframe=True``.
        shape: Optional hint for endpoint-specific DataFrame shaping.
    """
    if output == "dataframe" or force:
        return to_dataframe(payload, shape=shape)
    return payload


def to_dataframe(payload: Any, *, shape: OutputShape = "generic") -> Any:
    """Convert common API payload shapes to a pandas DataFrame.

    The generic conversion intentionally stays simple:
        - list payloads become row-oriented frames,
        - dict payloads become a single-row frame,
        - scalar payloads become a one-column frame.

    Endpoint-specific structures, such as historical candles, can pass a shape
    hint to preserve domain column names.
    """
    try:
        import pandas as pd
    except ImportError as exc:  # pragma: no cover
        raise DataLayerClientConfigError(
            "pandas is required for dataframe output"
        ) from exc

    if payload is None:
        return pd.DataFrame()
    if shape == "candles":
        return _candles_to_dataframe(payload, pd)
    if isinstance(payload, list):
        return pd.DataFrame(payload)
    if isinstance(payload, dict):
        return pd.DataFrame([payload])
    return pd.DataFrame({"value": [payload]})


def _candles_to_dataframe(payload: Any, pd: Any) -> Any:
    """Convert candle arrays to a timestamp-indexed OHLCV DataFrame.

    AngelOne returns historical candles as positional arrays:
    ``[date, open, high, low, close, volume]``. The canonical API currently
    forwards that data shape, so the client assigns stable column names and
    formats the timestamp index for downstream analytical code.
    """
    frame = pd.DataFrame(payload, columns=CANDLE_COLUMNS)
    if frame.empty:
        return frame.set_index("date")

    frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d %H:%M")
    return frame.set_index("date")
