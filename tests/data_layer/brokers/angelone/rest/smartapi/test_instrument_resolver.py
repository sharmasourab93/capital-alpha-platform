import pytest

from data_layer.brokers.angelone.rest.angel_instrument import AngelOneBroker
from data_layer.brokers.angelone.rest.smartapi.errors import (
    AngelOneSmartApiRestBrokerError,
)
from data_layer.brokers.angelone.rest.smartapi.instrument_resolver import (
    AngelInstrumentResolver,
)


def test_resolver_finds_scrips_by_name_case_insensitively() -> None:
    resolver = AngelInstrumentResolver(_instruments())

    scrip = resolver.get_scrip("nse", "sbin")

    assert scrip is not None
    assert scrip.exchange == "NSE"
    assert scrip.name == "SBIN"
    assert scrip.symbol == "SBIN-EQ"
    assert scrip.token == 3045


def test_resolver_keeps_exchange_lookup_isolated() -> None:
    resolver = AngelInstrumentResolver(_instruments())

    nse_scrip = resolver.require_scrip("NSE", "SBIN")
    bse_scrip = resolver.require_scrip("BSE", "SBIN")

    assert nse_scrip.exchange == "NSE"
    assert nse_scrip.token == 3045
    assert bse_scrip.exchange == "BSE"
    assert bse_scrip.token == 500112


def test_resolver_finds_indices_by_name() -> None:
    resolver = AngelInstrumentResolver(_instruments())

    scrip = resolver.require_scrip("NSE", "NIFTY")

    assert scrip.symbol == "NIFTY"
    assert scrip.token == 99926000


def test_resolver_returns_none_for_unknown_exchange() -> None:
    resolver = AngelInstrumentResolver(_instruments())

    assert resolver.get_scrip("MCX", "SBIN") is None
    assert resolver.get_all_scrips("MCX") == []


def test_resolver_require_scrip_raises_for_unknown_name() -> None:
    resolver = AngelInstrumentResolver(_instruments())

    with pytest.raises(AngelOneSmartApiRestBrokerError) as exc_info:
        resolver.require_scrip("NSE", "MISSING")

    assert exc_info.value.details == {"exchange": "NSE", "key": "MISSING"}


def test_resolver_require_scrips_accepts_single_name_and_name_list() -> None:
    resolver = AngelInstrumentResolver(_instruments())

    single = resolver.require_scrips("NSE", "SBIN")
    multiple = resolver.require_scrips("NSE", ["SBIN", "NIFTY"])

    assert [scrip.name for scrip in single] == ["SBIN"]
    assert [scrip.name for scrip in multiple] == ["SBIN", "NIFTY"]


def test_resolver_require_scrips_rejects_empty_input() -> None:
    resolver = AngelInstrumentResolver(_instruments())

    with pytest.raises(AngelOneSmartApiRestBrokerError) as exc_info:
        resolver.require_scrips("NSE", [])

    assert exc_info.value.details == {"exchange": "NSE"}


def _instruments() -> AngelOneBroker:
    rows = [
        {
            "token": "3045",
            "symbol": "SBIN-EQ",
            "name": "SBIN",
            "instrumenttype": "",
            "exch_seg": "NSE",
            "tick_size": "5",
        },
        {
            "token": "500112",
            "symbol": "SBIN",
            "name": "SBIN",
            "instrumenttype": "",
            "exch_seg": "BSE",
            "tick_size": "5",
        },
        {
            "token": "99926000",
            "symbol": "NIFTY",
            "name": "NIFTY",
            "instrumenttype": "AMXIDX",
            "exch_seg": "NSE",
            "tick_size": "0",
        },
    ]
    return AngelOneBroker.from_scrip_master_rows(rows)
