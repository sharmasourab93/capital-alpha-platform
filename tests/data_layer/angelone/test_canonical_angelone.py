from __future__ import annotations

from data_layer.abs import BrokerResponse
from data_layer.canonical import (
    normalize_candles,
    normalize_derivative_expiries,
    normalize_derivative_underlyings,
    normalize_instruments,
    normalize_quotes,
)
from data_layer.canonical.symbols import canonicalize_symbol


def test_normalize_quotes_maps_angelone_payload():
    response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_quotes_by_tokens",
        payload={
            "status": True,
            "data": [
                {
                    "exchange": "NSE",
                    "tradingSymbol": "SBIN-EQ",
                    "symbolToken": "3045",
                    "ltp": 812.35,
                    "open": 800.0,
                    "high": 815.0,
                    "low": 798.0,
                    "close": 805.0,
                    "tradeVolume": 123456,
                    "exchFeedTime": "2026-05-04 10:15:00",
                }
            ],
        },
        response_meta={"exchange": "NSE"},
    )

    quotes = normalize_quotes(response)

    assert len(quotes) == 1
    assert quotes[0].provider == "angelone"
    assert quotes[0].exchange == "NSE"
    assert quotes[0].symbol == "SBIN"
    assert quotes[0].broker_symbol == "SBIN-EQ"
    assert quotes[0].token == "3045"
    assert quotes[0].ltp == 812.35
    assert quotes[0].volume == 123456


def test_normalize_quotes_skips_rows_without_valid_ltp():
    response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_quotes_by_tokens",
        payload={
            "status": True,
            "data": [
                {
                    "exchange": "NSE",
                    "tradingSymbol": "SBIN-EQ",
                    "symbolToken": "3045",
                    "ltp": "",
                },
                {
                    "exchange": "NSE",
                    "tradingSymbol": "RELIANCE-EQ",
                    "symbolToken": "2885",
                    "ltp": "bad-number",
                },
                {
                    "exchange": "NSE",
                    "tradingSymbol": "ICICIBANK-EQ",
                    "symbolToken": "4963",
                    "ltp": 1432.1,
                },
            ],
        },
        response_meta={"exchange": "NSE"},
    )

    quotes = normalize_quotes(response)

    assert len(quotes) == 1
    assert quotes[0].symbol == "ICICIBANK"
    assert quotes[0].ltp == 1432.1


def test_normalize_candles_maps_angelone_payload():
    response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_candles",
        payload={
            "status": True,
            "data": [
                ["2026-05-04 09:15:00", 800.0, 815.0, 798.0, 812.35, 123456]
            ],
        },
        response_meta={
            "exchange": "NSE",
            "interval": "1d",
            "symbol": "SBIN",
        },
    )

    candles = normalize_candles(response)

    assert len(candles) == 1
    assert candles[0].provider == "angelone"
    assert candles[0].exchange == "NSE"
    assert candles[0].symbol == "SBIN"
    assert candles[0].interval == "1d"
    assert candles[0].timestamp == "2026-05-04 09:15:00"
    assert candles[0].close == 812.35
    assert candles[0].volume == 123456


def test_normalize_candles_skips_bad_rows_and_keeps_batch_alive():
    response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_candles",
        payload={
            "status": True,
            "data": [
                ["2026-05-04 09:15:00", 800.0, 815.0, 798.0, 812.35, 123456],
                ["2026-05-04 09:16:00", "bad-open", 816.0, 799.0, 813.0, 100],
                [
                    "2026-05-04 09:17:00",
                    801.0,
                    817.0,
                    800.0,
                    814.0,
                    "bad-volume",
                ],
                [None, 802.0, 818.0, 801.0, 815.0, 200],
            ],
        },
        response_meta={
            "exchange": "NSE",
            "interval": "1m",
            "symbol": "SBIN-EQ",
        },
    )

    candles = normalize_candles(response)

    assert len(candles) == 2
    assert candles[0].timestamp == "2026-05-04 09:15:00"
    assert candles[0].volume == 123456
    assert candles[1].timestamp == "2026-05-04 09:17:00"
    assert candles[1].close == 814.0
    assert candles[1].volume is None


def test_normalize_instruments_maps_search_payload():
    response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_instruments",
        payload={
            "status": True,
            "data": [
                {
                    "exchange": "NSE",
                    "tradingsymbol": "SBIN-EQ",
                    "symboltoken": "3045",
                    "symbolname": "STATE BANK OF INDIA",
                }
            ],
        },
        response_meta={"exchange": "NSE"},
    )

    instruments = normalize_instruments(response)

    assert len(instruments) == 1
    assert instruments[0].provider == "angelone"
    assert instruments[0].exchange == "NSE"
    assert instruments[0].symbol == "SBIN"
    assert instruments[0].broker_symbol == "SBIN-EQ"
    assert instruments[0].token == "3045"
    assert instruments[0].name == "STATE BANK OF INDIA"


