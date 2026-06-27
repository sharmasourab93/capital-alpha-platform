"""Tests for raw and DataFrame output adaptation."""

from __future__ import annotations

import pytest

from data_client.output import adapt_output, to_dataframe


def test_adapt_output_returns_raw_payload_by_default() -> None:
    """Verify raw mode does not mutate or wrap API payloads."""
    payload = {"symbol": "SBIN", "ltp": 100}

    assert adapt_output(payload, output="raw") is payload


def test_dataframe_output_handles_dict_list_scalar_and_none() -> None:
    """Verify generic DataFrame conversion for common response shapes."""
    dict_frame = to_dataframe({"symbol": "SBIN", "ltp": 100})
    list_frame = to_dataframe([{"symbol": "SBIN"}, {"symbol": "RELIANCE"}])
    scalar_frame = to_dataframe("ok")
    none_frame = to_dataframe(None)

    assert dict_frame.to_dict("records") == [{"symbol": "SBIN", "ltp": 100}]
    assert list_frame["symbol"].tolist() == ["SBIN", "RELIANCE"]
    assert scalar_frame.to_dict("records") == [{"value": "ok"}]
    assert none_frame.empty


def test_empty_candle_dataframe_keeps_date_index() -> None:
    """Verify empty candle responses still produce a stable OHLCV frame."""
    frame = to_dataframe([], shape="candles")

    assert frame.empty
    assert frame.index.name == "date"
    assert list(frame.columns) == ["open", "high", "low", "close", "volume"]


def test_candle_dataframe_rejects_malformed_rows() -> None:
    """Verify malformed candle rows fail loudly instead of silently shifting data."""
    with pytest.raises(ValueError):
        to_dataframe([["2026-06-26T09:15:00+05:30", 100]], shape="candles")
