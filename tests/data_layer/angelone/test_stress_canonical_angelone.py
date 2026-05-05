from __future__ import annotations

from data_layer.abs import BrokerResponse, DerivativeInstrumentRequest
from data_layer.brokers.angelone.rest.instrument_master import (
    AngelInstrumentMaster,
)
from data_layer.canonical import (
    normalize_candles,
    normalize_derivative_expiries,
    normalize_derivative_underlyings,
    normalize_instruments,
    normalize_quotes,
)
from data_layer.canonical.run_angelone_canonical import normalize_response


def test_stress_normalize_quotes_skips_only_bad_rows() -> None:
    rows = []
    expected_valid = 0

    for index in range(4000):
        row = {
            "exchange": "NSE",
            "tradingSymbol": "SBIN-EQ" if index % 2 == 0 else "RELIANCE-EQ",
            "symbolToken": str(3000 + index),
            "ltp": 800.0 + index,
            "open": 790.0 + index,
            "high": 810.0 + index,
            "low": 780.0 + index,
            "close": 795.0 + index,
            "tradeVolume": 1000 + index,
            "exchFeedTime": "2026-05-04 10:15:00",
        }
        if index % 7 == 0:
            row["ltp"] = "bad-ltp"
        else:
            expected_valid += 1
        rows.append(row)

    response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_bulk_quotes",
        payload={"status": True, "data": rows},
        response_meta={"exchange": "NSE"},
    )

    quotes = normalize_quotes(response)

    assert len(quotes) == expected_valid
    assert all(item.ltp > 0 for item in quotes)
    assert {item.symbol for item in quotes} == {"SBIN", "RELIANCE"}


def test_stress_normalize_candles_keeps_large_batch_alive() -> None:
    rows = []
    expected_valid = 0

    for index in range(12000):
        row = [
            "2026-05-04 09:{0:02d}:00".format(index % 60),
            800.0 + index,
            805.0 + index,
            795.0 + index,
            802.0 + index,
            10000 + index,
        ]
        if index % 11 == 0:
            row[2] = "bad-high"
        else:
            expected_valid += 1
        rows.append(row)

    response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_candles",
        payload={"status": True, "data": rows},
        response_meta={
            "exchange": "NSE",
            "interval": "1m",
            "symbol": "SBIN-EQ",
        },
    )

    candles = normalize_candles(response)

    assert len(candles) == expected_valid
    assert all(item.symbol == "SBIN" for item in candles)
    assert all(item.high >= item.low for item in candles)


def test_stress_normalize_instruments_handles_large_exchange_payload() -> None:
    payload = []
    for index in range(6000):
        payload.append(
            {
                "exchange": "NFO",
                "symbol": "BANKNIFTY29MAY2025{0}CE".format(50000 + index),
                "token": str(50000 + index),
                "name": "BANKNIFTY",
                "instrument_type": "OPTIDX",
                "underlying": "BANKNIFTY",
                "expiry": "29MAY2025",
                "strike": str(50000 + index),
                "lot_size": "15",
                "option_type": "CE",
                "exchange_segment": "NFO",
            }
        )

    response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_instruments_by_exchange",
        payload=payload,
        response_meta={"exchange": "NFO"},
    )

    instruments = normalize_instruments(response)

    assert len(instruments) == 6000
    assert instruments[0].underlying == "BANKNIFTY"
    assert instruments[-1].exchange == "NFO"


def test_stress_normalize_derivative_discovery_payloads() -> None:
    underlyings_response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_derivative_underlyings",
        payload={
            "NFO": {
                "OPTIDX": ["BANKNIFTY", "NIFTY"] * 500,
                "OPTSTK": ["RELIANCE", "SBIN"] * 500,
            }
        },
        response_meta={"exchange_count": 1},
    )
    expiries_response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_derivative_expiries",
        payload=["29MAY2025", "26JUN2025", "31JUL2025"] * 2000,
        response_meta={
            "exchange": "NFO",
            "underlying": "BANKNIFTY",
            "instrument_type": "OPTIDX",
        },
    )

    underlyings = normalize_derivative_underlyings(underlyings_response)
    expiries = normalize_derivative_expiries(expiries_response)

    assert len(underlyings) == 2000
    assert len(expiries) == 6000
    assert underlyings[0].exchange == "NFO"
    assert all(item.underlying == "BANKNIFTY" for item in expiries)


