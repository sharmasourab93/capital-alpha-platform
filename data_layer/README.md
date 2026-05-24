# Capital Alpha Data Layer

The data layer is Capital Alpha's broker-facing boundary. It exposes
broker-neutral contracts to application runtimes and delegates broker-specific
work to adapters such as AngelOne SmartAPI.

This README is a navigation guide. Detailed architecture, API contracts, ADRs,
and operational runbooks should live under `/docs`.

## Quick View

```text
FastAPI / Lambda / Future Runtime
        |
        v
Canonical Broker Service
        |
        v
Broker Registry
        |
        v
Broker Adapter
        |
        v
Broker Facade
        |
        v
SmartAPI / Broker SDK
```

Dependency direction is intentionally one-way: runtimes call canonical
services, canonical services call registered adapters, and adapters own broker
translation.

## Layer Map

```text
data_layer/
|-- abstractions/
|   `-- shared low-level broker and instrument contracts
|
|-- brokers/
|   |-- canonical/
|   |   |-- broker-neutral request and response models
|   |   |-- broker registry
|   |   `-- canonical REST service
|   |
|   |-- angelone/
|   |   `-- rest/
|   |       |-- angel_instrument.py
|   |       |-- angel_rest_broker.py
|   |       |-- angelone_adapter.py
|   |       `-- smartapi/
|   |           |-- account.py
|   |           |-- errors.py
|   |           |-- instrument_resolver.py
|   |           |-- payloads.py
|   |           |-- session.py
|   |           `-- transport.py
|   |
|   `-- rest_registry.py
|
|-- fundamental/
|   `-- reserved for fundamentals providers
|
|-- market/
|   `-- reserved for shared market-data concerns
|
|-- derivatives/
|   `-- being considered for futures and options modules
|
`-- runtimes/
    |-- rest/
    |   |-- FastAPI app, routes, schemas, handlers, logging
    |   |-- run.py
    |   `-- lambda_handler.py
    |
    `-- wss/
        `-- reserved for websocket runtime work
```

## Request Flow

```text
POST /market/angelone/NSE/candles
        |
        v
runtimes.rest.routes.market
        |
        v
canonical.models.CandleRequest
        |
        v
BrokerRestService
        |
        v
BrokerRegistry["angelone"]
        |
        v
AngelOneRestAdapter
        |
        v
AngelRestBroker
        |
        v
SmartApiTransport.get_candles()
        |
        v
AngelOne SmartAPI
```

REST routes should stay thin. Validation and normalization happen at the REST
schema and canonical model boundaries. AngelOne-specific lookups, tokens,
payloads, sessions, and SDK calls remain inside AngelOne modules.

## Canonical Broker Layer

The canonical layer is the broker-neutral contract used by runtimes and broker
adapters.

It currently models:

| Area | Request model | Response model |
|---|---|---|
| Scrip lookup | `ScripRequest` | `ScripResponse` |
| Scrip list | `ScripListRequest` | `ScripListResponse` |
| LTP | `LtpRequest` | `LtpResponse` |
| Quotes | `QuoteRequest` | `QuoteResponse` |
| Candles | `CandleRequest` | `CandleResponse` |
| Account | `AccountRequest` | `AccountResponse` |

Broker tokens, SDK payload names, and provider-specific response quirks should
not leak into canonical models.

## Broker Registry

```text
create_broker_rest_service()
        |
        v
create_default_rest_registry()
        |
        v
register AngelOneRestAdapter
```

`data_layer.brokers.rest_registry` wires available REST adapters into the
canonical service. Route code should not instantiate concrete broker classes.

Current broker:

```text
angelone
```

Future brokers should provide a canonical adapter and register through this
factory.

## AngelOne REST Module

AngelOne is split by responsibility:

| File | Responsibility |
|---|---|
| `angel_instrument.py` | Parse and index AngelOne scrip master data. |
| `angel_rest_broker.py` | Facade for AngelOne REST operations. |
| `angelone_adapter.py` | Translate canonical requests to AngelOne calls. |
| `smartapi/session.py` | SmartAPI credentials, TOTP, login, refresh, logout. |
| `smartapi/transport.py` | SmartAPI SDK method calls. |
| `smartapi/payloads.py` | Build SmartAPI candle, LTP, and quote payloads. |
| `smartapi/instrument_resolver.py` | Resolve name-based app symbols to AngelOne instruments. |
| `smartapi/account.py` | Account operation wrappers. |
| `smartapi/errors.py` | Error normalization and retry behavior. |

### AngelOne Design Notes

```text
Name from REST request
        |
        v
AngelInstrumentResolver
        |
        v
AngelOneBroker instrument index
        |
        v
AngelOne token and tradingsymbol
        |
        v
SmartAPI payload
```

Key decisions:

- Instrument lookup is name-based by design.
- Symbol and token lookup are not part of the public lookup contract.
- BSE stocks are mapped through `bse_others` because BSE symbols do not expose
  the same `-EQ` convention used by NSE.
- `AngelRestBroker` lazily loads instruments only when a lookup is needed.
- SmartAPI session refresh is handled by a decorator around authenticated
  broker calls.
- Unknown scrips currently fail through the broker operation error path.

## REST Runtime

The REST runtime is under `data_layer/runtimes/rest`.

```text
runtimes/rest/
|-- app.py              FastAPI app factory
|-- routes/             API route modules
|-- schemas.py          Pydantic request payloads
|-- errors.py           HTTP error mapping
|-- middleware.py       Request logging middleware
|-- config.py           Runtime environment settings
|-- run.py              Local uvicorn entrypoint
`-- lambda_handler.py   AWS Lambda handler frame
```

