# Angel One REST Test Plan

## Scope

This plan covers the Angel One REST broker module under:

- `data_layer/brokers/angelone/rest/instrument_master.py`
- `data_layer/brokers/angelone/rest/errors.py`
- `data_layer/brokers/angelone/rest/smartapi_rest_broker.py`
- `data_layer/brokers/angelone/run_angelone_broker.py`

The goal is a `pytest`-only suite that is:

- deterministic
- isolated from live Angel One services by default
- strong on symbol resolution, derivative resolution, payload shaping, chunking, and error handling

## Test Layout

Recommended layout:

```text
tests/
  data_layer/
    angelone/
      conftest.py
      fixtures.py
      test_instrument_master.py
      test_smartapi_rest_broker_quotes.py
      test_smartapi_rest_broker_bulk_quotes.py
      test_smartapi_rest_broker_candles.py
      test_smartapi_rest_broker_derivatives.py
      test_smartapi_rest_broker_metadata.py
      test_smartapi_rest_broker_errors.py
      test_run_angelone_broker.py
      test_live_smoke.py
```

## Test Strategy

### Layer 1: Pure unit tests

No network, no real SmartAPI client.

Targets:

- `instrument_master.py`
- helper logic inside `smartapi_rest_broker.py`

### Layer 2: Broker tests with mocks

Mock:

- `SmartConnect`
- `AngelInstrumentMaster.from_url`
- broker client methods such as `generateSession`, `getMarketData`, `getCandleData`, `searchScrip`, `terminateSession`

Targets:

- request payload shaping
- auth flow
- `BrokerResponse` structure
- error wrapping

### Layer 3: Optional live smoke tests

Run only with markers and env flags.

Targets:

- one auth check
- one quote request
- one candle request

These should never be part of the default local or CI run.

## Shared Fixtures

Create in `tests/data_layer/angelone/fixtures.py` or `conftest.py`.

### `sample_equity_rows`

Minimal rows:

- `SBIN-EQ`
- `RELIANCE-EQ`
- `UBL-EQ`
- `BHEL-EQ`
- `MTARTECH-EQ`

Include:

- `token`
- `symbol`
- `name`
- `exch_seg`
- `instrumenttype`
- `expiry`
- `strike`
- `lotsize`

### `sample_equity_rows_with_ambiguity`

Used to test:

- duplicate or conflicting equity-style resolution
- ambiguous symbol error paths

### `sample_derivative_rows`

Include:

- `BANKNIFTY` futures
- `BANKNIFTY` option CE
- `BANKNIFTY` option PE
- at least two expiries
- at least two strikes

### `sample_scrip_master_rows`

Combined dataset of equity and derivative rows.

### `mock_smartconnect`

Stub object with mocked methods:

- `generateSession`
- `getMarketData`
- `getCandleData`
- `searchScrip`
- `terminateSession`

### `authenticated_session_payload`

Example:

```python
{
    "status": True,
    "data": {
        "jwtToken": "jwt",
        "refreshToken": "refresh",
    },
}
```

### `ltp_market_data_response`

Example:

```python
{
    "status": True,
    "message": "SUCCESS",
    "errorcode": "",
    "data": [
        {
            "exchange": "NSE",
            "tradingSymbol": "SBIN-EQ",
            "symbolToken": "3045",
            "ltp": 812.35,
        }
    ],
}
```

### `ohlc_market_data_response`

Example:

```python
{
    "status": True,
    "message": "SUCCESS",
    "errorcode": "",
    "data": [
        {
            "exchange": "NSE",
            "tradingSymbol": "SBIN-EQ",
            "symbolToken": "3045",
            "ltp": 812.35,
            "open": 805.0,
            "high": 816.9,
            "low": 802.15,
            "close": 808.4,
        }
    ],
}
```

### `candle_response`

Example:

```python
{
    "status": True,
    "message": "SUCCESS",
    "errorcode": "",
    "data": [
        ["2025-01-01T09:15:00+05:30", 100.0, 110.0, 99.0, 108.0, 123456],
    ],
}
```

## Concrete Test Matrix

## `test_instrument_master.py`

### Priority: P0

1. `test_from_rows_builds_instruments_and_indexes`
- assert instrument count
- assert `by_token` populated
- assert `by_symbol_exchange` populated

