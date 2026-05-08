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

    stock_names = subparsers.add_parser(
        "stock-names",
        help="List stock names for one exchange catalog",
    )
    stock_names.add_argument(
        "--exchange",
        required=True,
        choices=("NSE", "BSE"),
    )

    listed_equities = subparsers.add_parser(
        "listed-equities",
        help="List compact equity rows for one exchange catalog",
    )
    listed_equities.add_argument(
        "--exchange",
        required=True,
        choices=("NSE", "BSE"),
    )
    listed_equities.add_argument("--offset", type=int, default=0)
    listed_equities.add_argument("--limit", type=int, default=25)

    stock_instruments = subparsers.add_parser(
        "stock-instruments",
        help="List full stock instrument metadata for one exchange",
    )
    stock_instruments.add_argument(
        "--exchange",
        required=True,
        choices=("NSE", "BSE"),
    )

    stock_by_name = subparsers.add_parser(
        "stock-by-name",
        help="Resolve stock instruments by exact stock name within one exchange",
    )
    stock_by_name.add_argument(
        "--exchange",
        required=True,
        choices=("NSE", "BSE"),
    )
    stock_by_name.add_argument("--name", required=True)

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

    derivative_underlyings = subparsers.add_parser(
        "derivative-underlyings",
        help="Fetch derivative underlyings grouped by exchange and instrument type",
    )
    derivative_underlyings.add_argument("--exchange")
    derivative_underlyings.add_argument("--instrument-type")

    derivative_expiries = subparsers.add_parser(
        "derivative-expiries",
        help="Fetch derivative expiries for one underlying family",
    )
    derivative_expiries.add_argument(
        "--exchange",
        required=True,
        choices=("NFO", "BFO", "MCX", "CDS", "CD"),
    )
    derivative_expiries.add_argument("--underlying", required=True)
    derivative_expiries.add_argument("--instrument-type", required=True)

    derivative_strikes = subparsers.add_parser(
        "derivative-strikes",
        help="Fetch derivative strikes for one expiry",
    )
    derivative_strikes.add_argument(
        "--exchange",
        required=True,
        choices=("NFO", "BFO", "MCX", "CDS", "CD"),
    )
    derivative_strikes.add_argument("--underlying", required=True)
    derivative_strikes.add_argument("--instrument-type", required=True)
    derivative_strikes.add_argument("--expiry", required=True)
    derivative_strikes.add_argument("--option-type")

    derivative_market_catalog = subparsers.add_parser(
        "derivative-market-catalog",
        help="Inspect high-level derivative market catalog for one exchange",
    )
    derivative_market_catalog.add_argument(
        "--exchange",
        required=True,
        choices=("NFO", "BFO", "MCX", "CDS", "CD"),
    )

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

    derivative_contracts = subparsers.add_parser(
        "derivative-contracts",
        help="List derivative contracts for one underlying/expiry",
    )
    derivative_contracts.add_argument("--exchange", required=True)
    derivative_contracts.add_argument("--underlying", required=True)
    derivative_contracts.add_argument("--instrument-type", required=True)
    derivative_contracts.add_argument("--expiry", required=True)
    derivative_contracts.add_argument("--option-type")

    derivative_history = subparsers.add_parser(
        "derivative-history",
        help="Fetch candle/history for one derivative contract",
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

    master_summary = subparsers.add_parser(
        "master-summary",
        help="Inspect a compact summary of the prebuilt Angel instrument master catalogs",
    )
    master_summary.add_argument(
        "--exchange",
        help="Optional exchange filter such as NSE, BSE, NFO or MCX",
    )

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
        elif args.command == "stock-names":
            response = broker.fetch_stock_names(exchange=args.exchange)
        elif args.command == "listed-equities":
            response = broker.fetch_listed_equities(
                exchange=args.exchange,
                offset=args.offset,
                limit=args.limit,
            )
        elif args.command == "stock-instruments":
            response = broker.fetch_stock_instruments(exchange=args.exchange)
        elif args.command == "stock-by-name":
            response = broker.fetch_stock_instruments_by_name(
                exchange=args.exchange,
                name=args.name,
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
        elif args.command == "derivative-underlyings":
            response = broker.fetch_derivative_underlyings(
                exchange=args.exchange,
                instrument_type=args.instrument_type,
            )
        elif args.command == "derivative-expiries":
            response = broker.fetch_derivative_expiries(
                exchange=args.exchange,
                underlying=args.underlying,
                instrument_type=args.instrument_type,
            )
        elif args.command == "derivative-strikes":
            response = broker.fetch_derivative_strikes(
                exchange=args.exchange,
                underlying=args.underlying,
                instrument_type=args.instrument_type,
                expiry=args.expiry,
                option_type=args.option_type,
            )
        elif args.command == "derivative-market-catalog":
            response = broker.fetch_derivative_market_catalog(
                exchange=args.exchange,
            )
        elif args.command == "resolve-derivative":
            response = broker.resolve_derivative_instruments(
                build_derivative_request(args)
            )
        elif args.command == "derivative-contracts":
            response = broker.fetch_derivative_contracts(
                exchange=args.exchange,
                underlying=args.underlying,
                instrument_type=args.instrument_type,
                expiry=args.expiry,
                option_type=args.option_type,
            )
        elif args.command == "derivative-history":
            resolved = broker.resolve_derivative_instruments(
                build_derivative_request(args)
            )
            instrument = resolved.payload[0]
            response = broker.fetch_candles(
                CandleRequest(
                    exchange=args.exchange,
                    interval=args.interval,
                    from_date=args.from_date,
                    to_date=args.to_date,
                    symbol=instrument["symbol"],
                    instrument_token=instrument["token"],
                )
            )
        elif args.command == "master-summary":
            master = broker._get_market_data()
            if args.exchange:
                exchange_catalog = master.indexes.exchange_catalogs.get(
                    args.exchange.upper()
                )
                payload = (
                    _summarize_exchange_catalog(exchange_catalog)
                    if exchange_catalog is not None
                    else None
                )
            else:
                payload = {
                    exchange: _summarize_exchange_catalog(exchange_catalog)
                    for exchange, exchange_catalog in sorted(
                        master.indexes.exchange_catalogs.items()
                    )
                }
            print(json.dumps(payload, indent=2, default=str))
            return
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


def _summarize_exchange_catalog(exchange_catalog) -> dict | None:
    if exchange_catalog is None:
        return None

    stock_catalog = exchange_catalog.stock_catalog
    derivative_catalog = exchange_catalog.derivative_catalog

    return {
        "exchange": exchange_catalog.exchange,
        "instrument_types": list(exchange_catalog.instrument_types),
        "stock_catalog": (
            {
                "stock_name_count": len(stock_catalog.stock_names),
                "listed_equity_count": len(stock_catalog.listed_equities),
                "sample_names": list(stock_catalog.stock_names[:10]),
            }
            if stock_catalog is not None
            else None
        ),
        "derivative_catalog": (
            {
                "instrument_type_count": len(
                    derivative_catalog.families_by_instrument_type
                ),
                "underlyings_by_instrument_type": {
                    instrument_type: list(underlyings[:10])
                    for instrument_type, underlyings in sorted(
                        derivative_catalog.underlyings_by_instrument_type.items()
                    )
                },
            }
            if derivative_catalog is not None
            else None
        ),
    }


if __name__ == "__main__":
    main()
