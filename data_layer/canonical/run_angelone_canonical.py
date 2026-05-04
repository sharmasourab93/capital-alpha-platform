from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_layer.abs import (
    BrokerResponse,
    CandleRequest,  # noqa: E402
    DerivativeInstrumentRequest,
    InstrumentRequest,
    QuoteRequest,
)
from data_layer.canonical import (
    normalize_candles,  # noqa: E402
    normalize_derivative_expiries,
    normalize_derivative_underlyings,
    normalize_instruments,
    normalize_quotes,
)

_QUOTE_OPERATIONS = frozenset(
    {"fetch_quotes", "fetch_quotes_by_tokens", "fetch_bulk_quotes"}
)
_INSTRUMENT_OPERATIONS = frozenset(
    {
        "fetch_instruments",
        "fetch_instruments_by_exchange",
        "fetch_derivative_contracts",
        "resolve_derivative_instruments",
    }
)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for canonical Angel One commands."""

    parser = argparse.ArgumentParser(
        description="Run Angel One broker actions and emit canonical data."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    instruments = subparsers.add_parser(
        "instruments",
        help="Search instruments and return canonical instrument rows",
    )
    instruments.add_argument("--exchange", required=True)
    instruments.add_argument("--query", required=True)

    instruments_by_exchange = subparsers.add_parser(
        "instruments-by-exchange",
        help="List exchange instruments as canonical instrument rows",
    )
    instruments_by_exchange.add_argument("--exchange", required=True)

    quotes = subparsers.add_parser(
        "quotes",
        help="Fetch quotes by symbol and return canonical quote rows",
    )
    quotes.add_argument("--exchange", required=True)
    quotes.add_argument(
        "--mode", default="FULL", choices=("LTP", "OHLC", "FULL")
    )
    quotes.add_argument("--symbols", nargs="+", required=True)

    candles = subparsers.add_parser(
        "candles",
        help="Fetch candles by token and return canonical candle rows",
    )
    candles.add_argument("--exchange", required=True)
    candles.add_argument("--interval", required=True)
    candles.add_argument("--from-date", required=True)
    candles.add_argument("--to-date", required=True)
    candles.add_argument("--instrument-token", required=True)
    candles.add_argument("--symbol")

    derivative_underlyings = subparsers.add_parser(
        "derivative-underlyings",
        help="Fetch canonical derivative-underlying rows",
    )
    derivative_underlyings.add_argument("--exchange")
    derivative_underlyings.add_argument("--instrument-type")

    derivative_expiries = subparsers.add_parser(
        "derivative-expiries",
        help="Fetch canonical derivative-expiry rows",
    )
    derivative_expiries.add_argument("--exchange", required=True)
    derivative_expiries.add_argument("--underlying", required=True)
    derivative_expiries.add_argument("--instrument-type", required=True)

    derivative_contracts = subparsers.add_parser(
        "derivative-contracts",
        help="List derivative contracts as canonical instrument rows",
    )
    derivative_contracts.add_argument("--exchange", required=True)
    derivative_contracts.add_argument("--underlying", required=True)
    derivative_contracts.add_argument("--instrument-type", required=True)
    derivative_contracts.add_argument("--expiry", required=True)
    derivative_contracts.add_argument("--option-type")

    derivative_resolve = subparsers.add_parser(
        "resolve-derivative",
        help="Resolve one derivative instrument and return canonical rows",
    )
    derivative_resolve.add_argument("--exchange", required=True)
    derivative_resolve.add_argument("--underlying", required=True)
    derivative_resolve.add_argument("--instrument-type", required=True)
    derivative_resolve.add_argument("--expiry", required=True)
    derivative_resolve.add_argument("--strike", type=float)
    derivative_resolve.add_argument("--option-type")

    derivative_history = subparsers.add_parser(
        "derivative-history",
        help="Fetch canonical candles for one derivative contract",
    )
    derivative_history.add_argument("--exchange", required=True)
    derivative_history.add_argument("--underlying", required=True)
    derivative_history.add_argument("--instrument-type", required=True)
    derivative_history.add_argument("--expiry", required=True)
    derivative_history.add_argument("--interval", required=True)
    derivative_history.add_argument("--from-date", required=True)
    derivative_history.add_argument("--to-date", required=True)
    derivative_history.add_argument("--strike", type=float)
    derivative_history.add_argument("--option-type")

    return parser


def build_derivative_request(
    args: argparse.Namespace,
) -> tuple[DerivativeInstrumentRequest, ...]:
    """Build the derivative request tuple expected by the broker."""

    return (
        DerivativeInstrumentRequest(
            exchange=args.exchange,
            underlying=args.underlying,
            instrument_type=args.instrument_type,
            expiry=args.expiry,
            strike=args.strike,
            option_type=args.option_type,
        ),
    )


def normalize_response(response: BrokerResponse) -> list[dict]:
    """Normalize a broker response and serialize canonical rows as dicts."""

    normalized_rows = _normalize_broker_response(response)
    return [asdict(row) for row in normalized_rows]


def _normalize_broker_response(response: BrokerResponse) -> list:
    """Dispatch one broker response to the appropriate canonical normalizer."""

    if response.operation in _QUOTE_OPERATIONS:
        return normalize_quotes(response)
    if response.operation == "fetch_candles":
        return normalize_candles(response)
    if response.operation in _INSTRUMENT_OPERATIONS:
        return normalize_instruments(response)
    if response.operation == "fetch_derivative_underlyings":
        return normalize_derivative_underlyings(response)
    if response.operation == "fetch_derivative_expiries":
        return normalize_derivative_expiries(response)

    raise ValueError(
        "No canonical output mapping registered for operation={0}".format(
            response.operation
        )
    )


def main() -> None:
    """Run the canonical Angel One CLI and print canonical JSON rows."""

    parser = build_parser()
    args = parser.parse_args()

    try:
        from data_layer.brokers.angelone.rest.smartapi_rest_broker import (
            AngelOneSmartApiRestBroker,
        )
    except ModuleNotFoundError as exc:
        missing_module = getattr(exc, "name", "") or str(exc)
        raise SystemExit(
            "Missing runtime dependency: {0}. Install the Angel One broker dependencies in this interpreter.".format(
                missing_module
            )
        ) from exc

    broker = AngelOneSmartApiRestBroker()
    broker.authenticate()

    try:
        started_at = perf_counter()
        broker_started_at = perf_counter()
        response = _run_command(broker, args)
        broker_elapsed_ms = (perf_counter() - broker_started_at) * 1000
        canonical_started_at = perf_counter()
        canonical_rows = normalize_response(response)
        canonical_elapsed_ms = (perf_counter() - canonical_started_at) * 1000
        total_elapsed_ms = (perf_counter() - started_at) * 1000
        print(
            json.dumps(
                {
                    "operation": response.operation,
                    "canonical": canonical_rows,
                    "response_meta": response.response_meta,
                    "timing_ms": {
                        "broker": round(broker_elapsed_ms, 3),
                        "canonical": round(canonical_elapsed_ms, 3),
                        "total": round(total_elapsed_ms, 3),
                    },
                },
                indent=2,
                default=str,
            )
        )
    finally:
        broker.terminate_session()


def _run_command(broker, args: argparse.Namespace) -> BrokerResponse:
    """Execute one canonical CLI command against the Angel One broker."""

    if args.command == "instruments":
        return broker.fetch_instruments(
            InstrumentRequest(
                exchange=args.exchange,
                query=args.query,
            )
        )
    if args.command == "instruments-by-exchange":
        return broker.fetch_instruments_by_exchange(exchange=args.exchange)
    if args.command == "quotes":
        return broker.fetch_quotes(
            QuoteRequest(
                mode=args.mode,
                exchange=args.exchange,
                symbols=tuple(args.symbols),
            )
        )
    if args.command == "candles":
        return broker.fetch_candles(
            CandleRequest(
                exchange=args.exchange,
                interval=args.interval,
                from_date=args.from_date,
                to_date=args.to_date,
                symbol=args.symbol,
                instrument_token=args.instrument_token,
            )
        )
    if args.command == "derivative-underlyings":
        return broker.fetch_derivative_underlyings(
            exchange=args.exchange,
            instrument_type=args.instrument_type,
        )
    if args.command == "derivative-expiries":
        return broker.fetch_derivative_expiries(
            exchange=args.exchange,
            underlying=args.underlying,
            instrument_type=args.instrument_type,
        )
    if args.command == "derivative-contracts":
        return broker.fetch_derivative_contracts(
            exchange=args.exchange,
            underlying=args.underlying,
            instrument_type=args.instrument_type,
            expiry=args.expiry,
            option_type=args.option_type,
        )
    if args.command == "resolve-derivative":
        return broker.resolve_derivative_instruments(
            build_derivative_request(args)
        )
    if args.command == "derivative-history":
        resolved = broker.resolve_derivative_instruments(
            build_derivative_request(args)
        )
        instrument = resolved.payload[0]
        return broker.fetch_candles(
            CandleRequest(
                exchange=args.exchange,
                interval=args.interval,
                from_date=args.from_date,
                to_date=args.to_date,
                symbol=instrument["symbol"],
                instrument_token=instrument["token"],
            )
        )

    raise ValueError("Unsupported command: {0}".format(args.command))


if __name__ == "__main__":
    main()
