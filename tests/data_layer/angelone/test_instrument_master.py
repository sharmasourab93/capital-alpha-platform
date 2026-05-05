from __future__ import annotations

import pytest

from data_layer.abs import DerivativeInstrumentRequest
from data_layer.brokers.angelone.rest.instrument_master import (
    AngelInstrumentMaster,
)


def test_from_rows_builds_instruments_and_indexes(
    sample_scrip_master_rows: list[dict],
) -> None:
    master = AngelInstrumentMaster.from_rows(sample_scrip_master_rows)

    assert len(master.instruments) == len(sample_scrip_master_rows)
    assert master.by_token["3045"].symbol == "SBIN-EQ"
    assert master.get_by_symbol_exchange("SBIN-EQ", "NSE")[0].token == "3045"


def test_get_by_token_returns_matching_instrument(
    instrument_master: AngelInstrumentMaster,
) -> None:
    instrument = instrument_master.get_by_token("2885")

    assert instrument is not None
    assert instrument.symbol == "RELIANCE-EQ"


def test_resolve_equity_instrument_accepts_plain_symbol(
    instrument_master: AngelInstrumentMaster,
) -> None:
    instrument = instrument_master.resolve_equity_instrument("SBIN", "NSE")

    assert instrument.symbol == "SBIN-EQ"
    assert instrument.token == "3045"


def test_resolve_equity_instrument_accepts_broker_native_symbol(
    instrument_master: AngelInstrumentMaster,
) -> None:
    instrument = instrument_master.resolve_equity_instrument("SBIN-EQ", "NSE")

    assert instrument.symbol == "SBIN-EQ"


def test_resolve_equity_instrument_prefers_eq_variant_when_available(
    sample_equity_rows_with_ambiguity: list[dict],
) -> None:
    master = AngelInstrumentMaster.from_rows(sample_equity_rows_with_ambiguity)

    instrument = master.resolve_equity_instrument("SBIN", "NSE")

    assert instrument.symbol == "SBIN-EQ"
    assert instrument.token == "3045"


def test_resolve_equity_instrument_raises_for_missing_symbol(
    instrument_master: AngelInstrumentMaster,
) -> None:
    with pytest.raises(LookupError, match="No equity instrument found"):
        instrument_master.resolve_equity_instrument("DOESNOTEXIST", "NSE")


def test_resolve_equity_instrument_raises_for_ambiguous_matches(
    sample_equity_rows: list[dict],
) -> None:
    master = AngelInstrumentMaster.from_rows(
        sample_equity_rows
        + [
            {
                "token": "93045",
                "symbol": "ABC",
                "name": "ABC LTD",
                "exch_seg": "NSE",
                "instrumenttype": "EQ",
                "expiry": "",
                "strike": "",
                "lotsize": "1",
            },
            {
                "token": "93046",
                "symbol": "ABC",
                "name": "ABC LTD",
                "exch_seg": "NSE",
                "instrumenttype": "EQ",
                "expiry": "",
                "strike": "",
                "lotsize": "1",
            },
        ]
    )

    with pytest.raises(LookupError, match="Multiple equity instruments found"):
        master.resolve_equity_instrument("ABC", "NSE")


def test_get_derivative_symbols_groups_by_exchange_and_instrument_type(
    instrument_master: AngelInstrumentMaster,
) -> None:
    symbols = instrument_master.get_derivative_symbols(exchange="NFO")

    assert "NFO" in symbols
    assert "OPTIDX" in symbols["NFO"]
    assert "BANKNIFTY29MAY202550000CE" in symbols["NFO"]["OPTIDX"]


def test_get_derivative_underlyings_returns_index_and_stock_underlyings(
    instrument_master: AngelInstrumentMaster,
) -> None:
    underlyings = instrument_master.get_derivative_underlyings(exchange="NFO")

    assert underlyings["NFO"]["OPTIDX"] == ["BANKNIFTY"]
    assert underlyings["NFO"]["OPTSTK"] == ["RELIANCE"]
    assert underlyings["NFO"]["FUTSTK"] == ["RELIANCE"]


def test_get_derivative_expiries_returns_sorted_unique_expiries(
    instrument_master: AngelInstrumentMaster,
) -> None:
    expiries = instrument_master.get_derivative_expiries(
        exchange="NFO",
        underlying="BANKNIFTY",
        instrument_type="OPTIDX",
    )

    assert expiries == ("29MAY2025", "26JUN2025")


