from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Angel One SmartAPI broker actions."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("exchanges", help="Fetch supported exchanges")

    instrument_types = subparsers.add_parser(
        "instrument-types",
        help="Fetch instrument types, optionally filtered by exchange",
    )
    instrument_types.add_argument("--exchange")

    instruments = subparsers.add_parser(
        "instruments",
        help="Search instruments using SmartAPI searchScrip",
    )
    instruments.add_argument("--exchange", required=True)
    instruments.add_argument("--query", required=True)

    quotes = subparsers.add_parser(
        "quotes",
        help="Fetch market quotes by symbol",
    )
    quotes.add_argument("--exchange", required=True)
    quotes.add_argument(
        "--mode", default="FULL", choices=("LTP", "OHLC", "FULL")
    )
    quotes.add_argument("--symbols", nargs="+", required=True)

    quotes_by_tokens = subparsers.add_parser(
        "quotes-by-tokens",
        help="Fetch market quotes by token",
    )
    quotes_by_tokens.add_argument("--exchange", required=True)
    quotes_by_tokens.add_argument(
        "--mode", default="FULL", choices=("LTP", "OHLC", "FULL")
    )
    quotes_by_tokens.add_argument("--tokens", nargs="+", required=True)

    bulk_quotes = subparsers.add_parser(
        "bulk-quotes",
        help="Fetch consolidated quotes by symbol in one BrokerResponse",
    )
    bulk_quotes.add_argument("--exchange", required=True)
    bulk_quotes.add_argument(
        "--mode", default="LTP", choices=("LTP", "OHLC", "FULL")
    )
    bulk_quotes.add_argument("--symbols", nargs="+", required=True)
    bulk_quotes.add_argument("--chunk-size", type=int, default=50)
    bulk_quotes.add_argument("--pause-seconds", type=float, default=1.05)

    bulk_quotes_by_tokens = subparsers.add_parser(
        "bulk-quotes-by-tokens",
        help="Fetch consolidated quotes by token in one BrokerResponse",
    )
    bulk_quotes_by_tokens.add_argument("--exchange", required=True)
    bulk_quotes_by_tokens.add_argument(
        "--mode", default="LTP", choices=("LTP", "OHLC", "FULL")
    )
    bulk_quotes_by_tokens.add_argument("--tokens", nargs="+", required=True)
    bulk_quotes_by_tokens.add_argument("--chunk-size", type=int, default=50)
    bulk_quotes_by_tokens.add_argument(
        "--pause-seconds", type=float, default=1.05
    )

    candles = subparsers.add_parser(
        "candles",
        help="Fetch candle data",
    )
    candles.add_argument("--exchange", required=True)
    candles.add_argument("--interval", required=True)
    candles.add_argument("--from-date", required=True)
    candles.add_argument("--to-date", required=True)
    candles.add_argument("--instrument-token", required=True)
    candles.add_argument("--symbol")

    derivatives = subparsers.add_parser(
        "derivative-symbols",
        help="Fetch derivative symbols grouped by exchange and instrument type",
    )
    derivatives.add_argument("--exchange")
    derivatives.add_argument("--instrument-type")

    derivative_resolve = subparsers.add_parser(
        "resolve-derivative",
        help="Resolve one derivative instrument",
    )
    derivative_resolve.add_argument("--exchange", required=True)
    derivative_resolve.add_argument("--underlying", required=True)
    derivative_resolve.add_argument("--instrument-type", required=True)
    derivative_resolve.add_argument("--expiry", required=True)
    derivative_resolve.add_argument("--strike", type=float)
    derivative_resolve.add_argument("--option-type")

    derivative_tokens = subparsers.add_parser(
        "derivative-tokens",
        help="Resolve one derivative instrument and return its token",
    )
    derivative_tokens.add_argument("--exchange", required=True)
    derivative_tokens.add_argument("--underlying", required=True)
    derivative_tokens.add_argument("--instrument-type", required=True)
    derivative_tokens.add_argument("--expiry", required=True)
    derivative_tokens.add_argument("--strike", type=float)
    derivative_tokens.add_argument("--option-type")

    return parser


def build_derivative_request(
    args: argparse.Namespace,
) -> tuple:
    from data_layer.abs import DerivativeInstrumentRequest

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


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        from data_layer.abs import (
            CandleRequest,
            InstrumentRequest,
            QuoteRequest,
        )
        from data_layer.brokers.angelone.rest.smartapi_rest_broker import (
            AngelOneSmartApiRestBroker,
        )
    except ModuleNotFoundError as exc:
        missing_module = getattr(exc, "name", "") or str(exc)
        raise SystemExit(
            "Missing runtime dependency: {0}. "
            "Install the Angel One broker dependencies in this interpreter.".format(
                missing_module
            )
        ) from exc

    broker = AngelOneSmartApiRestBroker()
    broker.authenticate()

    try:
        if args.command == "exchanges":
            response = broker.fetch_exchanges()
        elif args.command == "instrument-types":
            response = broker.fetch_instrument_types(exchange=args.exchange)
        elif args.command == "instruments":
            response = broker.fetch_instruments(
                InstrumentRequest(
                    exchange=args.exchange,
                    query=args.query,
                )
            )
        elif args.command == "quotes":
            response = broker.fetch_quotes(
                QuoteRequest(
                    mode=args.mode,
                    exchange=args.exchange,
                    symbols=tuple(args.symbols),
                )
            )
        elif args.command == "quotes-by-tokens":
            response = broker.fetch_quotes_by_tokens(
                exchange=args.exchange,
                instrument_tokens=tuple(args.tokens),
                mode=args.mode,
            )
        elif args.command == "bulk-quotes":
            response = broker.fetch_bulk_quotes(
                QuoteRequest(
                    mode=args.mode,
                    exchange=args.exchange,
                    symbols=tuple(args.symbols),
                ),
                chunk_size=args.chunk_size,
                pause_seconds=args.pause_seconds,
            )
        elif args.command == "bulk-quotes-by-tokens":
            response = broker.fetch_bulk_quotes_by_tokens(
                exchange=args.exchange,
                instrument_tokens=tuple(args.tokens),
                mode=args.mode,
                chunk_size=args.chunk_size,
                pause_seconds=args.pause_seconds,
            )
        elif args.command == "candles":
            response = broker.fetch_candles(
                CandleRequest(
                    exchange=args.exchange,
                    interval=args.interval,
                    from_date=args.from_date,
                    to_date=args.to_date,
                    symbol=args.symbol,
                    instrument_token=args.instrument_token,
                )
            )
        elif args.command == "derivative-symbols":
            response = broker.fetch_derivative_symbols(
                exchange=args.exchange,
                instrument_type=args.instrument_type,
            )
        elif args.command == "resolve-derivative":
            response = broker.resolve_derivative_instruments(
                build_derivative_request(args)
            )
        elif args.command == "derivative-tokens":
            response = broker.fetch_derivative_tokens(
                build_derivative_request(args)
            )
        else:
            raise ValueError("Unsupported command: {0}".format(args.command))

        print(
            json.dumps(
                {
                    "operation": response.operation,
                    "payload": response.payload,
                    "response_meta": response.response_meta,
                },
                indent=2,
                default=str,
            )
        )
    finally:
        broker.terminate_session()


if __name__ == "__main__":
    main()
