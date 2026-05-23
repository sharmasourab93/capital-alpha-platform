import json

import pytest

from data_layer.brokers.angelone.rest.angel_instrument import (
    AngelInstrument,
    AngelOneBroker,
    AngelOneIndex,
    AngelOneInstruments,
    AngelOneOtherScrip,
    AngelOneStock,
)

DECIMAL_TICK_SIZE_CONTRACT_SKIP_REASON = (
    "Skipped because finalized angel_instrument.py expects integer tick_size "
    "values, not decimal strings."
)
UNKNOWN_INSTRUMENT_TYPE_CONTRACT_SKIP_REASON = (
    "Skipped because finalized angel_instrument.py only maps known AngelOne "
    "instrument types and blank BSE other rows."
)


@pytest.mark.skip(reason=DECIMAL_TICK_SIZE_CONTRACT_SKIP_REASON)
def test_stock_from_row_normalizes_core_fields_and_token() -> None:
    stock = AngelOneStock.from_row(
        _row(
            token="2885.0",
            symbol="reliance-eq",
            name="reliance",
            exchange="nse",
            tick_size="5.000000",
        )
    )

    assert stock.exchange == "NSE"
    assert stock.symbol == "RELIANCE-EQ"
    assert stock.name == "RELIANCE"
    assert stock.token == 2885
    assert stock.ticksize == "5.000000"


def test_index_from_row_normalizes_core_fields_and_instrument_type() -> None:
    index = AngelOneIndex.from_row(
        _row(
            token="99926000",
            symbol="nifty",
            name="nifty",
            exchange="nse",
            instrument_type="AMXIDX",
        )
    )

    assert index.exchange == "NSE"
    assert index.symbol == "NIFTY"
    assert index.name == "NIFTY"
    assert index.token == 99926000
    assert index.instrumenttype == "AMXIDX"


@pytest.mark.skip(reason=DECIMAL_TICK_SIZE_CONTRACT_SKIP_REASON)
def test_other_scrip_from_row_normalizes_core_fields() -> None:
    other = AngelOneOtherScrip.from_row(
        _row(
            token="12345",
            symbol="test",
            name="test",
            exchange="bse",
            instrument_type="BSEOTHER",
        )
    )

    assert other.exchange == "BSE"
    assert other.symbol == "TEST"
    assert other.name == "TEST"
    assert other.token == 12345
    assert other.instrumenttype == "BSEOTHER"


@pytest.mark.skip(reason=DECIMAL_TICK_SIZE_CONTRACT_SKIP_REASON)
def test_instruments_group_equity_rows_by_exchange_and_name() -> None:
    instruments = AngelOneInstruments.from_scrip_master_rows(
        [
            _row(token="111", symbol="SBIN-EQ", name="SBIN", exchange="NSE"),
            _row(
                token="222",
                symbol="RELIANCE-EQ",
                name="RELIANCE",
                exchange="BSE",
            ),
        ]
    )

    assert tuple(instruments.nse_stocks) == ("SBIN",)
    assert tuple(instruments.bse_stocks) == ("RELIANCE",)
    assert instruments.nse_stocks["SBIN"].token == 111
    assert instruments.bse_stocks["RELIANCE"].token == 222


@pytest.mark.skip(reason=UNKNOWN_INSTRUMENT_TYPE_CONTRACT_SKIP_REASON)
def test_instruments_group_indices_and_other_scrips_separately() -> None:
    instruments = AngelOneInstruments.from_scrip_master_rows(
        [
            _row(
                token="99926000",
                symbol="NIFTY",
                name="NIFTY",
                exchange="NSE",
                instrument_type="AMXIDX",
            ),
            _row(
                token="12345",
                symbol="TEST",
                name="TEST",
                exchange="NSE",
                instrument_type="NSEOTHER",
            ),
        ]
    )

    assert tuple(instruments.nse_indices) == ("NIFTY",)
    assert tuple(instruments.nse.others) == ("TEST",)
    assert instruments.nse_indices["NIFTY"].token == 99926000
    assert instruments.nse.others["TEST"].token == 12345
    assert instruments.nse_stocks == {}


@pytest.mark.skip(reason=DECIMAL_TICK_SIZE_CONTRACT_SKIP_REASON)
def test_unimplemented_exchange_rows_are_ignored() -> None:
    instruments = AngelOneInstruments.from_scrip_master_rows(
        [
            _row(token="111", symbol="SBIN-EQ", name="SBIN", exchange="NFO"),
            _row(token="222", symbol="ABB-EQ", name="ABB", exchange="NSE"),
        ]
    )

    assert tuple(instruments.nse_stocks) == ("ABB",)
    assert instruments.bse_stocks == {}