def test_normalize_instruments_keeps_derivative_broker_symbol_as_canonical():
    response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_instruments_by_exchange",
        payload=[
            {
                "exchange": "NFO",
                "symbol": "BANKNIFTY29MAY202550000CE",
                "token": "50002",
                "name": "BANKNIFTY",
                "instrument_type": "OPTIDX",
                "underlying": "BANKNIFTY",
                "expiry": "29MAY2025",
                "strike": "50000",
                "lot_size": "15",
                "option_type": "CE",
                "exchange_segment": "NFO",
            }
        ],
        response_meta={"exchange": "NFO"},
    )

    instruments = normalize_instruments(response)

    assert len(instruments) == 1
    assert instruments[0].symbol == "BANKNIFTY29MAY202550000CE"
    assert instruments[0].broker_symbol == "BANKNIFTY29MAY202550000CE"


def test_normalize_instruments_maps_derivative_contract_rows_without_tokens():
    response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_derivative_contracts",
        payload=[
            {
                "symbol": "BANKNIFTY29MAY202550000CE",
                "exchange": "NFO",
                "exchange_segment": "NFO",
                "instrument_type": "OPTIDX",
                "underlying": "BANKNIFTY",
                "expiry": "29MAY2025",
                "strike": 50000,
                "lot_size": 15,
                "option_type": "CE",
            }
        ],
        response_meta={
            "exchange": "NFO",
            "underlying": "BANKNIFTY",
            "instrument_type": "OPTIDX",
            "expiry": "29MAY2025",
        },
    )

    instruments = normalize_instruments(response)

    assert len(instruments) == 1
    assert instruments[0].symbol == "BANKNIFTY29MAY202550000CE"
    assert instruments[0].token is None
    assert instruments[0].name == "BANKNIFTY"
    assert instruments[0].underlying == "BANKNIFTY"


def test_normalize_instruments_maps_master_payload():
    response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_instruments_by_exchange",
        payload=[
            {
                "exchange": "NSE",
                "symbol": "SBIN-EQ",
                "token": "3045",
                "name": "STATE BANK OF INDIA",
                "instrument_type": "EQ",
                "underlying": "STATE BANK OF INDIA",
                "expiry": None,
                "strike": None,
                "lot_size": 1,
                "option_type": None,
                "exchange_segment": "NSE",
            }
        ],
        response_meta={"exchange": "NSE"},
    )

    instruments = normalize_instruments(response)

    assert len(instruments) == 1
    assert instruments[0].symbol == "SBIN"
    assert instruments[0].broker_symbol == "SBIN-EQ"
    assert instruments[0].instrument_type == "EQ"


def test_normalize_derivative_underlyings_flattens_grouped_payload():
    response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_derivative_underlyings",
        payload={
            "NFO": {
                "OPTIDX": ["BANKNIFTY", "NIFTY"],
                "OPTSTK": ["RELIANCE"],
            }
        },
        response_meta={"exchange_count": 1},
    )

    underlyings = normalize_derivative_underlyings(response)

    assert [
        (
            item.exchange,
            item.instrument_type,
            item.underlying,
        )
        for item in underlyings
    ] == [
        ("NFO", "OPTIDX", "BANKNIFTY"),
        ("NFO", "OPTIDX", "NIFTY"),
        ("NFO", "OPTSTK", "RELIANCE"),
    ]


def test_normalize_derivative_expiries_uses_response_meta_contract_context():
    response = BrokerResponse(
        broker_name="angelone",
        operation="fetch_derivative_expiries",
        payload=["29MAY2025", "26JUN2025"],
        response_meta={
            "exchange": "NFO",
            "underlying": "BANKNIFTY",
            "instrument_type": "OPTIDX",
        },
    )

    expiries = normalize_derivative_expiries(response)

    assert [
        (
            item.exchange,
            item.instrument_type,
            item.underlying,
            item.expiry,
        )
        for item in expiries
    ] == [
        ("NFO", "OPTIDX", "BANKNIFTY", "29MAY2025"),
        ("NFO", "OPTIDX", "BANKNIFTY", "26JUN2025"),
    ]


def test_canonicalize_symbol_contract_is_explicit_for_equities_and_derivatives():
    assert canonicalize_symbol(" sbin-eq ") == "SBIN"
    assert (
        canonicalize_symbol(
            "BANKNIFTY29MAY202550000CE",
            instrument_type="OPTIDX",
        )
        == "BANKNIFTY29MAY202550000CE"
    )
    assert canonicalize_symbol("RELIANCE", instrument_type="EQ") == "RELIANCE"