def test_stress_instrument_master_build_and_resolve_large_dataset(
    sample_scrip_master_rows: list[dict],
) -> None:
    rows = sample_scrip_master_rows * 3000
    master = AngelInstrumentMaster.from_rows(rows)

    instrument = master.resolve_derivative_instrument(
        DerivativeInstrumentRequest(
            exchange="NFO",
            underlying="BANKNIFTY",
            instrument_type="OPTIDX",
            expiry="29MAY2025",
            strike=50000,
            option_type="CE",
        )
    )
    expiries = master.get_derivative_expiries(
        exchange="NFO",
        underlying="BANKNIFTY",
        instrument_type="OPTIDX",
    )

    assert instrument.symbol == "BANKNIFTY29MAY202550000CE"
    assert expiries == ("29MAY2025", "26JUN2025")


def test_stress_canonical_runner_normalize_response_on_large_contract_batch() -> (
    None
):
    response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_derivative_contracts",
        payload=[
            {
                "symbol": "BANKNIFTY29MAY2025{0}CE".format(50000 + index),
                "exchange": "NFO",
                "exchange_segment": "NFO",
                "instrument_type": "OPTIDX",
                "underlying": "BANKNIFTY",
                "expiry": "29MAY2025",
                "strike": 50000 + index,
                "lot_size": 15,
                "option_type": "CE",
            }
            for index in range(5000)
        ],
        response_meta={
            "exchange": "NFO",
            "underlying": "BANKNIFTY",
            "instrument_type": "OPTIDX",
            "expiry": "29MAY2025",
        },
    )

    normalized = normalize_response(response)

    assert len(normalized) == 5000
    assert normalized[0]["token"] is None
    assert normalized[-1]["underlying"] == "BANKNIFTY"


def test_stress_instrument_master_skips_large_malformed_row_mix() -> None:
    rows = []
    expected_valid = 0

    for index in range(10000):
        row = {
            "token": str(80000 + index),
            "symbol": "BANKNIFTY29MAY2025{0}CE".format(50000 + index),
            "name": "BANKNIFTY",
            "exch_seg": "NFO",
            "instrumenttype": "OPTIDX",
            "expiry": "29MAY2025",
            "strike": "5000000",
            "lotsize": "15",
        }
        if index % 13 == 0:
            row["token"] = ""
        elif index % 17 == 0:
            row["lotsize"] = "bad-lot-size"
        elif index % 19 == 0:
            row["symbol"] = ""
        else:
            expected_valid += 1
        rows.append(row)

    master = AngelInstrumentMaster.from_rows(rows)

    assert len(master.instruments) == expected_valid
    assert len(master.by_token) == expected_valid


def test_stress_normalizers_tolerate_malformed_top_level_shapes() -> None:
    malformed_responses = [
        BrokerResponse(
            broker_name="angelone",
            operation="fetch_quotes_by_tokens",
            payload={"status": True, "data": "not-a-list"},
            response_meta={"exchange": "NSE"},
        ),
        BrokerResponse(
            broker_name="angelone",
            operation="fetch_candles",
            payload={"status": True, "data": {"bad": "shape"}},
            response_meta={
                "exchange": "NSE",
                "interval": "1m",
                "symbol": "SBIN",
            },
        ),
        BrokerResponse(
            broker_name="angelone",
            operation="fetch_derivative_underlyings",
            payload={"NFO": ["bad-shape"]},
            response_meta={},
        ),
        BrokerResponse(
            broker_name="angelone",
            operation="fetch_derivative_expiries",
            payload={"bad": "shape"},
            response_meta={
                "exchange": "NFO",
                "underlying": "BANKNIFTY",
                "instrument_type": "OPTIDX",
            },
        ),
    ]

    assert normalize_quotes(malformed_responses[0]) == []
    assert normalize_candles(malformed_responses[1]) == []
    assert normalize_derivative_underlyings(malformed_responses[2]) == []
    assert normalize_derivative_expiries(malformed_responses[3]) == []
