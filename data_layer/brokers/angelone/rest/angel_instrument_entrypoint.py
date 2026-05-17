from __future__ import annotations

import argparse

from data_layer.brokers.angelone.rest.angel_instrument import (
    ANGEL_SCRIP_MASTER_URL,
    AngelInstrument,
)

SAMPLE_ROWS = [
    {
        "token": "16669",
        "symbol": "BAJAJ-AUTO-EQ",
        "name": "BAJAJ-AUTO",
        "expiry": "",
        "strike": "-1.000000",
        "lotsize": "1",
        "instrumenttype": "",
        "exch_seg": "NSE",
        "tick_size": "5.000000",
    },
    {
        "token": "333",
        "symbol": "NIFTY28OCT2524400CE",
        "name": "NIFTY",
        "expiry": "28OCT2025",
        "strike": "2440000.000000",
        "lotsize": "75",
        "instrumenttype": "OPTIDX",
        "exch_seg": "NFO",
        "tick_size": "5.000000",
    },
    {
        "token": "444",
        "symbol": "NIFTY28OCT2524500CE",
        "name": "NIFTY",
        "expiry": "28OCT2025",
        "strike": "2450000.000000",
        "lotsize": "75",
        "instrumenttype": "OPTIDX",
        "exch_seg": "NFO",
        "tick_size": "5.000000",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build and query the AngelInstrument exchange maps."
    )
    parser.add_argument(
        "--file",
        help="Path to a saved OpenAPIScripMaster.json file.",
    )
    parser.add_argument(
        "--url",
        action="store_true",
        help="Download the live Angel One scrip master JSON.",
    )
    parser.add_argument(
        "--exchange",
        default="NSE",
        help="Exchange segment to query, for example NSE or BSE.",
    )
    parser.add_argument(
        "--token",
        help="Token lookup value.",
    )
    parser.add_argument(
        "--symbol",
        help="Symbol lookup value, for example BAJAJ-AUTO-EQ.",
    )
    parser.add_argument(
        "--name",
        help="Name lookup value, for example NIFTY.",
    )
    args = parser.parse_args()

    angel = build_instrument(args.file, args.url)
    exchange = angel.get_exchange(args.exchange)
    if exchange is None:
        raise ValueError(f"Unknown Angel exchange segment: {args.exchange}")

    print("Loaded Angel exchanges:", angel.instrument_master.exchange_segments)
    print(f"{args.exchange} symbols available:", len(exchange.symbols))

    if args.token:
        print("By token:", exchange.get_by_token(args.token))

    if args.symbol:
        print("By symbol:", exchange.get_by_symbol(args.symbol))
        print("Token:", exchange.get_token(args.symbol))

    if args.name:
        matches = exchange.get_by_name(args.name)
        print(f"By name: {len(matches)} match(es)")
        for instrument in matches[:10]:
            print(instrument)

    if not any([args.token, args.symbol, args.name]):
        print("No query supplied. Running sample lookups.")
        print("NSE symbols:", angel.instrument_master.nse_stock.symbols)
        print(
            "NSE token:",
            angel.instrument_master.nse_stock.get_token("BAJAJ-AUTO-EQ"),
        )


def build_instrument(path: str | None, use_url: bool) -> AngelInstrument:
    if path and use_url:
        raise ValueError("Use either --file or --url, not both")

    if path:
        return AngelInstrument.from_file(path)

    if use_url:
        print(f"Downloading {ANGEL_SCRIP_MASTER_URL}")
        return AngelInstrument.from_url()

    return AngelInstrument.from_scrip_master_rows(SAMPLE_ROWS)


if __name__ == "__main__":
    main()
