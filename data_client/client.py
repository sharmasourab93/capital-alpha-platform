"""Public data-layer client entry point.

The package is intentionally organized around a single root client:

    DataLayerClient.from_env()

Endpoint groups hang from that root client as small namespaces such as
``client.market``. The methods are thin wrappers over the REST contract; they
do not cache server data, mutate global state, or translate broker-specific
fields outside the response shape returned by the data layer.
"""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import quote

from data_client.auth import AwsCredentials, SigV4Signer
from data_client.config import DataLayerClientConfig
from data_client.output import OutputMode, adapt_output
from data_client.transport import HttpTransport

ApiPayload = Any
JsonBody = dict[str, Any]
QueryParams = dict[str, str]


class DataLayerClient:
    """Thin client for the Capital Alpha data-layer REST API.

    ``DataLayerClient`` owns shared concerns: base URL resolution, request
    signing, HTTP transport, and optional output adaptation. Domain-specific
    endpoints are exposed through lightweight namespace clients so downstream
    applications get one obvious function call per API endpoint without
    duplicating signing and transport code.
    """

    def __init__(
        self,
        config: DataLayerClientConfig,
        *,
        credentials: AwsCredentials | None = None,
        transport: HttpTransport | None = None,
        output: OutputMode = "raw",
    ) -> None:
        """Create a stateless client around immutable config.

        Args:
            config: Resolved connection settings for the API Gateway stage.
            credentials: AWS credentials used for IAM/SigV4 protected routes.
                Leave unset only when calling public routes or injecting a
                transport in tests.
            transport: Optional transport override for tests or advanced hosts.
            output: Default output mode for all endpoint calls.
        """
        self.config = config
        self._signer = (
            SigV4Signer(credentials, region=config.region)
            if credentials is not None
            else None
        )
        self._transport = transport or HttpTransport(config.timeout_seconds)
        self._output = output
        self.market = MarketClient(self)

    @classmethod
    def from_env(
        cls,
        *,
        output: OutputMode = "raw",
        require_aws_credentials: bool = True,
    ) -> "DataLayerClient":
        """Build a client from data-layer and AWS environment variables.

        This is the expected production entry point. It resolves the API base
        URL from ``DATA_LAYER_API_BASE_URL`` or from API Gateway parts, then
        loads AWS credentials for IAM-authorized routes unless explicitly told
        not to.
        """
        config = DataLayerClientConfig.from_env()
        credentials = (
            AwsCredentials.from_env() if require_aws_credentials else None
        )
        return cls(config, credentials=credentials, output=output)

    def health(self, *, as_dataframe: bool = False) -> Any:
        """Return public runtime health.

        The health endpoint is intentionally unsigned because the API Gateway
        contract keeps ``/health`` available for basic uptime checks.
        """
        payload = self._request("GET", "/health", auth_required=False)
        return adapt_output(payload, output=self._output, force=as_dataframe)

    def brokers(self, *, as_dataframe: bool = False) -> Any:
        """Return available REST brokers using the compatibility endpoint."""
        payload = self._request("GET", "/brokers")
        return adapt_output(
            _extract(payload, "brokers"),
            output=self._output,
            force=as_dataframe,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: QueryParams | None = None,
        json_body: JsonBody | None = None,
        auth_required: bool = True,
    ) -> ApiPayload:
        """Send one request through the configured transport.

        Endpoint methods should stay small and delegate all cross-cutting
        concerns here. That keeps auth behavior consistent and makes it harder
        for a new endpoint wrapper to accidentally skip signing.
        """
        url = self.config.url_for(path, query)
        return self._transport.request_json(
            method,
            url,
            json_body=json_body,
            signer=self._signer if auth_required else None,
        )