2. `test_get_by_token_returns_matching_instrument`
- assert correct token returns correct symbol

3. `test_get_by_symbol_exchange_returns_exact_matches`
- assert direct symbol lookup returns expected row list

4. `test_resolve_equity_instrument_accepts_plain_symbol`
- input: `SBIN`, `NSE`
- expect resolved symbol is `SBIN-EQ`

5. `test_resolve_equity_instrument_accepts_broker_native_symbol`
- input: `SBIN-EQ`, `NSE`
- expect same row

6. `test_resolve_equity_instrument_prefers_eq_variant_when_available`
- dataset includes both `SBIN` and `SBIN-EQ`
- expect `SBIN` resolves to `SBIN-EQ`

7. `test_resolve_equity_instrument_raises_for_missing_symbol`
- expect `LookupError`

8. `test_resolve_equity_instrument_raises_for_ambiguous_matches`
- expect error contains conflicting symbols

9. `test_get_exchanges_returns_sorted_exchange_tuple`

10. `test_get_instrument_types_filters_by_exchange`

11. `test_get_instruments_by_exchange_returns_serialized_rows`

12. `test_get_derivative_symbols_groups_by_exchange_and_instrument_type`

13. `test_resolve_derivative_instrument_resolves_unique_option_contract`

14. `test_resolve_derivative_instrument_resolves_unique_future_contract`

15. `test_resolve_derivative_instrument_raises_for_wrong_expiry`

16. `test_resolve_derivative_instrument_raises_for_wrong_strike`

17. `test_resolve_derivative_instrument_raises_for_wrong_option_type`

18. `test_resolve_derivative_instrument_raises_for_multiple_matches`

## `test_smartapi_rest_broker_quotes.py`

### Priority: P0

1. `test_fetch_quotes_resolves_plain_symbols_and_calls_market_data`
- patch instrument master
- patch `getMarketData`
- assert token resolution used
- assert one `BrokerResponse` returned

2. `test_fetch_quotes_passes_requested_mode`
- verify `LTP`, `OHLC`, `FULL`

3. `test_fetch_quotes_by_tokens_builds_exchange_tokens_payload`
- assert exact payload

4. `test_fetch_quotes_auto_authenticates_when_session_missing`
- assert `authenticate()` called before market request

5. `test_fetch_quotes_by_tokens_includes_response_meta`

6. `test_fetch_quotes_raises_for_empty_symbols`

7. `test_fetch_quotes_raises_clean_error_for_unresolvable_symbol`

## `test_smartapi_rest_broker_bulk_quotes.py`

### Priority: P0

1. `test_fetch_bulk_quotes_single_chunk_returns_one_broker_response`

2. `test_fetch_bulk_quotes_multiple_chunks_merges_all_data_rows`
- dataset > 50 tokens
- assert merged `payload["data"]` contains all rows
- assert `response_meta["chunk_count"]` matches expected chunk count

3. `test_fetch_bulk_quotes_defaults_to_ltp_when_mode_missing`

4. `test_fetch_bulk_quotes_by_tokens_uses_chunk_size_limit`

5. `test_fetch_bulk_quotes_by_tokens_rejects_chunk_size_zero`

6. `test_fetch_bulk_quotes_by_tokens_rejects_chunk_size_above_fifty`

7. `test_fetch_bulk_quotes_by_tokens_respects_pause_between_chunks`
- patch `time.sleep`
- assert call count

8. `test_fetch_bulk_quotes_raises_if_any_chunk_returns_failure_status`

9. `test_fetch_bulk_quotes_raises_if_any_chunk_returns_non_dict_payload`

10. `test_merge_bulk_quote_payloads_handles_empty_chunk_response_list`

## `test_smartapi_rest_broker_candles.py`

### Priority: P1

1. `test_fetch_candles_builds_expected_payload`

2. `test_fetch_candles_maps_supported_intervals`
- parametrize `1m`, `3m`, `5m`, `10m`, `15m`, `30m`, `1h`, `1d`

3. `test_fetch_candles_raises_for_unsupported_interval`

4. `test_fetch_candles_raises_when_instrument_token_missing`

