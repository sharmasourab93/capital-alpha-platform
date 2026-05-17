import pytest

from data_layer.brokers.angelone.rest.angel_instrument import AngelOneBroker
from data_layer.brokers.angelone.rest.angel_rest import AngelRestBroker


def test_angel_rest_loads_instruments_from_url_on_init(monkeypatch) -> None:
    instruments = AngelOneBroker.from_scrip_master_rows(
        [
            _row(token="2885", symbol="RELIANCE-EQ", name="RELIANCE"),
        ]
    )
    monkeypatch.setattr(AngelOneBroker, "from_url", lambda: instruments)

    broker = AngelRestBroker()

    scrip = broker.get_scrip("nse", "RELIANCE")

    assert broker.instruments is instruments
    assert scrip is not None
    assert scrip.symbol == "RELIANCE-EQ"
    assert scrip.token == 2885


def test_angel_rest_get_all_scrips_defaults_to_nse(monkeypatch) -> None:
    instruments = AngelOneBroker.from_scrip_master_rows(
        [
            _row(token="3045", symbol="SBIN-EQ", name="SBIN", exchange="NSE"),
            _row(token="500002", symbol="ABB", name="ABB", exchange="BSE"),
        ]
    )
    monkeypatch.setattr(AngelOneBroker, "from_url", lambda: instruments)

    broker = AngelRestBroker()

    scrips = broker.get_all_scrips()

    assert [scrip.name for scrip in scrips] == ["SBIN"]


def test_angel_rest_unwired_market_data_methods_are_explicit(
    monkeypatch,
) -> None:
    instruments = AngelOneBroker.from_scrip_master_rows([])
    monkeypatch.setattr(AngelOneBroker, "from_url", lambda: instruments)

    broker = AngelRestBroker()

    with pytest.raises(NotImplementedError, match="quote REST calls"):
        broker.get_quote()

    with pytest.raises(NotImplementedError, match="LTP REST calls"):
        broker.get_ltp()

    with pytest.raises(NotImplementedError, match="candle REST calls"):
        broker.get_candles()


def _row(
    *,
    token: str,
    symbol: str,
    name: str,
    exchange: str = "NSE",
    instrument_type: str = "",
    tick_size: str = "5.000000",
) -> dict[str, str]:
    return {
        "token": token,
        "symbol": symbol,
        "name": name,
        "expiry": "",
        "strike": "-1.000000",
        "lotsize": "1",
        "instrumenttype": instrument_type,
        "exch_seg": exchange,
        "tick_size": tick_size,
    }