def test_get_derivative_strikes_returns_sorted_unique_strikes(
    instrument_master: AngelInstrumentMaster,
) -> None:
    strikes = instrument_master.get_derivative_strikes(
        exchange="NFO",
        underlying="BANKNIFTY",
        instrument_type="OPTIDX",
        expiry="29MAY2025",
        option_type="CE",
    )

    assert strikes == (50000.0, 51000.0)


def test_get_symbol_name_counts_by_exchange_returns_compact_summary(
    instrument_master: AngelInstrumentMaster,
) -> None:
    counts = instrument_master.get_symbol_name_counts_by_exchange()

    assert counts["NSE"] == 3
    assert counts["NFO"] == 7


def test_get_symbol_name_page_returns_filtered_paginated_rows(
    instrument_master: AngelInstrumentMaster,
) -> None:
    page = instrument_master.get_symbol_name_page(
        "NSE",
        query="SBIN",
        offset=0,
        limit=10,
    )

    assert page["exchange"] == "NSE"
    assert page["total"] == 1
    assert page["count"] == 1
    assert page["items"] == [
        {"symbol": "SBIN-EQ", "name": "STATE BANK OF INDIA"}
    ]


def test_resolve_derivative_instrument_resolves_unique_option_contract(
    instrument_master: AngelInstrumentMaster,
) -> None:
    instrument = instrument_master.resolve_derivative_instrument(
        DerivativeInstrumentRequest(
            exchange="NFO",
            underlying="BANKNIFTY",
            instrument_type="OPTIDX",
            expiry="29MAY2025",
            strike=50000,
            option_type="CE",
        )
    )

    assert instrument.token == "50002"
    assert instrument.option_type == "CE"


def test_resolve_derivative_instrument_raises_for_wrong_expiry(
    instrument_master: AngelInstrumentMaster,
) -> None:
    with pytest.raises(LookupError, match="No derivative instrument found"):
        instrument_master.resolve_derivative_instrument(
            DerivativeInstrumentRequest(
                exchange="NFO",
                underlying="BANKNIFTY",
                instrument_type="OPTIDX",
                expiry="01JAN2030",
                strike=50000,
                option_type="CE",
            )
        )


def test_from_rows_prefers_symbol_strike_over_scaled_raw_strike() -> None:
    master = AngelInstrumentMaster.from_rows(
        [
            {
                "token": "70001",
                "symbol": "NIFTY29MAY202524500CE",
                "name": "NIFTY",
                "exch_seg": "NFO",
                "instrumenttype": "OPTIDX",
                "expiry": "29MAY2025",
                "strike": "245000000",
                "lotsize": "75",
            }
        ]
    )

    instrument = master.get_by_token("70001")

    assert instrument is not None
    assert instrument.strike == 24500.0


def test_from_rows_infers_underlying_when_name_is_blank_for_derivative() -> (
    None
):
    master = AngelInstrumentMaster.from_rows(
        [
            {
                "token": "70002",
                "symbol": "BANKNIFTY29MAY2025FUT",
                "name": "",
                "exch_seg": "NFO",
                "instrumenttype": "FUTIDX",
                "expiry": "29MAY2025",
                "strike": "",
                "lotsize": "15",
            }
        ]
    )

    instrument = master.get_by_token("70002")

    assert instrument is not None
    assert instrument.underlying == "BANKNIFTY"


def test_from_rows_skips_malformed_rows_without_killing_master_build() -> None:
    master = AngelInstrumentMaster.from_rows(
        [
            {
                "token": "3045",
                "symbol": "SBIN-EQ",
                "name": "STATE BANK OF INDIA",
                "exch_seg": "NSE",
                "instrumenttype": "EQ",
                "expiry": "",
                "strike": "",
                "lotsize": "1",
            },
            {
                "token": "",
                "symbol": "BADTOKEN-EQ",
                "name": "BROKEN",
                "exch_seg": "NSE",
                "instrumenttype": "EQ",
                "expiry": "",
                "strike": "",
                "lotsize": "1",
            },
            {
                "token": "70003",
                "symbol": "BADLOT29MAY202550000CE",
                "name": "BANKNIFTY",
                "exch_seg": "NFO",
                "instrumenttype": "OPTIDX",
                "expiry": "29MAY2025",
                "strike": "5000000",
                "lotsize": "not-an-int",
            },
            {
                "token": "70004",
                "symbol": "BADSTRIKE29MAY2025FUT",
                "name": "BANKNIFTY",
                "exch_seg": "NFO",
                "instrumenttype": "FUTIDX",
                "expiry": "29MAY2025",
                "strike": "bad-strike",
                "lotsize": "15",
            },
        ]
    )

    assert len(master.instruments) == 2
    assert master.get_by_token("3045") is not None
    assert master.get_by_token("70004") is not None
