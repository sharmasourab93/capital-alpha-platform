from .instruments import (
    DEFAULT_SCRIP_MASTER_URL,
    DERIVATIVE_EXCHANGES,
    AngelInstrument,
    AngelInstrumentMaster,
    AssetClass,
    AssetType,
    DerivativeInstrumentRecord,
    DerivativeKind,
    ExchangeSegmentIndex,
    InstrumentBucket,
    InstrumentClassification,
    ListedEquity,
    ListedEquityInstrument,
    classify_instrument,
    is_probable_debt_symbol,
    normalize_symbol,
)


def classify_angelone_instrument(instrument) -> str:
    if isinstance(instrument, AngelInstrument):
        classification = instrument.classification
    else:
        classification = classify_instrument(
            exchange=str(
                instrument.get("exch_seg") or instrument.get("exchange") or ""
            ),
            symbol=str(instrument.get("symbol") or ""),
            name=str(instrument.get("name") or ""),
            instrument_type=str(
                instrument.get("instrumenttype")
                or instrument.get("instrument_type")
                or ""
            ),
        )
    return classification.market_label


__all__ = [
    "AngelInstrument",
    "AngelInstrumentMaster",
    "AssetClass",
    "AssetType",
    "DEFAULT_SCRIP_MASTER_URL",
    "DERIVATIVE_EXCHANGES",
    "DerivativeInstrumentRecord",
    "DerivativeKind",
    "ExchangeSegmentIndex",
    "InstrumentBucket",
    "InstrumentClassification",
    "ListedEquity",
    "ListedEquityInstrument",
    "classify_angelone_instrument",
    "is_probable_debt_symbol",
    "normalize_symbol",
]
