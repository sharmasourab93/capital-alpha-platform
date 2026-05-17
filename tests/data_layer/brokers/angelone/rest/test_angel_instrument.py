import pytest

from data_layer.brokers.angelone.rest.angel_instrument import AngelInstrument


def test_angel_instrument_groups_rows_by_exchange() -> None:
    angel = AngelInstrument.from_scrip_master_rows(
        [
            _row(token="111", symbol="SBIN-EQ", name="SBIN", exchange="NSE"),
            _row(token="222", symbol="SBIN-EQ", name="SBIN", exchange="BSE"),
        ]
    )

    instruments = angel.instrument_master

    assert instruments.exchange_segments == ("NSE", "BSE")
    assert instruments.nse_stock.get_token("SBIN-EQ") == 111
    assert instruments.bse_stock.get_token("SBIN-EQ") == 222


def test_exchange_instrument_exposes_available_symbols() -> None:
    angel = AngelInstrument.from_scrip_master_rows(
        [
            _row(token="16669", symbol="BAJAJ-AUTO-EQ", name="BAJAJ-AUTO"),
            _row(token="3045", symbol="SBIN-EQ", name="SBIN"),
        ]
    )

    assert angel.instrument_master.nse_stock.symbols == (
        "BAJAJ-AUTO-EQ",
        "SBIN-EQ",
    )


def test_exchange_instrument_resolves_symbol_to_full_record() -> None:
    angel = AngelInstrument.from_scrip_master_rows(
        [
            _row(token="16669", symbol="BAJAJ-AUTO-EQ", name="BAJAJ-AUTO"),
        ]
    )

    instrument = angel.instrument_master.nse_stock.get_by_symbol(
        "BAJAJ-AUTO-EQ"
    )

    assert instrument is not None
    assert instrument.token == 16669
    assert instrument.ticksize == "5.000000"


def test_bse_stock_lookup_is_kept_separate_from_nse() -> None:
    angel = AngelInstrument.from_scrip_master_rows(
        [
            _row(
                token="333",
                symbol="RELIANCE-EQ",
                name="RELIANCE",
                exchange="NSE",
            ),
            _row(
                token="444",
                symbol="RELIANCE-EQ",
                name="RELIANCE",
                exchange="BSE",
            ),
        ]
    )

    assert angel.instrument_master.nse_stock.get_token("RELIANCE-EQ") == 333
    assert angel.instrument_master.bse_stock.get_token("RELIANCE-EQ") == 444


def test_broker_get_scrip_resolves_exchange_and_stock_key() -> None:
    angel = AngelInstrument.from_scrip_master_rows(
        [
            _row(
                token="333",
                symbol="RELIANCE-EQ",
                name="RELIANCE",
                exchange="NSE",
            ),
            _row(
                token="500325",
                symbol="RELIANCE",
                name="RELIANCE",
                exchange="BSE",
            ),
        ]
    )

    nse_scrip = angel.get_scrip("Nse", "RELIANCE")
    bse_scrip = angel.get_scrip("bse", "RELIANCE")

    assert nse_scrip is not None
    assert nse_scrip.symbol == "RELIANCE-EQ"
    assert nse_scrip.token == 333
    assert bse_scrip is not None
    assert bse_scrip.symbol == "RELIANCE"
    assert bse_scrip.token == 500325


def test_broker_get_scrip_accepts_full_nse_symbol() -> None:
    angel = AngelInstrument.from_scrip_master_rows(
        [
            _row(
                token="333",
                symbol="RELIANCE-EQ",
                name="RELIANCE",
                exchange="NSE",
            ),
        ]
    )

    scrip = angel.get_scrip("NSE", "RELIANCE-EQ")

    assert scrip is not None
    assert scrip.token == 333


def test_broker_get_all_scrips_returns_exchange_stocks() -> None:
    angel = AngelInstrument.from_scrip_master_rows(
        [
            _row(token="111", symbol="SBIN-EQ", name="SBIN", exchange="NSE"),
            _row(
                token="222",
                symbol="RELIANCE-EQ",
                name="RELIANCE",
                exchange="NSE",
            ),
            _row(token="333", symbol="ABB", name="ABB", exchange="BSE"),
        ]
    )

    nse_scrips = angel.get_all_scrips("nse")

    assert [scrip.name for scrip in nse_scrips] == ["SBIN", "RELIANCE"]


def test_broker_get_all_scrips_defaults_to_nse() -> None:
    angel = AngelInstrument.from_scrip_master_rows(
        [
            _row(token="111", symbol="SBIN-EQ", name="SBIN", exchange="NSE"),
            _row(token="333", symbol="ABB", name="ABB", exchange="BSE"),
        ]
    )

    scrips = angel.get_all_scrips()

    assert [scrip.name for scrip in scrips] == ["SBIN"]


def test_bse_stock_rows_do_not_require_eq_suffix() -> None:
    angel = AngelInstrument.from_scrip_master_rows(
        [
            _row(
                token="500002",
                symbol="ABB",
                name="ABB",
                exchange="BSE",
                tick_size="5.000000",
            ),
            _row(
                token="1",
                symbol="BSX",
                name="BSX",
                exchange="BSE",
                tick_size="0.000000",
            ),
        ]
    )

    assert angel.instrument_master.bse_stock.get_token("ABB") == 500002
    assert angel.instrument_master.bse_stock.get_token("BSX") is None
    assert angel.instrument_master.bse_stock.indices["BSX"].token == 1


def test_duplicate_symbol_inside_same_exchange_is_rejected() -> None:
    rows = [
        _row(token="16669", symbol="BAJAJ-AUTO-EQ", name="BAJAJ-AUTO"),
        _row(token="99999", symbol="BAJAJ-AUTO-EQ", name="BAJAJ-AUTO"),
    ]

    with pytest.raises(
        ValueError, match="Duplicate Angel instrument stock key"
    ):
        AngelInstrument.from_scrip_master_rows(rows)


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
