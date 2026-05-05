from __future__ import annotations


def test_authenticate_wraps_sdk_exception_in_broker_error(
    broker_module,
    mock_client,
) -> None:
    mock_client.generateSession.side_effect = RuntimeError("sdk boom")
    broker = broker_module.AngelOneSmartApiRestBroker(client=mock_client)

    try:
        broker.authenticate()
    except broker_module.AngelOneSmartApiRestBrokerError as exc:
        assert "authentication failed" in str(exc).lower()
        assert exc.details["reason"] == "sdk boom"
    else:
        raise AssertionError("Expected AngelOneSmartApiRestBrokerError")


def test_authenticate_raises_on_invalid_session_payload(
    broker_module,
    mock_client,
) -> None:
    mock_client.generateSession.return_value = {"status": True}
    broker = broker_module.AngelOneSmartApiRestBroker(client=mock_client)

    try:
        broker.authenticate()
    except broker_module.AngelOneSmartApiRestBrokerError as exc:
        assert "invalid session" in str(exc).lower()
        assert exc.details["session"] == {"status": True}
    else:
        raise AssertionError("Expected AngelOneSmartApiRestBrokerError")


def test_broker_error_handler_does_not_double_wrap_broker_errors(
    broker_module,
) -> None:
    original_error = broker_module.AngelOneSmartApiRestBrokerError(
        "already broker error"
    )

    @broker_module.broker_error_handler("wrapped")
    def raises_broker_error():
        raise original_error

    try:
        raises_broker_error()
    except broker_module.AngelOneSmartApiRestBrokerError as exc:
        assert exc is original_error
        assert str(exc) == "already broker error"
    else:
        raise AssertionError("Expected AngelOneSmartApiRestBrokerError")


def test_market_data_error_contains_payload_details(
    broker_module,
    mock_client,
) -> None:
    mock_client.getMarketData.side_effect = RuntimeError("network boom")
    broker = broker_module.AngelOneSmartApiRestBroker(client=mock_client)
    broker.session = {"data": {"jwtToken": "jwt"}}

    try:
        broker.fetch_quotes_by_tokens(
            exchange="NSE",
            instrument_tokens=("3045",),
            mode="LTP",
        )
    except broker_module.AngelOneSmartApiRestBrokerError as exc:
        assert exc.details["payload"]["mode"] == "LTP"
        assert exc.details["reason"] == "network boom"
    else:
        raise AssertionError("Expected AngelOneSmartApiRestBrokerError")


def test_terminate_session_returns_none_on_sdk_exception(
    broker_module,
    mock_client,
) -> None:
    mock_client.terminateSession.side_effect = RuntimeError("close failed")
    broker = broker_module.AngelOneSmartApiRestBroker(client=mock_client)

    assert broker.terminate_session() is None
