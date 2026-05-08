# REST FastAPI Layer

This package exposes the broker-backed market data REST API.

## Layout

- `fastapi_app.py`: FastAPI app assembly, middleware, exception handling, router registration.
- `contracts/`: stable route paths and OpenAPI endpoint documentation.
- `routes/`: FastAPI `APIRouter` modules grouped by API family.
- `schemas/`: request models and shared field descriptions.
- `dispatch/`: REST-to-broker request mapping logic.
- `router.py`: broker dispatch entry point and provider resolution.
- `security.py`: request authentication, authorization, rate limiting, and payload validation.
- `http_core.py`: transport wrapper around the REST router.

## Endpoint Reference

### System

#### `GET /health`
- Purpose: lightweight service health response for the REST layer.
- Query params: none.
- Request body: none.

### Reference

#### `GET /market/reference/instruments`
- Purpose: search broker instruments by market/exchange and free-text symbol or name.
- Query params:
  - `provider`: broker provider, currently `angelone`
  - `market`: exchange or market such as `NSE`, `BSE`, `NFO`
  - `query`: free-text symbol or name search term
- Request body: none.

#### `GET /market/reference/exchanges`
- Purpose: list exchanges available from the selected broker integration.
- Query params:
  - `provider`
- Request body: none.

#### `GET /market/reference/instrument-types`
- Purpose: list broker instrument types, optionally filtered by exchange.
- Query params:
  - `provider`
  - `exchange` optional
- Request body: none.

#### `GET /market/reference/exchange-symbol-name-map`
- Purpose: return exchange-scoped symbol/name listings or per-exchange summary counts.
- Query params:
  - `provider`
  - `exchange` optional
  - `query` optional, only meaningful with `exchange`
  - `offset` optional, default `0`
  - `limit` optional, default `100`, max `500`
- Request body: none.

### Cash

#### `GET /market/cash/nse-listed-stocks`
- Purpose: return paged NSE cash-equity stock rows with canonical `symbol` and `name`.
- Query params:
  - `provider`
  - `offset` optional, default `0`
  - `limit` optional, default `100`, max `500`
- Request body: none.

#### `GET /market/cash/bse-listed-stocks`
- Purpose: return paged BSE cash-equity stock rows with canonical `symbol` and `name`.
- Query params:
  - `provider`
  - `offset` optional, default `0`
  - `limit` optional, default `100`, max `500`
- Request body: none.

#### `POST /market/cash/quotes`
- Purpose: fetch live quote data for one or more cash-market symbols.
- Request body:
  - `provider`
  - `exchange`
  - `mode`: `LTP`, `OHLC`, or `FULL`
  - `symbols`: list of user-facing symbols, capped at `50`

#### `POST /market/cash/candles`
- Purpose: fetch historical candles for one cash-market symbol.
- Request body:
  - `provider`
  - `exchange`
  - `interval`
  - `from`
  - `to`
  - `symbol`

### Derivatives

#### `GET /market/derivatives/symbols`
- Purpose: list broker-native derivative symbols, optionally filtered by exchange and instrument type.
- Query params:
  - `provider`
  - `exchange` optional
  - `instrument_type` optional
- Request body: none.

#### `GET /market/derivatives/underlyings`
- Purpose: list derivative underlyings for one exchange or instrument family.
- Query params:
  - `provider`
  - `exchange` optional
  - `instrument_type` optional
- Request body: none.

#### `GET /market/derivatives/expiries`
- Purpose: list expiries for one derivative family.
- Query params:
  - `provider`
  - `exchange`
  - `underlying`
  - `instrument_type`
- Request body: none.

#### `GET /market/derivatives/strikes`
- Purpose: list strikes for one derivative family and expiry.
- Query params:
  - `provider`
  - `exchange`
  - `underlying`
  - `instrument_type`
  - `expiry`
  - `option_type` optional
- Request body: none.

#### `GET /market/derivatives/contracts`
- Purpose: list full derivative contract rows for one derivative family and expiry.
- Query params:
  - `provider`
  - `exchange`
  - `underlying`
  - `instrument_type`
  - `expiry`
  - `option_type` optional
- Request body: none.

#### `POST /market/derivatives/history`
- Purpose: fetch historical candles for a resolved derivative contract.
- Request body:
  - `provider`
  - `exchange`
  - `underlying`
  - `instrument_type`
  - `expiry`
  - `strike` optional
  - `option_type` optional
  - `interval`
  - `from`
  - `to`

#### `POST /market/derivatives/resolve`
- Purpose: resolve one or more derivative selections into broker instrument rows.
- Request body:
  - `provider`
  - `requests[]`
    - `exchange`
    - `underlying`
    - `instrument_type`
    - `expiry`
    - `strike` optional
    - `option_type` optional
