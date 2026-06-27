"""AWS SigV4 signing for IAM-protected API Gateway requests.

The data-layer API uses API Gateway IAM authorization for private endpoints.
This module keeps signing local to the client package so the runtime dependency
surface stays small and the client remains usable without boto3 or botocore.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping
from urllib.parse import parse_qsl, quote, urlsplit

from data_client.exceptions import DataLayerClientConfigError

AWS_ACCESS_KEY_ID_ENV = "AWS_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY_ENV = "AWS_SECRET_ACCESS_KEY"
AWS_SESSION_TOKEN_ENV = "AWS_SESSION_TOKEN"


@dataclass(frozen=True)
class AwsCredentials:
    """AWS credentials used for SigV4 request signing.

    The credentials are intentionally plain values loaded at client creation
    time. The signer does not refresh credentials by itself; callers using
    short-lived STS credentials should recreate the client when credentials are
    rotated by their host process.
    """

    access_key_id: str
    secret_access_key: str
    session_token: str | None = None

    @classmethod
    def from_env(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> "AwsCredentials":
        """Load AWS credentials from standard AWS environment variables.

        Required:
            AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.

        Optional:
            AWS_SESSION_TOKEN for temporary role/session credentials.
        """
        source = os.environ if environ is None else environ
        access_key_id = _require_env(source, AWS_ACCESS_KEY_ID_ENV)
        secret_access_key = _require_env(source, AWS_SECRET_ACCESS_KEY_ENV)
        session_token = _optional_env(source, AWS_SESSION_TOKEN_ENV)
        return cls(access_key_id, secret_access_key, session_token)


class SigV4Signer:
    """Sign API Gateway requests using AWS Signature Version 4.

    The signer is scoped to one AWS region and service. For the data-layer API
    the service is ``execute-api``, which is the SigV4 service name required by
    API Gateway HTTP APIs using IAM authorization.
    """

    def __init__(
        self,
        credentials: AwsCredentials,
        *,
        region: str,
        service: str = "execute-api",
    ) -> None:
        """Create a signer for one AWS service and region."""
        self._credentials = credentials
        self._region = region
        self._service = service

    def sign(
        self,
        method: str,
        url: str,
        *,
        body: bytes = b"",
        headers: Mapping[str, str] | None = None,
        now: datetime | None = None,
    ) -> dict[str, str]:
        """Return headers with SigV4 authorization fields added.

        Args:
            method: HTTP method, for example ``GET`` or ``POST``.
            url: Fully resolved request URL including query string.
            body: Already encoded request body bytes.
            headers: Caller-provided headers that must be included in the
                signature.
            now: Optional fixed timestamp used by tests.

        Returns:
            A new header mapping containing the original headers plus
            ``Authorization`` and required ``X-Amz-*`` signing headers.
        """
        request_time = now or datetime.now(timezone.utc)
        amz_date = request_time.strftime("%Y%m%dT%H%M%SZ")
        date_scope = request_time.strftime("%Y%m%d")
        parsed_url = urlsplit(url)
        host = parsed_url.netloc
        canonical_uri = _canonical_uri(parsed_url.path)
        canonical_query = _canonical_query(parsed_url.query)
        payload_hash = hashlib.sha256(body).hexdigest()

        # API Gateway verifies the signature against this exact canonical
        # header set. Header values are normalized per the SigV4 spec before
        # they are joined into the canonical request.
        signed_headers = {
            "host": host,
            "x-amz-content-sha256": payload_hash,
            "x-amz-date": amz_date,
        }
        if headers:
            for key, value in headers.items():
                signed_headers[key.lower()] = " ".join(str(value).split())
        if self._credentials.session_token:
            signed_headers["x-amz-security-token"] = (
                self._credentials.session_token
            )

        canonical_header_names = sorted(signed_headers)
        canonical_headers = "".join(
            f"{name}:{signed_headers[name]}\n"
            for name in canonical_header_names
        )
        signed_header_names = ";".join(canonical_header_names)
        canonical_request = "\n".join(
            [
                method.upper(),
                canonical_uri,
                canonical_query,
                canonical_headers,
                signed_header_names,
                payload_hash,
            ]
        )

        # The credential scope binds the signature to one date, region, and AWS
        # service. A valid signature in ap-south-2 will not validate in another
        # region.
        credential_scope = (
            f"{date_scope}/{self._region}/{self._service}/aws4_request"
        )
        string_to_sign = "\n".join(
            [
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode()).hexdigest(),
            ]
        )
        signing_key = _signing_key(
            self._credentials.secret_access_key,
            date_scope,
            self._region,
            self._service,
        )
        signature = hmac.new(
            signing_key, string_to_sign.encode(), hashlib.sha256
        ).hexdigest()
        authorization = (
            "AWS4-HMAC-SHA256 "
            f"Credential={self._credentials.access_key_id}/{credential_scope}, "
            f"SignedHeaders={signed_header_names}, "
            f"Signature={signature}"
        )

        result = {key: value for key, value in (headers or {}).items()}
        result["Authorization"] = authorization
        result["Host"] = host
        result["X-Amz-Content-Sha256"] = payload_hash
        result["X-Amz-Date"] = amz_date
        if self._credentials.session_token:
            result["X-Amz-Security-Token"] = self._credentials.session_token
        return result


def _require_env(source: Mapping[str, str], key: str) -> str:
    """Return a non-empty environment value or raise a config error."""
    value = source.get(key)
    if value is None or not value.strip():
        raise DataLayerClientConfigError(
            f"Missing required AWS environment variable: {key}"
        )
    return value.strip()


def _optional_env(source: Mapping[str, str], key: str) -> str | None:
    """Return a stripped environment value when present."""
    value = source.get(key)
    if value is None or not value.strip():
        return None
    return value.strip()


def _canonical_uri(path: str) -> str:
    """Return a SigV4-compatible canonical URI."""
    return quote(path or "/", safe="/-_.~")


def _canonical_query(query: str) -> str:
    """Return a sorted and percent-encoded SigV4 canonical query string."""
    if not query:
        return ""
    pairs = []
    for key, value in parse_qsl(query, keep_blank_values=True):
        pairs.append(
            (
                quote(key, safe="-_.~"),
                quote(value, safe="-_.~"),
            )
        )
    return "&".join(f"{key}={value}" for key, value in sorted(pairs))


def _signing_key(
    secret_access_key: str,
    date_scope: str,
    region: str,
    service: str,
) -> bytes:
    """Derive the scoped SigV4 signing key for one request date."""
    key = f"AWS4{secret_access_key}".encode()
    date_key = hmac.new(key, date_scope.encode(), hashlib.sha256).digest()
    region_key = hmac.new(date_key, region.encode(), hashlib.sha256).digest()
    service_key = hmac.new(
        region_key, service.encode(), hashlib.sha256
    ).digest()
    return hmac.new(service_key, b"aws4_request", hashlib.sha256).digest()