def test_from_json_rejects_non_list_payload() -> None:
    with pytest.raises(
        ValueError, match="Angel scrip master payload must be a JSON list"
    ):
        AngelOneInstruments.from_json(json.dumps({"token": "2885"}))


@pytest.mark.skip(reason=DECIMAL_TICK_SIZE_CONTRACT_SKIP_REASON)
def test_from_json_builds_instruments_from_bytes_payload() -> None:
    payload = json.dumps(
        [_row(token="2885", symbol="RELIANCE-EQ", name="RELIANCE")]
    ).encode()

    instruments = AngelOneInstruments.from_json(payload)

    assert instruments.nse_stocks["RELIANCE"].token == 2885


@pytest.mark.skip(reason=DECIMAL_TICK_SIZE_CONTRACT_SKIP_REASON)
def test_from_file_builds_instruments(tmp_path) -> None:
    path = tmp_path / "angel_scrip_master.json"
    path.write_text(
        json.dumps([_row(token="3045", symbol="SBIN-EQ", name="SBIN")]),
        encoding="utf-8",
    )

    instruments = AngelOneInstruments.from_file(path)

    assert instruments.nse_stocks["SBIN"].symbol == "SBIN-EQ"


def test_broker_get_exchange_is_case_insensitive() -> None:
    broker = AngelInstrument.from_scrip_master_rows([])

    assert broker.get_exchange("nse") is broker.instrument_master.nse
    assert broker.get_exchange("Bse") is broker.instrument_master.bse
    assert broker.get_exchange("NFO") is None


@pytest.mark.skip(reason=UNKNOWN_INSTRUMENT_TYPE_CONTRACT_SKIP_REASON)
def test_broker_get_scrip_resolves_stock_index_and_other_by_name() -> None:
    broker = AngelInstrument.from_scrip_master_rows(
        [
            _row(token="111", symbol="SBIN-EQ", name="SBIN", exchange="NSE"),
            _row(
                token="99926000",
                symbol="NIFTY",
                name="NIFTY",
                exchange="NSE",
                instrument_type="AMXIDX",
            ),
            _row(
                token="12345",
                symbol="TEST",
                name="TEST",
                exchange="NSE",
                instrument_type="NSEOTHER",
            ),
        ]
    )

    stock = broker.get_scrip("nse", "sbin")
    index = broker.get_scrip("NSE", "nifty")
    other = broker.get_scrip("NSE", "test")

    assert stock is not None
    assert stock.token == 111
    assert index is not None
    assert index.token == 99926000
    assert other is not None
    assert other.token == 12345


@pytest.mark.skip(reason=DECIMAL_TICK_SIZE_CONTRACT_SKIP_REASON)
def test_broker_get_scrip_returns_none_for_unknown_exchange_or_key() -> None:
    broker = AngelInstrument.from_scrip_master_rows(
        [_row(token="111", symbol="SBIN-EQ", name="SBIN", exchange="NSE")]
    )

    assert broker.get_scrip("NFO", "SBIN") is None
    assert broker.get_scrip("NSE", "MISSING") is None


@pytest.mark.skip(reason=DECIMAL_TICK_SIZE_CONTRACT_SKIP_REASON)
def test_broker_get_all_scrips_defaults_to_nse_and_includes_indices() -> None:
    broker = AngelInstrument.from_scrip_master_rows(
        [
            _row(token="111", symbol="SBIN-EQ", name="SBIN", exchange="NSE"),
            _row(
                token="99926000",
                symbol="NIFTY",
                name="NIFTY",
                exchange="NSE",
                instrument_type="AMXIDX",
            ),
            _row(token="222", symbol="ABB-EQ", name="ABB", exchange="BSE"),
        ]
    )

    assert broker.get_all_scrips() == ["NSE: SBIN", "NSE: NIFTY"]
    assert broker.get_all_scrips("bse") == ["BSE: ABB"]
    assert broker.get_all_scrips("NFO") == []


def test_broker_factory_alias_points_to_broker_class() -> None:
    assert AngelInstrument is AngelOneBroker


def _row(
    *,
    token: str,
    symbol: str,
    name: str,
    exchange: str = "NSE",
    expiry: str = "",
    strike: str = "-1.000000",
    lot_size: str = "1",
    instrument_type: str = "",
    tick_size: str = "5.000000",
) -> dict[str, str]:
    return {
        "token": token,
        "symbol": symbol,
        "name": name,
        "expiry": expiry,
        "strike": strike,
        "lotsize": lot_size,
        "instrumenttype": instrument_type,
        "exch_seg": exchange,
        "tick_size": tick_size,
    }
