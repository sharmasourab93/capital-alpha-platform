"""Configuration for the data-layer client.

The client can be pointed at an explicit API base URL or can derive the URL
from API Gateway parts. This keeps local/dev usage simple while preserving a
stable environment contract for deployed applications.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlencode

from data_client.exceptions import DataLayerClientConfigError

DATA_LAYER_API_BASE_URL_ENV = "DATA_LAYER_API_BASE_URL"
DATA_LAYER_API_ID_ENV = "DATA_LAYER_API_ID"
DATA_LAYER_AWS_REGION_ENV = "DATA_LAYER_AWS_REGION"
DATA_LAYER_STAGE_ENV = "DATA_LAYER_STAGE"
DATA_LAYER_TIMEOUT_SECONDS_ENV = "DATA_LAYER_TIMEOUT_SECONDS"
DEFAULT_REGION = "ap-south-2"
DEFAULT_STAGE = "dev"
DEFAULT_TIMEOUT_SECONDS = 10.0


@dataclass(frozen=True)
class DataLayerClientConfig:
    """Immutable data-layer API connection settings.

    URL resolution precedence:
        1. ``base_url`` / ``DATA_LAYER_API_BASE_URL`` when provided.
        2. API Gateway URL built from ``api_id``, ``region``, and ``stage``.

    The default region and stage reflect the current data-layer deployment
    defaults, but callers can override both through environment variables.
    """

    api_id: str | None = None
    region: str = DEFAULT_REGION
    stage: str = DEFAULT_STAGE
    base_url: str | None = None
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> "DataLayerClientConfig":
        """Load client config from environment variables.

        Recognized variables:
            DATA_LAYER_API_BASE_URL, DATA_LAYER_API_ID,
            DATA_LAYER_AWS_REGION, DATA_LAYER_STAGE, and
            DATA_LAYER_TIMEOUT_SECONDS.

        ``AWS_REGION`` is accepted as a fallback for the region so the client
        works naturally inside AWS-hosted runtimes.
        """
        source = os.environ if environ is None else environ
        return cls(
            base_url=_optional_env(source, DATA_LAYER_API_BASE_URL_ENV),
            api_id=_optional_env(source, DATA_LAYER_API_ID_ENV),
            region=_optional_env(source, DATA_LAYER_AWS_REGION_ENV)
            or source.get("AWS_REGION")
            or DEFAULT_REGION,
            stage=_optional_env(source, DATA_LAYER_STAGE_ENV) or DEFAULT_STAGE,
            timeout_seconds=float(
                _optional_env(source, DATA_LAYER_TIMEOUT_SECONDS_ENV)
                or DEFAULT_TIMEOUT_SECONDS
            ),
        )

    @property
    def resolved_base_url(self) -> str:
        """Return the configured or derived API Gateway stage URL.

        Raises:
            DataLayerClientConfigError: When neither an explicit base URL nor
                an API Gateway ID is available.
        """
        if self.base_url:
            return self.base_url.rstrip("/")
        if not self.api_id:
            raise DataLayerClientConfigError(
                "DATA_LAYER_API_ID is required when DATA_LAYER_API_BASE_URL "
                "is not set"
            )
        return (
            f"https://{self.api_id}.execute-api."
            f"{self.region}.amazonaws.com/{self.stage}"
        )

    def url_for(
        self,
        path: str,
        query: Mapping[str, str] | None = None,
    ) -> str:
        """Build a full API URL for one endpoint path.

        Args:
            path: Endpoint path with or without a leading slash.
            query: Optional query parameters encoded using standard URL form
                encoding.
        """
        normalized_path = path if path.startswith("/") else f"/{path}"
        url = f"{self.resolved_base_url}{normalized_path}"
        if not query:
            return url
        return f"{url}?{urlencode(query)}"


def _optional_env(source: Mapping[str, str], key: str) -> str | None:
    """Return a stripped environment value when present."""
    value = source.get(key)
    if value is None or not value.strip():
        return None
    return value.strip()
