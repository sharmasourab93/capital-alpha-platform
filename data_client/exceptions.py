"""Exceptions raised by the data-layer client.

The client exposes a small exception hierarchy so callers can catch all
client-originated failures with ``DataLayerClientError`` or distinguish
configuration failures from API/transport failures when needed.
"""


class DataLayerClientError(Exception):
    """Base exception for all data-layer client errors."""


class DataLayerClientConfigError(DataLayerClientError):
    """Raised when client configuration is missing or invalid.

    Examples include missing API Gateway configuration, missing AWS credentials
    for signed requests, or requesting DataFrame output without pandas
    installed.
    """


class DataLayerHttpError(DataLayerClientError):
    """Raised for non-success responses from the data-layer API.

    ``status_code`` contains the HTTP response code when available. A value of
    ``0`` represents a local network failure before a response was received.
    ``payload`` contains parsed JSON when the response body is JSON, otherwise
    decoded text.
    """

    def __init__(self, status_code: int, payload: object) -> None:
        """Store response status and parsed payload."""
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"Data-layer API returned HTTP {status_code}")
