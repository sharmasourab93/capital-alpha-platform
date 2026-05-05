from __future__ import annotations

from data_layer.abs import QuoteRequest


def test_fetch_quotes_resolves_plain_symbols_and_calls_market_data(
    broker_module,
    mock_client,
    sample_scrip_master_rows: list[dict],
) -> None:
    broker = broker_module.AngelOneSmartApiRestBroker(client=mock_client)
    broker.market_data = broker_module.AngelInstrumentMaster.from_rows(
        sample_scrip_master_rows
    )
    mock_client.getMarketData.return_value = {
        "status": True,
        "data": [{"symbolToken": "3045"}, {"symbolToken": "2885"}],
    }

    response = broker.fetch_quotes(
        QuoteRequest(
            mode="LTP",
            exchange="NSE",
            symbols=("SBIN", "RELIANCE"),
        )
    )

    assert response.operation == "fetch_quotes_by_tokens"
    assert response.response_meta["tokens"] == ["3045", "2885"]
    mock_client.generateSession.assert_called_once()
    mock_client.getMarketData.assert_called_once_with(
        mode="LTP",
        exchangeTokens={"NSE": ["3045", "2885"]},
    )


def test_fetch_quotes_by_tokens_builds_exchange_tokens_payload(
    broker_module,
    mock_client,
) -> None:
    broker = broker_module.AngelOneSmartApiRestBroker(client=mock_client)
    mock_client.getMarketData.return_value = {"status": True, "data": []}

    broker.fetch_quotes_by_tokens(
        exchange="nse",
        instrument_tokens=("3045", "2885"),
        mode="OHLC",
    )

    mock_client.generateSession.assert_called_once()
    mock_client.getMarketData.assert_called_once_with(
        mode="OHLC",
        exchangeTokens={"NSE": ["3045", "2885"]},
    )


def test_fetch_quotes_raises_clean_error_for_unresolvable_symbol(
    broker_module,
    mock_client,
    sample_scrip_master_rows: list[dict],
) -> None:
    broker = broker_module.AngelOneSmartApiRestBroker(client=mock_client)
    broker.market_data = broker_module.AngelInstrumentMaster.from_rows(
        sample_scrip_master_rows
    )

    try:
        broker.fetch_quotes(
            QuoteRequest(
                mode="LTP",
                exchange="NSE",
                symbols=("DOESNOTEXIST",),
            )
        )
    except broker_module.AngelOneSmartApiRestBrokerError as exc:
        assert exc.details["exchange"] == "NSE"
        assert exc.details["symbol"] == "DOESNOTEXIST"
    else:
        raise AssertionError("Expected AngelOneSmartApiRestBrokerError")


def test_fetch_exchange_symbol_name_map_returns_summary_by_default(
    broker_module,
    mock_client,
    sample_scrip_master_rows: list[dict],
) -> None:
    broker = broker_module.AngelOneSmartApiRestBroker(client=mock_client)
    broker.market_data = broker_module.AngelInstrumentMaster.from_rows(
        sample_scrip_master_rows
    )

    response = broker.fetch_exchange_symbol_name_map()

    assert response.operation == "fetch_exchange_symbol_name_map"
    assert response.response_meta["mode"] == "summary"
    assert response.payload["exchanges"] == [
        {"exchange": "NFO", "symbol_count": 7},
        {"exchange": "NSE", "symbol_count": 3},
    ]


def test_fetch_exchange_symbol_name_map_returns_paged_exchange_rows(
    broker_module,
    mock_client,
    sample_scrip_master_rows: list[dict],
) -> None:
    broker = broker_module.AngelOneSmartApiRestBroker(client=mock_client)
    broker.market_data = broker_module.AngelInstrumentMaster.from_rows(
        sample_scrip_master_rows
    )

    response = broker.fetch_exchange_symbol_name_map(
        exchange="NSE",
        query="SBIN",
        limit=50,
    )

    assert response.response_meta["mode"] == "page"
    assert response.payload["exchange"] == "NSE"
    assert response.payload["total"] == 1
    assert response.payload["items"] == [
        {"symbol": "SBIN-EQ", "name": "STATE BANK OF INDIA"}
    ]


def test_fetch_derivative_expiries_returns_sorted_expiries(
    broker_module,
    mock_client,
    sample_scrip_master_rows: list[dict],
) -> None:
    broker = broker_module.AngelOneSmartApiRestBroker(client=mock_client)
    broker.market_data = broker_module.AngelInstrumentMaster.from_rows(
        sample_scrip_master_rows
    )

    response = broker.fetch_derivative_expiries(
        exchange="NFO",
        underlying="BANKNIFTY",
        instrument_type="OPTIDX",
    )

    assert response.operation == "fetch_derivative_expiries"
    assert response.payload == ("29MAY2025", "26JUN2025")
    assert response.response_meta["expiry_count"] == 2


def test_fetch_derivative_underlyings_returns_grouped_underlyings(
    broker_module,
    mock_client,
    sample_scrip_master_rows: list[dict],
) -> None:
    broker = broker_module.AngelOneSmartApiRestBroker(client=mock_client)
    broker.market_data = broker_module.AngelInstrumentMaster.from_rows(
        sample_scrip_master_rows
    )

    response = broker.fetch_derivative_underlyings(exchange="NFO")

    assert response.operation == "fetch_derivative_underlyings"
    assert response.payload["NFO"]["OPTIDX"] == ["BANKNIFTY"]
    assert response.payload["NFO"]["OPTSTK"] == ["RELIANCE"]
    assert response.payload["NFO"]["FUTSTK"] == ["RELIANCE"]


def test_fetch_derivative_strikes_returns_sorted_unique_strikes(
    broker_module,
    mock_client,
    sample_scrip_master_rows: list[dict],
) -> None:
    broker = broker_module.AngelOneSmartApiRestBroker(client=mock_client)
    broker.market_data = broker_module.AngelInstrumentMaster.from_rows(
        sample_scrip_master_rows
    )

    response = broker.fetch_derivative_strikes(
        exchange="NFO",
        underlying="BANKNIFTY",
        instrument_type="OPTIDX",
        expiry="29MAY2025",
        option_type="CE",
    )

    assert response.operation == "fetch_derivative_strikes"
    assert response.payload == (50000.0, 51000.0)
    assert response.response_meta["strike_count"] == 2


def test_fetch_derivative_contracts_returns_contracts_without_tokens(
    broker_module,
    mock_client,
    sample_scrip_master_rows: list[dict],
) -> None:
    broker = broker_module.AngelOneSmartApiRestBroker(client=mock_client)
    broker.market_data = broker_module.AngelInstrumentMaster.from_rows(
        sample_scrip_master_rows
    )

    response = broker.fetch_derivative_contracts(
        exchange="NFO",
        underlying="BANKNIFTY",
        instrument_type="OPTIDX",
        expiry="29MAY2025",
        option_type="CE",
    )

    assert response.operation == "fetch_derivative_contracts"
    assert response.response_meta["contract_count"] == 2
    assert all("token" not in contract for contract in response.payload)
    assert response.payload[0]["symbol"] == "BANKNIFTY29MAY202550000CE"