5. `test_fetch_candles_auto_authenticates_when_session_missing`

6. `test_fetch_candles_returns_expected_broker_response_shape`

## `test_smartapi_rest_broker_derivatives.py`

### Priority: P0

1. `test_resolve_derivative_instruments_returns_serialized_results`

2. `test_resolve_derivative_instruments_raises_for_empty_request_tuple`

3. `test_resolve_derivative_instruments_wraps_lookup_error_cleanly`

4. `test_fetch_derivative_tokens_groups_tokens_by_exchange`

5. `test_fetch_derivative_symbols_filters_by_exchange`

6. `test_fetch_derivative_symbols_filters_by_instrument_type`

## `test_smartapi_rest_broker_metadata.py`

### Priority: P1

1. `test_fetch_exchanges_returns_expected_payload`

2. `test_fetch_instrument_types_returns_expected_payload`

3. `test_fetch_instruments_by_exchange_returns_expected_payload`

4. `test_fetch_exchange_symbol_name_map_returns_expected_grouping`

5. `test_fetch_instruments_calls_search_scrip_correctly`

6. `test_fetch_instruments_raises_when_query_missing`

## `test_smartapi_rest_broker_errors.py`

### Priority: P0

1. `test_authenticate_wraps_sdk_exception_in_broker_error`

2. `test_authenticate_raises_on_invalid_session_payload`

3. `test_broker_error_handler_does_not_double_wrap_broker_errors`

4. `test_market_data_error_contains_payload_details`

5. `test_instrument_search_error_contains_exchange_and_query`

6. `test_candle_error_contains_request_details`

7. `test_instrument_master_load_error_is_wrapped`

8. `test_terminate_session_returns_none_on_sdk_exception`

## `test_run_angelone_broker.py`

### Priority: P1

1. `test_build_parser_contains_all_expected_commands`
- verify:
  - `exchanges`
  - `instrument-types`
  - `instruments`
  - `quotes`
  - `quotes-by-tokens`
  - `bulk-quotes`
  - `bulk-quotes-by-tokens`
  - `candles`
  - `derivative-symbols`
  - `resolve-derivative`
  - `derivative-tokens`

2. `test_help_works_when_called_from_repo_root_script_path`

3. `test_help_works_when_called_as_module`

4. `test_build_derivative_request_creates_expected_request_tuple`

5. `test_runner_exits_cleanly_when_runtime_dependency_missing`

6. `test_runner_quotes_command_dispatches_to_fetch_quotes`

7. `test_runner_bulk_quotes_command_dispatches_to_fetch_bulk_quotes`

8. `test_runner_bulk_quotes_by_tokens_dispatches_to_fetch_bulk_quotes_by_tokens`

9. `test_runner_candles_command_dispatches_to_fetch_candles`

## `test_live_smoke.py`

### Priority: P2

Mark every test:

```python
@pytest.mark.integration
```

Suggested tests:

1. `test_live_authenticate`
2. `test_live_quote_single_symbol`
3. `test_live_bulk_quote_small_batch`
4. `test_live_candle_single_symbol`

Skip unless all required env vars are present.

## Implementation Order

### Phase 1

- `test_instrument_master.py`
- `test_smartapi_rest_broker_quotes.py`
- `test_smartapi_rest_broker_bulk_quotes.py`
- `test_smartapi_rest_broker_errors.py`

### Phase 2

- `test_smartapi_rest_broker_candles.py`
- `test_smartapi_rest_broker_derivatives.py`
- `test_smartapi_rest_broker_metadata.py`

### Phase 3

- `test_run_angelone_broker.py`
- `test_live_smoke.py`

## Recommended Pytest Markers

In `pytest.ini` later:

```ini
[pytest]
markers =
    integration: live SmartAPI checks requiring network and credentials
```

## Immediate Gaps To Resolve While Writing Tests

These are likely to surface during test implementation:

1. Candle API still requires token-only input.
- likely future enhancement: `fetch_candles_by_symbol()`

2. Bulk quote methods are concrete-broker-only, not part of `MarketDataBroker`.
- decide whether that is intentional

3. Equity resolution heuristics are still symbol-pattern-based.
- likely need stricter cash-equity filtering if Angel master rows expose better fields
