from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re


class AssetClass(str, Enum):
    EQUITY = "equity"
    DEBT = "debt"
    DERIVATIVE = "derivative"
    COMMODITY = "commodity"
    CURRENCY = "currency"
    UNKNOWN = "unknown"


class AssetType(str, Enum):
    STOCK = "stock"
    INDEX = "index"
    BOND = "bond"
    FUTURE = "future"
    OPTION = "option"
    CASH = "cash"
    UNKNOWN = "unknown"


class DerivativeKind(str, Enum):
    NONE = "none"
    FUTURE = "future"
    OPTION = "option"


_DEBT_KEYWORDS = (
    "NCD",
    "BOND",
    "DEB",
    "DEBENTURE",
    "GOI",
    "GSEC",
    "G-SEC",
    "SDL",
    "TBILL",
    "T-BILL",
    "SGB",
)
_PROBABLE_DEBT_SYMBOL_PATTERN = re.compile(r"^\d{3,4}[A-Z]{2,}\d{2}$")
_NSE_EQUITY_SERIES = frozenset({"EQ", "BE", "BZ", "SM", "ST"})
_NSE_DEBT_SERIES = frozenset(
    {"GB", "GS", "TB", "SG", "N0", "N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "N9", "NA"}
)
_NON_STOCK_NAME_KEYWORDS = (
    " ETF",
    " ETF ",
    " FUND",
    " MF",
    " INVIT",
    " REIT",
)


@dataclass(frozen=True)
class InstrumentClassification:
    exchange: str
    asset_class: AssetClass
    asset_type: AssetType
    derivative_kind: DerivativeKind = DerivativeKind.NONE
    instrument_type: str = ""
    market_label: str = "UNKNOWN"


def normalize_symbol(symbol: str) -> str:
    normalized_symbol = str(symbol).upper().strip()
    base_symbol, series = split_symbol_series(normalized_symbol)
    if series in _NSE_EQUITY_SERIES:
        return base_symbol
    return normalized_symbol


def split_symbol_series(symbol: str) -> tuple[str, str | None]:
    normalized_symbol = str(symbol).upper().strip()
    if "-" not in normalized_symbol:
        return normalized_symbol, None
    base_symbol, series = normalized_symbol.rsplit("-", 1)
    return base_symbol, series


def is_probable_debt_symbol(symbol: str, name: str = "") -> bool:
    normalized_symbol = symbol.upper().strip()
    normalized_name = " {0} ".format(name.upper().strip())
    _, series = split_symbol_series(normalized_symbol)

    if series in _NSE_DEBT_SERIES:
        return True

    if normalized_symbol.startswith(("SGB", "GSEC", "GOI", "TBILL", "SDL")):
        return True

    if any(" {0} ".format(keyword) in normalized_name for keyword in _DEBT_KEYWORDS):
        return True

    return _PROBABLE_DEBT_SYMBOL_PATTERN.match(normalized_symbol) is not None


def classify_instrument(
    *,
    exchange: str,
    symbol: str,
    name: str,
    instrument_type: str,
) -> InstrumentClassification:
    normalized_exchange = exchange.upper().strip()
    normalized_symbol = symbol.upper().strip()
    normalized_name = name.upper().strip()
    normalized_instrument_type = instrument_type.upper().strip()

    classifier = _CLASSIFIERS_BY_EXCHANGE.get(
        normalized_exchange,
        _classify_unknown,
    )
    return classifier(
        exchange=normalized_exchange,
        symbol=normalized_symbol,
        name=normalized_name,
        instrument_type=normalized_instrument_type,
    )


def _classify_nse(
    *,
    exchange: str,
    symbol: str,
    name: str,
    instrument_type: str,
) -> InstrumentClassification:
    _, series = split_symbol_series(symbol)

    if instrument_type == "AMXIDX":
        return InstrumentClassification(
            exchange=exchange,
            asset_class=AssetClass.EQUITY,
            asset_type=AssetType.INDEX,
            instrument_type=instrument_type,
            market_label="NSE_EQUITY_INDEX",
        )
    if is_probable_debt_symbol(symbol, name):
        return InstrumentClassification(
            exchange=exchange,
            asset_class=AssetClass.DEBT,
            asset_type=AssetType.BOND,
            instrument_type=instrument_type,
            market_label="NSE_DEBT_BOND",
        )
    if series in _NSE_EQUITY_SERIES or instrument_type == "EQ":
        return InstrumentClassification(
            exchange=exchange,
            asset_class=AssetClass.EQUITY,
            asset_type=AssetType.STOCK,
            instrument_type=instrument_type,
            market_label="NSE_EQUITY_STOCK",
        )
    return InstrumentClassification(
        exchange=exchange,
        asset_class=AssetClass.UNKNOWN,
        asset_type=AssetType.CASH,
        instrument_type=instrument_type,
        market_label="NSE_CASH_UNKNOWN",
    )


def _classify_bse(
    *,
    exchange: str,
    symbol: str,
    name: str,
    instrument_type: str,
) -> InstrumentClassification:
    if instrument_type == "AMXIDX":
        return InstrumentClassification(
            exchange=exchange,
            asset_class=AssetClass.EQUITY,
            asset_type=AssetType.INDEX,
            instrument_type=instrument_type,
            market_label="BSE_EQUITY_INDEX",
        )
    if is_probable_debt_symbol(symbol, name):
        return InstrumentClassification(
            exchange=exchange,
            asset_class=AssetClass.DEBT,
            asset_type=AssetType.BOND,
            instrument_type=instrument_type,
            market_label="BSE_DEBT_BOND",
        )
    if _is_probable_non_stock_cash_name(name):
        return InstrumentClassification(
            exchange=exchange,
            asset_class=AssetClass.UNKNOWN,
            asset_type=AssetType.CASH,
            instrument_type=instrument_type,
            market_label="BSE_CASH_UNKNOWN",
        )
    if instrument_type in {"", "EQ"}:
        return InstrumentClassification(
            exchange=exchange,
            asset_class=AssetClass.EQUITY,
            asset_type=AssetType.STOCK,
            instrument_type=instrument_type,
            market_label="BSE_EQUITY_STOCK",
        )
    return InstrumentClassification(
        exchange=exchange,
        asset_class=AssetClass.UNKNOWN,
        asset_type=AssetType.CASH,
        instrument_type=instrument_type,
        market_label="BSE_CASH_UNKNOWN",
    )


def _classify_derivative(
    *,
    exchange: str,
    symbol: str,
    name: str,
    instrument_type: str,
) -> InstrumentClassification:
    del symbol, name

    if instrument_type.startswith("OPT"):
        return InstrumentClassification(
            exchange=exchange,
            asset_class=AssetClass.DERIVATIVE,
            asset_type=AssetType.OPTION,
            derivative_kind=DerivativeKind.OPTION,
            instrument_type=instrument_type,
            market_label="{0}_DERIVATIVE_OPTION".format(exchange),
        )
    return InstrumentClassification(
        exchange=exchange,
        asset_class=AssetClass.DERIVATIVE,
        asset_type=AssetType.FUTURE,
        derivative_kind=DerivativeKind.FUTURE,
        instrument_type=instrument_type,
        market_label="{0}_DERIVATIVE_FUTURE".format(exchange),
    )


def _classify_mcx(
    *,
    exchange: str,
    symbol: str,
    name: str,
    instrument_type: str,
) -> InstrumentClassification:
    derivative_classification = _classify_derivative(
        exchange=exchange,
        symbol=symbol,
        name=name,
        instrument_type=instrument_type,
    )
    return InstrumentClassification(
        exchange=exchange,
        asset_class=AssetClass.COMMODITY,
        asset_type=derivative_classification.asset_type,
        derivative_kind=derivative_classification.derivative_kind,
        instrument_type=instrument_type,
        market_label="MCX_COMMODITY_{0}".format(
            derivative_classification.asset_type.value.upper()
        ),
    )


def _classify_currency(
    *,
    exchange: str,
    symbol: str,
    name: str,
    instrument_type: str,
) -> InstrumentClassification:
    derivative_classification = _classify_derivative(
        exchange=exchange,
        symbol=symbol,
        name=name,
        instrument_type=instrument_type,
    )
    return InstrumentClassification(
        exchange=exchange,
        asset_class=AssetClass.CURRENCY,
        asset_type=derivative_classification.asset_type,
        derivative_kind=derivative_classification.derivative_kind,
        instrument_type=instrument_type,
        market_label="{0}_CURRENCY_{1}".format(
            exchange,
            derivative_classification.asset_type.value.upper(),
        ),
    )


def _classify_unknown(
    *,
    exchange: str,
    symbol: str,
    name: str,
    instrument_type: str,
) -> InstrumentClassification:
    del symbol, name
    return InstrumentClassification(
        exchange=exchange,
        asset_class=AssetClass.UNKNOWN,
        asset_type=AssetType.UNKNOWN,
        instrument_type=instrument_type,
        market_label="UNKNOWN",
    )


def _is_probable_non_stock_cash_name(name: str) -> bool:
    normalized_name = " {0} ".format(name.upper().strip())
    return any(keyword in normalized_name for keyword in _NON_STOCK_NAME_KEYWORDS)


_CLASSIFIERS_BY_EXCHANGE = {
    "NSE": _classify_nse,
    "BSE": _classify_bse,
    "NFO": _classify_derivative,
    "BFO": _classify_derivative,
    "MCX": _classify_mcx,
    "CDS": _classify_currency,
    "CD": _classify_currency,
}


__all__ = [
    "AssetClass",
    "AssetType",
    "DerivativeKind",
    "InstrumentClassification",
    "classify_instrument",
    "is_probable_debt_symbol",
    "normalize_symbol",
    "split_symbol_series",
]
