from __future__ import annotations

from data_layer.abs import QuoteRequest


def test_fetch_bulk_quotes_single_chunk_returns_one_broker_response(
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
        "message": "SUCCESS",
        "errorcode": "",
        "data": [
            {"symbolToken": "3045", "ltp": 812.35},
            {"symbolToken": "2885", "ltp": 2941.80},
        ],
    }

    response = broker.fetch_bulk_quotes(
        QuoteRequest(
            mode="LTP",
            exchange="NSE",
            symbols=("SBIN", "RELIANCE"),
        ),
        pause_seconds=0,
    )

    assert response.operation == "fetch_bulk_quotes"
    assert response.payload["chunk_responses"] == 1
    assert len(response.payload["data"]) == 2
    assert response.response_meta["chunk_count"] == 1


def test_fetch_bulk_quotes_multiple_chunks_merges_all_data_rows(
    broker_module,
    mock_client,
    monkeypatch,
) -> None:
    broker = broker_module.AngelOneSmartApiRestBroker(client=mock_client)
    tokens = tuple(str(index) for index in range(60))
    chunk_1 = {
        "status": True,
        "message": "SUCCESS",
        "errorcode": "",
        "data": [
            {"symbolToken": token, "ltp": float(token)}
            for token in tokens[:50]
        ],
    }
    chunk_2 = {
        "status": True,
        "message": "SUCCESS",
        "errorcode": "",
        "data": [
            {"symbolToken": token, "ltp": float(token)}
            for token in tokens[50:]
        ],
    }
    mock_client.getMarketData.side_effect = [chunk_1, chunk_2]
    monkeypatch.setattr(broker_module.time, "sleep", lambda _: None)

    response = broker.fetch_bulk_quotes_by_tokens(
        exchange="NSE",
        instrument_tokens=tokens,
        mode="LTP",
        pause_seconds=0.01,
    )

    assert response.payload["chunk_responses"] == 2
    assert len(response.payload["data"]) == 60
    assert response.response_meta["chunk_count"] == 2
    assert response.response_meta["chunk_size"] == 50


def test_fetch_bulk_quotes_by_tokens_rejects_chunk_size_above_fifty(
    broker_module,
    mock_client,
) -> None:
    broker = broker_module.AngelOneSmartApiRestBroker(client=mock_client)

    try:
        broker.fetch_bulk_quotes_by_tokens(
            exchange="NSE",
            instrument_tokens=("3045",),
            chunk_size=51,
        )
    except broker_module.AngelOneSmartApiRestBrokerError as exc:
        assert exc.details["chunk_size"] == 51
    else:
        raise AssertionError("Expected AngelOneSmartApiRestBrokerError")


def test_fetch_bulk_quotes_raises_if_any_chunk_returns_failure_status(
    broker_module,
    mock_client,
) -> None:
    broker = broker_module.AngelOneSmartApiRestBroker(client=mock_client)
    mock_client.getMarketData.return_value = {
        "status": False,
        "message": "FAILED",
        "errorcode": "ERR",
        "data": [],
    }

    try:
        broker.fetch_bulk_quotes_by_tokens(
            exchange="NSE",
            instrument_tokens=("3045",),
            pause_seconds=0,
        )
    except broker_module.AngelOneSmartApiRestBrokerError as exc:
        assert exc.details["errorcode"] == "ERR"
        assert exc.details["chunk_index"] == 0
    else:
        raise AssertionError("Expected AngelOneSmartApiRestBrokerError")