class MarketClient:
    """Market-data endpoint methods.

    The market namespace mirrors the ``/market`` OpenAPI paths. Methods accept
    canonical request fields and return the API response data with optional
    DataFrame adaptation at the call site.
    """

    def __init__(self, client: DataLayerClient) -> None:
        """Create a market namespace around the root client."""
        self._client = client

    def brokers(self, *, as_dataframe: bool = False) -> Any:
        """Return available market brokers."""
        payload = self._client._request("GET", "/market/brokers")
        return adapt_output(
            _extract(payload, "brokers"),
            output=self._client._output,
            force=as_dataframe,
        )

    def intervals(
        self,
        *,
        broker: str,
        exchange: str,
        as_dataframe: bool = False,
    ) -> Any:
        """Return supported candle intervals for one broker exchange."""
        broker_path = _path_segment(broker)
        exchange_path = _path_segment(exchange)
        payload = self._client._request(
            "GET", f"/market/{broker_path}/{exchange_path}/intervals"
        )
        return adapt_output(
            _extract(payload, "intervals"),
            output=self._client._output,
            force=as_dataframe,
        )

    def scrips(
        self,
        *,
        broker: str,
        exchange: str,
        as_dataframe: bool = False,
    ) -> Any:
        """Return known scrip labels for one broker exchange."""
        broker_path = _path_segment(broker)
        exchange_path = _path_segment(exchange)
        payload = self._client._request(
            "GET", f"/market/{broker_path}/{exchange_path}/scrips"
        )
        return adapt_output(
            _extract(payload, "data"),
            output=self._client._output,
            force=as_dataframe,
        )

    def ltp(
        self,
        *,
        broker: str,
        exchange: str,
        symbol: str | list[str],
        as_dataframe: bool = False,
    ) -> Any:
        """Return latest traded price data for one or more symbols.

        The API contract accepts a comma-separated query value. This wrapper
        accepts either a single symbol or a list of symbols and normalizes the
        request without changing the response shape.
        """
        broker_path = _path_segment(broker)
        exchange_path = _path_segment(exchange)
        symbol_value = ",".join(symbol) if isinstance(symbol, list) else symbol
        payload = self._client._request(
            "GET",
            f"/market/{broker_path}/{exchange_path}/ltp",
            query={"symbol": symbol_value},
        )
        return adapt_output(
            _extract(payload, "data"),
            output=self._client._output,
            force=as_dataframe,
        )

    def quotes(
        self,
        *,
        broker: str,
        exchange: str,
        symbols: list[str],
        mode: Literal["LTP", "OHLC", "FULL"] = "FULL",
        as_dataframe: bool = False,
    ) -> Any:
        """Return quote data for one or more symbols.

        ``mode`` is intentionally restricted to the documented OpenAPI enum so
        callers fail early when they pass an unsupported quote mode.
        """
        broker_path = _path_segment(broker)
        exchange_path = _path_segment(exchange)
        payload = self._client._request(
            "POST",
            f"/market/{broker_path}/{exchange_path}/quotes",
            json_body={"symbols": symbols, "mode": mode},
        )
        return adapt_output(
            _extract(payload, "data"),
            output=self._client._output,
            force=as_dataframe,
        )

    def candles(
        self,
        *,
        broker: str,
        exchange: str,
        symbol: str,
        interval: str,
        from_time: str,
        to_time: str,
        as_dataframe: bool = False,
    ) -> Any:
        """Return historical candles.

        Candle payloads are adapted with the specialized ``candles`` shape so
        DataFrame output gets stable OHLCV columns and a date index.
        """
        broker_path = _path_segment(broker)
        exchange_path = _path_segment(exchange)
        payload = self._client._request(
            "POST",
            f"/market/{broker_path}/{exchange_path}/candles",
            json_body={
                "symbol": symbol,
                "interval": interval,
                "from_time": from_time,
                "to_time": to_time,
            },
        )
        return adapt_output(
            _extract(payload, "data"),
            output=self._client._output,
            force=as_dataframe,
            shape="candles",
        )


def _extract(payload: Any, key: str) -> Any:
    """Return a common response envelope field when present.

    The API commonly wraps endpoint data as ``{"data": ...}``,
    ``{"brokers": ...}``, or ``{"intervals": ...}``. Keeping extraction in one
    helper makes wrappers tolerant of direct payloads in tests while preserving
    the documented response body for real calls.
    """
    if isinstance(payload, dict) and key in payload:
        return payload[key]
    return payload


def _path_segment(value: str) -> str:
    """Return one URL-safe path segment without allowing slash traversal."""
    return quote(value, safe="")
