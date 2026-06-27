"""Client SDK for the Capital Alpha data-layer REST API.

Import ``DataLayerClient`` from this package for normal use:

    from data_client import DataLayerClient

The remaining exports are provided for applications that need explicit config
construction or exception handling.
"""

from data_client.client import DataLayerClient
from data_client.config import DataLayerClientConfig
from data_client.exceptions import (
    DataLayerClientConfigError,
    DataLayerClientError,
    DataLayerHttpError,
)

__all__ = [
    "DataLayerClient",
    "DataLayerClientConfig",
    "DataLayerClientConfigError",
    "DataLayerClientError",
    "DataLayerHttpError",
]