### Endpoints

| Method | Path | Status |
|---|---|---|
| `GET` | `/health` | Ready |
| `GET` | `/market/brokers` | Ready |
| `GET` | `/market/{broker}/{exchange}/intervals` | Ready |
| `GET` | `/market/{broker}/{exchange}/scrips` | Ready |
| `GET` | `/market/{broker}/{exchange}/ltp?symbol=SBIN,RELIANCE` | Ready |
| `POST` | `/market/{broker}/{exchange}/quotes` | Ready |
| `POST` | `/market/{broker}/{exchange}/candles` | Ready; pre-validation needs hardening |
| `GET` | `/funda/{market}` | Work in progress |
| `GET` | `/account/{broker}/profile` | Work in progress |
| `GET` | `/account/{broker}/funds` | Work in progress |
| `GET` | `/account/{broker}/holdings` | Work in progress |
| `GET` | `/account/{broker}/positions` | Work in progress |
| `GET` | `/account/{broker}/orders` | Work in progress |
| `GET` | `/account/{broker}/trades` | Work in progress |

Account routes are wired but marked `work_in_progress` until the final account
contract is reviewed. Fundamentals are reserved and also marked
`work_in_progress`.

## Market Limits

AngelOne market-data requests are guarded at the REST boundary.

| Limit | Current behavior |
|---|---|
| Quote symbols | Max `50` symbols per request. |
| Multi-symbol LTP | Max `50` comma-separated symbols. |
| Quote modes | `LTP`, `OHLC`, `FULL`. |
| Candle intervals | AngelOne interval constants only. |

Supported candle intervals exposed by the REST runtime:

| Label | AngelOne value |
|---|---|
| `1m` | `ONE_MINUTE` |
| `3m` | `THREE_MINUTE` |
| `5m` | `FIVE_MINUTE` |
| `10m` | `TEN_MINUTE` |
| `15m` | `FIFTEEN_MINUTE` |
| `30m` | `THIRTY_MINUTE` |
| `1h` | `ONE_HOUR` |
| `1D` | `ONE_DAY` |

## Runtime Modes

### Local FastAPI

```powershell
.\at-venv\Scripts\python.exe -m data_layer.runtimes.rest.run
```

Default local URL:

```text
http://127.0.0.1:8000
```

### AWS Lambda Frame

The Lambda handler is available at:

```text
data_layer.runtimes.rest.lambda_handler.handler
```

The handler uses Mangum:

```text
API Gateway or Lambda Function URL
        |
        v
Mangum
        |
        v
FastAPI app
```

Deployment packages must include `mangum`.

## Configuration

AngelOne credentials are read from environment variables when explicit
credentials are not injected:

| Variable | Purpose |
|---|---|
| `ANGELONE_API_KEY` | SmartAPI app API key |
| `ANGELONE_CLIENT_CODE` | AngelOne client code |
| `ANGELONE_PASSWORD` | AngelOne password |
| `ANGELONE_TOTP_SECRET` | TOTP secret for login |

REST runtime settings are environment-driven for host, port, reload, and log
level.

## Error Handling

```text
Broker-specific error
        |
        v
Canonical broker error
        |
        v
REST HTTP error response
```

Current HTTP mapping:

| Error | HTTP status |
|---|---|
| Validation failure | `422` |
| Broker not registered | `404` |
| Broker operation failure | `502` |
| AngelOne setup/runtime failure | `503` |
| Unexpected failure | `500` |

SmartAPI transport errors are normalized before they reach REST handlers.
Transient failures are retried. Authentication failures trigger one broker-level
session refresh.

## Development Status

```text
Done
|-- Canonical broker models and registry
|-- AngelOne REST facade and adapter
|-- AngelOne session management
|-- AngelOne market quotes, LTP, candles, and scrip listing
|-- FastAPI REST runtime
|-- AWS Lambda handler frame
|-- CI workflow for tests
|-- Unit tests for canonical, AngelOne, and REST runtime modules

In Progress
|-- Final account REST response contract
|-- Fundamental data namespace
|-- Candle payload pre-validation before SmartAPI calls
|-- Derivative modules for futures and options
|-- Additional brokers
|-- WebSocket runtime
```

## Testing

Run the full test suite:

```powershell
.\at-venv\Scripts\python.exe -m pytest -q
```

Run formatting check:

```powershell
.\at-venv\Scripts\python.exe -m black --check --line-length 79 --target-version py313 data_layer tests
```

## Adding a New Broker

```text
New broker SDK/client
        |
        v
Broker-specific facade
        |
        v
Canonical adapter
        |
        v
Broker registry
        |
        v
Existing REST routes
```

Expected steps:

1. Create the broker-specific facade under `data_layer/brokers/{broker}`.
2. Translate broker operations into canonical responses through an adapter.
3. Register the adapter in `data_layer/brokers/rest_registry.py`.
4. Add unit tests for payload translation, errors, and registry wiring.
5. Keep broker-specific fields out of canonical models unless the product
   contract explicitly requires them.

## Design Guardrails

- Keep canonical models broker-neutral.
- Keep AngelOne tokens and SmartAPI payload names inside AngelOne modules.
- Keep REST routes thin.
- Keep REST and WebSocket concerns separate.
- Keep instrument translation behind resolver/adapter boundaries.
- Prefer small explicit modules over broad shared abstractions.
- Add tests for every behavior change at the nearest useful boundary.
